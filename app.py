# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~

    web site where user can
        add songs via youtube-dl
        remove songs via mv to deleted directory
        rate songs into database
        play songs via vlc, locally or remotely
        get auto-playlist weighted by song rating
    
    todo: set renderer to chromecasts via command line
    todo: launch/relaunch vlc with new chromecast target using https://github.com/balloob/pychromecast (render change not supported via telnet yet)
'''
from flask import Flask, jsonify, render_template, request
from pathlib import Path
import sqlite3
import os
import random
import time

import telnetlib
import youtube_dl

app = Flask(__name__)

path = 'F:\\code\\music_pump\\downloads\\'

def load_video(videoId = 0):
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # videos=[]
        for row in c.execute('SELECT * FROM video where videoId = ? ORDER BY dateAdded desc', (videoId,)):
            video = Video(videoId = row[0], title = row[1], filename = row[2], rating = row[3], lastPlayed = row[4], dateAdded = row[5], mature = row[6], videoType = row[7], addedBy = row[8])
            # videos += video
            return video

# this not being serialisable sucks balls
class Video:
    def __init__(self, videoId=0, title='', filename='', rating=3, lastPlayed=None, 
                dateAdded=None, mature=False, videoType='music', addedBy='Unknown', length = -1):
        if(videoId > 0 ):
            self.videoId = videoId
        self.title = title
        self.filename = filename
        self.rating = rating
        self.lastPlayed = lastPlayed
        self.dateAdded = dateAdded
        self.mature = mature
        self.videoType = videoType
        self.addedBy = addedBy
        self.length = length

    def __str__(self):
        return '{ videoId: \"' + str(self.videoId)  + '\", title: \"' + self.title  + '\", filename: \"' + self.filename + '\"}'

    def save(self):
        conn = sqlite3.connect('video.db')
        with conn:
            c = conn.cursor()
            # dunno if i can even do this, probably not since the object has functions which i don't htink are directly serialisable
            if(self.videoId>0):
                c.execute('update video set title=:title, filename=:filename, rating=:rating, lastPlayed=:lastPlayed, dateAdded=:dateAdded, mature=:mature, videoType=:videoType, addedBy=:addedBy where videoId=:videoId', 
                    self)
            else:
                # c.execute('insert into video set (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (?,?,?,?,?,?,?,?) where videoId=?', 
                #     {title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy, videoId})
                c.execute('insert into video set (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (:title, :filename, :rating, :lastPlayed, :dateAdded, :mature, :videoType, :addedBy)', 
                    self)
            
class Vlc:
    # maybe init with URL?
    def __init__(self):
        self.downloading = False
        self.crntVideo = None
        self.crntOrder = -1
        self.pause = 0
        self.lastUpdated = -1

    def get_song(self):
        # build info from vlc player
        # todo: if valid and less than X seconds have elapsed just return existing
        try:
            print('calling at ' + str(self.lastUpdated))
            res=Video()

            res.title = '' # find by filename
            res.filename = telnet_command('get_title').strip()

            # seconds elapsed in current song
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
            print('Failed to get current song info from VLC')

        return jsonify(result=self.crntVideo)

        #return self.crntVideo

    def get_length(self):
        return self.crntVideo['length']

    def play_pause(self):
        telnet_command('pause')

        # toggle internal pause state
        self.pause = 1 - self.pause

        return jsonify(result=True)


vlc = Vlc()

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

@app.route('/_get_length')
def get_length():
    '''
        get the length of the currently playing track
        used for slider animation and 
    '''
    # length = telnet_command('get_length')

    return jsonify(result=vlc.crntVideo.length)

@app.route('/_play_pause')
def play_pause():
    '''play song by id, filename or title
        currently using the vlc rpc telnet interface, start vlc with "vlc --rc-host localhost:23"
    '''
    telnet_command('pause')
    return jsonify(result=True)

@app.route('/_delete_video')
def delete_video():
    video = load_video(request.args.get('videoId'))
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('delete from video where videoId =?', (video.videoId,))

    return jsonify(result={'title': video.title})

@app.route('/_play_video')
def play_video():
    '''play song by id, filename or title'''
    # load the video record by the videoId provided
    video = load_video(request.args.get('videoId'))
    addedBy = request.args.get('addedBy')

    # add to vlc
    print('query: ', video, addedBy)
    longpath = 'file:///' + (path + video.filename).replace('\\','/')
    telnet_command('add '+ longpath + '')

    #insert into queue
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('insert into queue (videoId, addedBy) values (?,?)', (video.videoId, addedBy))


    return jsonify(result={'title': video.title})

songInfoResult = {}
@app.route('/_get_song')
def get_song():
    ''' get current song but look it up in db to get extra info and pass it all back
        need: length, rating, who added
        todo: theoretically the script should know this before it asks as long as vlc
              isn't allowed to progress through it's own playlist
    '''
    
    return jsonify(vlc.get_song())

@app.route('/_raw_command')
def raw_command():
    ''' pass command directly to VLC, maybe get rid of it later '''
    cmd = request.args.get('cmd')

    return jsonify(result=telnet_command(cmd))


def add_video_to_database(title, filename, addedBy, url):
    '''add new video record into db'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # todo: check if filename exists here and overwrite? if it does
        c.execute('insert into video (title, filename, addedBy, srcUrl) values (?, ?, ?, ?)', (title, filename, addedBy, url))
        
        # print('videoId', 'title', 'filename', 'rating', 'lastPlayed', 'dateAdded', 'mature', 'videoType', 'added by')
        # for row in c.execute('SELECT * FROM video ORDER BY dateAdded desc'):
        #     print(row)
        
        return jsonify(result=True)

