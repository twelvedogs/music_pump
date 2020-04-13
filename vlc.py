import logging
import random
from flask import jsonify # probably shouldn't need this here
import sqlite3
import telnetlib
import time
from video import Video
import cfg


# telnet connection
tn = None
def telnet_connect():
    global tn

    # print('Connecting: ', cfg.host, cfg.port)
    logging.info('Connecting {} {}'.format(cfg.host, cfg.port))
    tn = telnetlib.Telnet(cfg.host, cfg.port) # default telnet: 23
    telnet_command(cfg.password)

# todo: this should force new telnet commands to wait for old ones to finish?
#       once we're on async might be able to handle it better
def telnet_command(cmd):
    global tn

    if(tn == None):
        telnet_connect()

    cmd += '\n'
    # print('running cmd: ' + str(cmd))

    # if connection gone re-connect and re-call this function once we have an active connection
    # todo: what if re-connect fails?  does this just start hammering reconnect?
    try:
        # todo: log all of these
        # todo: cache these so multiple clients don't hammer the shit out of vlc
        tn.write(cmd.encode("utf-8"))
    except:
        telnet_connect()
        telnet_command(cmd)

    # get whatever the response is up until newline> as that's the vlc server's prompt
    response = tn.read_until(b'\r\n>', timeout=2).decode('utf-8')
    response = response.replace('>', '')

    return response

class Vlc:
    # maybe init with URL?
    def __init__(self):
        self.downloading = False
        self.crntVideo = None
        self.timeStarted = -1
        self.elapsed = 0 # seconds since song start
        self.crntOrder = -1
        self.pause = 0
        self.lastUpdated = -1

    def raw(self, cmd):
        return telnet_command(cmd)

    def advance_queue(self):
        ''' try to advance to next song, add song if none found '''
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            # print('trying to play queue order > ', self.crntOrder)
            logging.info('Trying to play queue order > %s', self.crntOrder)
            rows = c.execute('select video.videoId, video.title, video.filename, queue.[order] from queue inner join video on queue.videoId=video.videoId where queue.[order]>? order by queue.[order] asc limit 1',(self.crntOrder,))
            nextInQueue = rows.fetchone()

            # if no videos in queue add one and restart
            if(nextInQueue == None):
                # print('queue empty, adding and re-trying')
                logging.info('Internal queue empty, calling auto_queue() and waiting for re-try from wherever called this')
                rows.close()
                self.auto_queue()

            else:
                logging.info('Playing next file in queue: %s', nextInQueue[2])
                self.crntOrder = nextInQueue[3]
                v = Video(nextInQueue[0], nextInQueue[1], nextInQueue[2])
                self.play_now(v)

    def tick(self):
        '''
        maintenance tasks like managing playlist/currently playing
        '''
        # TODO: this is only called by web browser and issues can arise when we're managing the next song
        #       and this is called again before we're finished sorting out the next song
        # TODO: if this is called and the other thing hasn't had a chance to query vlc and find the video this
        #       skips out on current video

        if(not self.crntVideo): # or self.timeStarted + self.crntVideo.length > time.time() ): # timer not working yet
            logging.info('tick: as far as the app knows nothing playing (this can happen before vlc is queried), calling advance_queue, it\'ll add a video to the queue if req')
            
            self.advance_queue()
        else:
            # not logging this too noisy
            print('tick: as far as the app knows vlc is playing: ', self.crntVideo)
            self.get_video()

    def play_video(self, videoId, addedBy, after = True):
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

    # this should be an internal function for the vlc object that is called after the queue is advanced
    # push file to vlc, needs to be from the queue, probably needs to be renamed
    def play_now(self, video):

        # rate limiter, can't play a song more than once every 10 sec (for now)
        if(self.timeStarted >= time.time() - 10):
            return

        # clear queue and add the new video
        # print('play_now: clearing VLC playlist and queueing \"' + video.filename + '\"')
        logging.info('play_now: clearing VLC playlist and adding \"' + video.filename + '\" to it\'s queue')
        telnet_command('clear')
        self.timeStarted = time.time()
        self.crntVideo = video
        
        # play filename right now to vlc via telnet
        longpath = 'file:///' + (cfg.path + video.filename).replace('\\','/')
        telnet_command('add '+ longpath + '')

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
        ''' clears out the queue table, doesn't change vlc (yet)'''

        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            c.execute('delete from queue')
            conn.commit()

        return True

    def auto_queue(self):
        ''' queues a random video, todo: currently not called'''
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
        todo: theoretically the script should know this before it asks as long as vlc
                isn't allowed to progress through it's own playlist
        '''

        try:
            # don't beat the crap out of the telnet server
            if(self.lastUpdated < time.time() - 7):
                filename = telnet_command('get_title').strip()
                
                # get video info from vlc

                # todo: if file not found remove from db with backup (probably just dump record as json)
                # todonext: this is getting none a few times in a row and re-queueing over and over
                if(filename=='' or filename==None):
                    logging.info('telnet: get_title returned empty string, probably no current song playing')
                    self.crntVideo = None # always clear crntVideo if no current filename
                else:
                    # don't update from db if filename hasn't changed
                    if(filename == self.crntVideo.filename):
                        logging.info('vlc\'s currently playing filename \''+ filename + '\' unchanged')
                    else:
                        # pull video object from db record
                        logging.info('got filename but it doesn\'t match crntVideo, reloading from db')
                        self.crntVideo = Video.findByFilename(filename)
                        logging.info('found filename \'%s\' from vlc in db, videoId: %s', filename, self.crntVideo.videoId)

                self.lastUpdated = time.time() # seconds since epoch

        # currently on error unset
        except Exception as err:
            logging.info('Exception getting current video info from VLC:\n%s', str(err))
            self.crntVideo = None # might need to be more careful with this, if communication fails and this is unset then video will skip

        # no idea why this needs to be a copy
        if(self.crntVideo):
            return dict.copy(self.crntVideo.__dict__)
        else:
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
        # self.crntVideo = currentVideo


    def get_length(self):
        return self.crntVideo.length


    def play_pause(self):
        telnet_command('pause')

        # toggle internal pause state
        self.pause = 1 - self.pause

        return jsonify(result=True)