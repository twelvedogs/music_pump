import random
from flask import jsonify # probably shouldn't need this here
import sqlite3
import telnetlib
import time
from video import Video

# todo: config file
path = 'F:\\code\\music_pump\\downloads\\'

# telnet connection
tn = None
def telnet_connect():
    global tn

    host = 'localhost' # ip/hostname
    password = 'test' # password, just jams it in once we're connected
    port = '4212' # vlc default telnet port, probably don't change as using 23 or something causes issues in linux

    print('Connecting', host, port)
    tn = telnetlib.Telnet(host, port) # default telnet: 23
    telnet_command(password)

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

    # print('telnet: ', cmd, response) 

    return response

class Vlc:
    # maybe init with URL?
    def __init__(self):
        self.downloading = False
        self.crntVideo = None
        self.crntOrder = -1
        self.pause = 0
        self.lastUpdated = -1

    def raw(self, cmd):
        return telnet_command(cmd)

    def play_video(self, videoId, addedBy, after = True):
        '''
        play video by id, addedBy just for info
        '''
        video = Video.load(videoId)

        #insert into queue
        conn = sqlite3.connect('video.db')
        with conn:
            c = conn.cursor()
            # make a gap by moving all videos after this one along one
            c.execute('update queue set order = order + 1 where order > ?', (self.crntOrder, ))
            # insert new thing
            c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, self.crntOrder + 1 ))

        if not after:
            # play filename right now to vlc via telnet
            longpath = 'file:///' + (path + video.filename).replace('\\','/')
            telnet_command('add '+ longpath + '')

    def auto_queue(self):
        ''' queues a random video, todo: currently not called'''

        conn = sqlite3.connect('video.db')
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

            # todo: it's 
            for row in c.execute(rando, { 'rand': rand } ):
                print(row)

                # insert random video after current one
                self.play_video(row[0], 'Video Bot', True)

        return True


    def get_video(self):
        ''' 
        get current video but look it up in db to get extra info and pass it all back
        need: length, rating, who added
        todo: theoretically the script should know this before it asks as long as vlc
                isn't allowed to progress through it's own playlist
        todo: if valid and less than X seconds have elapsed just return existing
        '''
        try:
            print('calling at ' + str(self.lastUpdated))
            res=Video()

            res.title = '' # find by filename
            res.filename = telnet_command('get_title').strip()

            # seconds elapsed in current video
            elapsed = telnet_command('get_time').strip()
            if(elapsed != ''):
                res.played = int(elapsed)
            else:
                res.played = 0
            
            res.length = int(telnet_command('get_length').strip())
            res.playing = int(telnet_command('is_playing').strip())

            # only update if we made it
            self.crntVideo = res
            self.lastUpdated = time.time() # seconds since epoch

        except Exception:
            print('Failed to get current video info from VLC')

        # no idea why this needs to be a copy
        return dict.copy(self.crntVideo.__dict__)


    def get_length(self):
        return self.crntVideo.length


    def play_pause(self):
        telnet_command('pause')

        # toggle internal pause state
        self.pause = 1 - self.pause

        return jsonify(result=True)