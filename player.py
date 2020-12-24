import logging
import random
import pychromecast
from flask import jsonify # probably shouldn't need this here
import sqlite3
import time
from video import Video
import cfg

chromecast = 'Office'


def get_chromecast():
    # dunno what this is but the first element is the list of ccasts
    chromecasts = pychromecast.get_chromecasts()[0]

    for cc in chromecasts:
        device = cc.device
        # print('device', device)

        if(device.friendly_name=='Office'):
            # print('Found office')
            cc.wait()
            cc.set_volume(0.01)
            return cc.media_controller


class Player:
    # probably init with player so each can be managed separately
    def __init__(self):
        self.downloading = False
        self.crnt_video = None
        self.time_started = -1
        self.crnt_order = -1
        self.pause = 0
        self.videos_last_updated = -1
        self.queue_last_updated = -1

        # self.last_status = ''
        # self.mc = get_chromecast(chromecast_guid)
        self.mc = get_chromecast()
        # self.mc.set_volume
        # this should only be called once lol
        self.last_event_time = -1
        self.mc.register_status_listener(self)
        

    @staticmethod
    def get_play_targets():
        # this blocks by default but can trigger a callback for each found chromecast
        chromecasts = pychromecast.get_chromecasts()[0]
        devices = []

        for cc in chromecasts:
            device = cc.device
            # "friendly_name", "model_name", "manufacturer", "uuid", "cast_type"
            devices += [{ 'uuid' : device.uuid, 'name' : device.friendly_name + ' ' + device.model_name }] # can probably do this fancier but whatevs

        return devices


    def new_media_status(self, status):
        '''
        chromecast calls back on status change, sometimes called multiple so needs rate limiter for actions
        player_state=='UNKNOWN' probably means the chromecast is disconnected, it will have lost the listener anyway
        is mc.status the same as the status passed in?
        '''

        logging.info('new chromecast status %s', self.mc.status)

        # self.status = status.player_state

        if(str(status.player_state)=='UNKNOWN'):
            print('did we lose the chromecast?')
            print(self.mc.status)

        # if(str(status.player_state)=='IDLE' and self.mc.status.idle_reason == 'ERROR'):
        #     print('IDLE status due to SHITTING ITSELF')
        #     # self.mc.status
        #     print(self.mc.status)

        # check if idle is a "new" status and ignore if not
        if(str(status.player_state)=='IDLE' and self.mc.status.idle_reason != 'CANCELLED' and self.mc.status.idle_reason != 'INTERRUPTED'):
            # print('IDLE status causing queue advance : ' + str(self.mc.status.idle_reason))
            self.advance_queue()

    def play_on_chromecast(self, file, title='', added_by='Unknown'):
        '''
        play the file
        probably change to play_on_target
        '''
        if(title==''):
            title=file

        # chromecast 1st & 2nd gen only support h264 & vp8 (from https://developers.google.com/cast/docs/media)
        # content_type is required but it's not super important, it's just used to decide the app that will handle it so any video 
        # content_type will work (possibly only those supported by your model device though)
        self.mc.play_media('http://192.168.1.10:5000/downloads/' + file, \
            title='%s - %s' % (title, added_by), content_type = 'video/mp4', \
            subtitles='http://192.168.1.10:5000/_subtitles', subtitle_id=1, subtitles_mime="text/vtt") #, autoplay=True)
        
        self.mc.enable_subtitle(1)
        self.mc.block_until_active()

        self.mc.play()

        

    def status(self):
        return self.mc.status

    def advance_queue(self):
        ''' 
        try to advance to next song, add song if none found 
        '''

        # we seem to get a second idle event very soon after the first once a track is finished
        # also one directly after a new track is played
        # there's probably a better way of handling this
        if(self.last_event_time >= time.time() - 1):
            print('Very fast multiple advance queue requests, ignoring')
            return
        self.last_event_time = time.time()  

        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            logging.info('Trying to play queue order > %d', self.crnt_order)
            next_in_queue_sql = 'select video.videoId, video.title, video.filename, queue.[order], queue.addedBy from queue inner join video on queue.videoId=video.videoId where queue.[order]>? order by queue.[order] asc limit 1'
            rows = c.execute(next_in_queue_sql,(self.crnt_order,))
            next_in_queue = rows.fetchone()

            # if no videos in queue add one
            if(next_in_queue == None):
                logging.info('At end of existing queue, calling auto_queue()')
                
                self.auto_queue()

                # get newly queued video
                rows = c.execute(next_in_queue_sql,(self.crnt_order,))
                next_in_queue = rows.fetchone()

            rows.close()

            logging.info('Playing next file in queue: %s', next_in_queue[2])
            
            # set queue position
            self.crnt_order = next_in_queue[3]
            v = Video.load(next_in_queue[0])

            self.play_now(v, next_in_queue[4])


    def insert_video_in_queue(self, videoId, addedBy):
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            c.execute('update queue set [order] = [order] + 1 where [order] > ?', (self.crnt_order, ))
            conn.commit()
            c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, self.crnt_order + 1 ))
            conn.commit()
        self.queue_last_updated=round(time.time())

    def queue_video(self, videoId, addedBy):
        '''
        add video to end of queue
        '''
        logging.info('queue_video %s', videoId)
        video = Video.load(videoId)
        
        #insert into queue
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            queueSql = '''
            SELECT 
                MAX([order])  
            FROM 
                queue
            '''
            for row in c.execute(queueSql):
                max = row[0]

            # if no rows max is undefined
            if(max==None):
                max=-1

            c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, max + 1 ))

        self.queue_last_updated=round(time.time())

        return video

    # this should be an internal function for the player object that is called after the queue is advanced
    # push file to player, needs to be from the queue, probably needs to be renamed
    def play_now(self, video, added_by="Not set"):
        # rate limiter, can't play a song more than once every x sec
        if(self.time_started >= time.time() - 0.25):
            print('rate limit hit, dropping request')
            return

        self.time_started = round(time.time())

        # TODO: only if file length is empty probably
        if(video.update_file_properties()):
            self.crnt_video = video

            # TODO: increase playcount
            self.play_on_chromecast(video.filename, video.title, added_by=added_by)
        else:
            print('couldn\'t add')

    def get_queue(self):
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()

            videos = []

            # select the queue and add extra info from the video table
            queueSql = '''
            SELECT 
                queue.videoId, 
                video.title, 
                video.rating,
                queue.addedBy,
                queue.[order] 
            FROM 
                queue 
            left join 
                video 
            on queue.videoId = video.videoId 

            ORDER BY queue.[order] asc
            '''

            # dunno if this can be simplified
            for row in c.execute(queueSql):

                video = {}
                video['videoId'] = row[0]
                video['title'] = row[1]
                video['rating'] = row[2]
                video['addedBy'] = row[3]
                video['order'] = row[4]

                videos.append(video)

            return videos

    def clear_queue(self):
        '''
        clears out the queue table
        '''
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            c.execute('delete from queue')
            conn.commit()

        self.crnt_order=-1
        self.queue_last_updated=round(time.time())

        return True

    def auto_queue(self):
        '''
        queues a random video
        '''
        conn = sqlite3.connect(cfg.db_path)

        video_to_add = -1
        with conn:
            c = conn.cursor()

            # gives each video a range, bigger if it's a higher rated song
            # we then pick a random number and play the video with the range that the number falls within
            rando = '''
            with video_with_sum as (select * from video CROSS JOIN (select sum(rating) as rating_sum from video)),
            sampling_probability as (select videoId, title, rating,rating*1.0/rating_sum as prob from video_with_sum),
            sampling_cumulative_prob AS (
            SELECT
                videoId, title,
                sum(prob) OVER (order by title) AS cum_prob
            FROM sampling_probability
            ),
            cumulative_bounds AS (
                SELECT
                videoId, title,
            COALESCE(
                lag(cum_prob) OVER (ORDER BY cum_prob, title), 0
            ) AS lower_cum_bound,
            cum_prob AS upper_cum_bound
            FROM sampling_cumulative_prob
            )
            SELECT *
            FROM cumulative_bounds where lower_cum_bound<:rand and upper_cum_bound>:rand;'''
            rand = random.random()

            for row in c.execute(rando, { 'rand': rand } ):
                video_to_add = row[0]

        # add new random video
        if(video_to_add > 0):
            self.queue_video(video_to_add, 'bot ')
            return True
        else:
            print('Failed to get a video')
            return False

    def get_video(self):
        ''' 
        get current video but look it up in db to get extra info and pass it all back
        TODO: get crnt video from chromecast if required, otherwise it's only findable if we've manipulated the chromecast since startup
        '''

        try:
            # apparently the dict is always? serialisable?
            if(self.crnt_video):
                return dict.copy(self.crnt_video.__dict__)
            else:
                return None

        # currently on error unset
        except Exception as err:
            logging.info('Exception getting current video info:\n%s', str(err))
            return None

    def stop(self):
        self.mc.stop()

        return True

    def play_next(self):
        self.advance_queue()

        return self.get_video()

    def play_prev(self):
        self.mc.stop()

        return self.get_video()

    def play_pause(self):
        if(self.pause):
            self.mc.play()
        else:
            self.mc.pause()

        # toggle internal pause state
        self.pause = 1 - self.pause

        return True