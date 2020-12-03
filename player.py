import logging
import random
import pychromecast
from flask import jsonify # probably shouldn't need this here
import sqlite3
#import telnetlib
import time
from video import Video
import cfg

chromecast = 'Office'


def get_chromecast():
    # dunno what this is but the first element is the list of ccasts
    chromecasts = pychromecast.get_chromecasts()[0]
    print('chromecasts', chromecasts)
    for cc in chromecasts:
        device = cc.device
        print('device', device)

        if(device.friendly_name=='Office'):
            print('Found office')
            cc.wait()
            return cc.media_controller
            # mc.play_media("http://192.168.1.10:5000/downloads/Au_Ra - X Games - bWGH2s2ZX0Y.mp4", content_type = "video/mp4")
            # mc.block_until_active()
            # mc.play()    


class Player:
    # maybe init with URL?
    def __init__(self):
        self.downloading = False
        self.crnt_video = None
        self.time_started = -1
        self.elapsed = 0 # seconds since song start
        self.crntOrder = -1
        self.pause = 0
        self.lastUpdated = -1

        self.mc = get_chromecast()

    @staticmethod
    def get_play_targets():
        chromecasts = pychromecast.get_chromecasts()[0]
        devices = []

        for cc in chromecasts:
            device = cc.device
            devices += [{ 'uuid' : device.uuid, 'name' : device.friendly_name + ' ' + device.model_name }] # can probably do this fancier but whatevs
            # [{ device.friendly_name, device.model_name, device.uuid }]
            print(device.friendly_name, device.model_name)

        return devices

    def play_on_chromecast(self, file):
        print('calling play on ' + file)
        self.mc.play_media('http://192.168.1.10:5000/downloads/' + file, content_type = 'video/mp4')
        self.mc.block_until_active()
        self.mc.play()  

    def advance_queue(self):
        ''' 
        try to advance to next song, add song if none found 
        '''
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            # print('trying to play queue order > ', self.crntOrder)
            logging.info('Trying to play queue order > %s', self.crntOrder)
            rows = c.execute('select video.videoId, video.title, video.filename, queue.[order] from queue inner join video on queue.videoId=video.videoId where queue.[order]>? order by queue.[order] asc limit 1',(self.crntOrder,))
            next_in_queue = rows.fetchone()

            # if no videos in queue add one and restart
            if(next_in_queue == None):
                # print('queue empty, adding and re-trying')
                logging.info('Internal queue empty, calling auto_queue() and waiting for re-try from wherever called this')
                rows.close()
                self.auto_queue()

            else:
                logging.info('Playing next file in queue: %s', next_in_queue[2])
                self.crntOrder = next_in_queue[3]
                v = Video(next_in_queue[0], next_in_queue[1], next_in_queue[2])
                self.play_now(v)

    def tick(self):
        '''
        should only check chromecast is still alive
        TODO: call this from web app
        '''
        if(not self.crnt_video): # or self.time_started + self.crnt_video.length > time.time() ): # timer not working yet
            logging.info('tick: as far as the app knows nothing playing (this can happen before player is queried), calling advance_queue, it\'ll add a video to the queue if req')
            
            self.advance_queue()
        else:
            # not logging this too noisy
            print('tick: as far as the app knows currently playing: ', self.crnt_video)
            self.get_video()

    def play_video(self, videoId, addedBy, after = False):
        '''
        insert video into queue by id, addedBy just for info
        TODO: rename to queue
        '''
        # print('playing video with id', videoId)
        logging.info('something called play_video with id %s, play after this song is set to %s', videoId, after)
        video = Video.load(videoId)
        
        #insert into queue
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            # make a gap by moving all videos after this one along one
            c.execute('update queue set [order] = [order] + 1 where [order] > ?', (self.crntOrder, ))
            conn.commit()
            # insert new thing
            c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, self.crntOrder + 1 ))
            conn.commit()

        if not after:
            # probably should just add to queue and stop current song?
            self.play_now(video)

    # this should be an internal function for the player object that is called after the queue is advanced
    # push file to player, needs to be from the queue, probably needs to be renamed
    def play_now(self, video):

        # rate limiter, can't play a song more than once every 10 sec (for now)
        if(self.time_started >= time.time() - 10):
            return

        # clear queue and add the new video
        # print('play_now: clearing player playlist and queueing \"' + video.filename + '\"')
        logging.info('play_now: clearing playlist and adding \"' + video.filename + '\" to queue')

        self.time_started = time.time()
        self.crnt_video = video
        
        # play filename right now to chromecast
        # long_path = 'file:///' + (cfg.path + video.filename).replace('\\','/')
        # telnet_command('add '+ long_path + '')
        self.play_on_chromecast(video.filename)


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

        return True

    def auto_queue(self):
        '''
        queues a random video
        '''
        print('trying to auto queue')
        conn = sqlite3.connect(cfg.db_path)

        video_to_add = -1
        with conn:
            c = conn.cursor()

            # here we go!
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
                print(row)
                video_to_add = row[0]

        # insert random video after current one
        if(video_to_add>0):
            self.play_video(video_to_add, 'Video Bot', True)
            return True
        else:
            return False


    def get_video(self):
        ''' 
        get current video but look it up in db to get extra info and pass it all back
        need: length, rating, who added
        todo: theoretically the script should know this before it asks as long as the chromecast
                isn't allowed to progress through it's own playlist
        '''

        try:
            # no idea why this needs to be a copy
            if(self.crnt_video):
                return dict.copy(self.crnt_video.__dict__)
            else:
                return None

        # currently on error unset
        except Exception as err:
            logging.info('Exception getting current video info:\n%s', str(err))
            self.crnt_video = None # might need to be more careful with this, if communication fails and this is unset then video will skip
            return None


    def update_length(self):
        pass
        # this needs a lot of work

        # seconds elapsed in current video
        # todo: calc from internal timer
        # elapsed = telnet_command('get_time').strip()
        # if(elapsed != ''):
        #     currentVideo.played = int(elapsed)
        #     self.elapsed = int(elapsed)
        # else:
        #     currentVideo.played = 0
        #     self.elapsed = 0
        # 
        # currentVideo.length = int(telnet_command('get_length').strip())
        # currentVideo.playing = int(telnet_command('is_playing').strip())

        # only update if we made it
        # self.crnt_video = currentVideo


    def get_length(self):
        return self.crnt_video.length


    def play_pause(self):
        # telnet_command('pause')

        # toggle internal pause state
        self.pause = 1 - self.pause

        return jsonify(result=True)