@app.route('/_rate')
def rate_video():
    # todo: validate input
    videoId = request.args.get('videoId')
    rating = request.args.get('rating')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()

        c.execute('update video set rating=? where videoId=?', (rating, videoId))

        return jsonify(result=True)

@app.route('/_insert_in_queue')
def insert_in_queue():
    ''' insert a video into the queue '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # c.execute('insert into queue (videoId, addedBy) values (?,?)', (videoId, addedBy))
        # make a gap by moving all songs after this one along one
        c.execute('update queue set order = order + 1 where order > ?', (crntOrder, ))
        # insert new thing
        c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, crntOrder + 1 ))

    return jsonify(result=True)

@app.route('/_auto_queue')
def auto_queue():
    # this just needs to play something if the queue is empty?

    ''' currently: check if queue is down to one or less songs, then queue one'''

    highestOrder = 0 # default to first in queue

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        for row in c.execute('select [order] from queue order by [order] desc LIMIT 1'): # get highest order
            highestOrder = row[0]
        
        # print('auto_queue current queue count', c.rowcount)

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
lag(cum_prob) OVER (ORDER BY cum_prob, title),
0
) AS lower_cum_bound,
cum_prob AS upper_cum_bound
FROM sampling_cumulative_prob
)
SELECT *
FROM cumulative_bounds where lower_cum_bound<:rand and upper_cum_bound>:rand;'''
        rand = random.random()
        videoId = 1
        for row in c.execute(rando, { 'rand': rand } ):
            print(row)
            # insert random song
            print(row[0], 'Video Bot', highestOrder + 1)
            c.execute('insert into queue (videoId, addedBy, [order]) values (?,?,?)', (row[0], 'Video Bot', highestOrder + 1))

    return '{ "response": True }'


def play_queue():
    # videoId = request.args.get('videoId')
    # addedBy = request.args.get('addedBy')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('select * from queue order by order asc')
        if(c.rowcount==0):
            auto_queue()
            return
        


        return jsonify(result=True)

@app.route('/_add_to_queue')
def add_to_queue():
    ''' insert a video into the queue '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('insert into queue (videoId, addedBy, [order]) values (?,?)', (videoId, addedBy, 1))
        return jsonify(result=True)

@app.route('/_clear_queue')
def clear_queue():
    '''return current queue to client'''

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # select the queue and add extra info from the video table
        queueSql = 'delete from queue'

        try:
            c.execute(queueSql)
            conn.commit()

            return jsonify(result=True)
        except:
            return jsonify(result=False)


@app.route('/_get_queue')
def get_queue():
    '''return current queue to client'''

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()

        videos = []

        # select the queue and add extra info from the video table
        queueSql = '''
        SELECT 
            queue.videoId, 
            video.title, 
            video.rating,
            queue.addedBy 
        FROM 
            queue 
        left join 
            video 
        on queue.videoId = video.videoId 

        ORDER BY queue.dateAdded desc
        '''

        # dunno if this can be simplified
        for row in c.execute(queueSql):

            video = {}
            video['videoId'] = row[0]
            video['title'] = row[1]
            video['rating'] = row[2]
            video['addedBy'] = row[3]
            # video['order'] = row[4]

            videos.append(video)

        return jsonify(result=videos)



@app.route('/_list_videos')
def list_videos():
    '''return big video list to client'''

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()

        videos = []

        # dunno if this can be simplified
        for row in c.execute('SELECT videoId, title, filename, rating, addedBy FROM video ORDER BY title desc'):
            video = {}
            video['videoId'] = row[0]
            video['title'] = row[1]
            video['filename'] = row[2]
            video['rating'] = row[3]
            video['addedBy'] = row[4]

            videos.append(video)

        return jsonify(result=videos)


def ydlhook(s):
    ''' just printing atm, need to pass back to clients '''
    try:
        if(s['status']!='finished'):
            print('ydlhook: ' + s['_percent_str'])
    except:
        print('ydlhook failed: ', s)

@app.route('/_clean_video_list')
def clean_video_list():
    ''' cull bad entries and other cleanup stuff'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        prevTitle=''
        for row in c.execute('''
        select video.videoId, clone.videoId, clone.title
            from video 
            left join video as clone 
            on video.title=clone.title 
                and video.videoId!=clone.videoId
        where clone.videoId is not null 
        order by video.videoId asc'''):

            video = {}
            video['videoId'] = row[0]
            video['cloneId'] = row[1]
            video['title'] = row[2]

            # close but no cigar, this will delete the first one if there's more than 2 similar records
            if(video['title'] != prevTitle):
                print('don\'t delete', video['videoId'])
                prevTitle=video['title']
                pass
            else:
                #c.execute('delete from video where videoId=?',(video['videoId'],))
                print('delete', video['videoId'])

            print('clone video found', video)

    return jsonify(result=True)

@app.route('/_download_video')
def download_video():
    '''download video and set default rating in db'''
    url = request.args.get('url', '', type=str)
    addedBy = request.args.get('addedBy', '', type=str)

    isPlaylist = url.find('&list=')
    if(isPlaylist>-1):
        url=url[0:isPlaylist]

    # todo: need to specify download format of h264 for rpi
    # todo: need to catch malformed url
    # todo: check if folder exists probably
    ydl = youtube_dl.YoutubeDL({'outtmpl': '/downloads/%(title)s - %(id)s.%(ext)s', 
    'format': 'bestvideo+bestaudio/best', 
    'getfilename': True, 
    'keep': True, 
    # 'restrictfilenames': True # makes it too hard to guess file name for now
    }) 
    # 'format': '137,136'}) # 'listformats': True
    ydl.add_progress_hook(ydlhook)
    with ydl:
        result = ydl.extract_info(
            url
            
            # ,download=False # We just want to extract the info
        )

    if 'entries' in result:
        # Can be a playlist or a list of videos
        # not doing playlists yet
        # video = result['entries'][0]
        return jsonify(result=False)
    else:
        # Just a video
        video = result

    # not sure where to find the actual filename it was saved as
    # todo: this is dumb
    # badChars = '"\'/&'
    filename = (video['title'] + ' - ' + video['id']).replace('"','\'').replace('/','_')

    

    # test if we had to merge the files into an mkv
    # todo: clean up
    try:
        print('trying downloads/' + filename + '.' + video['ext'])
        my_file = Path('downloads/'+ filename + '.' + video['ext']) # use os.join
        if not my_file.is_file():
            print(video['ext'] + ' not found trying mkv')
        else:
            filename += '.'+video['ext']

        print('trying downloads/' + filename + '.mkv')
        my_file = Path('downloads/' + filename + '.mkv') # use os.join
        if not my_file.is_file():
            print('file not found')
        else:
            filename += '.mkv'

    except:
        print('failed to find file')

    print('guessing filename should be: ' + filename)
    # strip stuff like (Official Video) from title
    # todo: this is dumb, maybe have a list of banned phrases
    title = video['title'].replace('(Music Video)','').replace('(Official Video)', '').replace('(Official Music Video)', '')
    add_video_to_database(title, filename, addedBy, url)

    return jsonify(result=video)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':

    app.debug = True
    app.run(host= '0.0.0.0', port=80)
