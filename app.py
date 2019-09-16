# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~

    web site where user can
        add songs via youtube-dl
        remove songs via mv to deleted directory
        rate songs into database
        play songs via vlc, locally or remotely
    
    todo: set renderer to chromecasts via command line
    todo: launch/relaunch vlc with new chromecast target using https://github.com/balloob/pychromecast (render change not supported via telnet yet)
'''
from flask import Flask, jsonify, render_template, request
import sqlite3
import os

import telnetlib
import youtube_dl

app = Flask(__name__)

path = 'F:\\code\\music_pump\\downloads\\'
# todo: global statuses so a cache of them can be hit up without
#       talking to vlc etc
downloading = False
crntVideoId = -1


def load_video(videoId = 0):
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # videos=[]
        for row in c.execute('SELECT * FROM video where videoId = ? ORDER BY dateAdded desc', (videoId,)):
            video = Video(videoId = row[0], title = row[1], filename = row[2], rating = row[3], lastPlayed = row[4], dateAdded = row[5], mature = row[6], videoType = row[7], addedBy = row[8])
            # videos += video
        return video

class Video:
    def __init__(self, videoId, title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy):
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
            


# telnet connection
tn = None
def telnet_connect():
    global tn

    host = 'localhost' # ip/hostname
    password = 'test' # password, just jams it in once we're connected
    port = '23'

    print('Connecting', host, port)
    tn = telnetlib.Telnet(host, port) # default telnet: 23
    telnet_command(password)

def telnet_command(cmd):
    global tn
    print(tn)
    if(tn == None):
        telnet_connect()

    cmd += '\n'
    print('running cmd: ' + str(cmd))

    # if connection gone re-connect and re-call this function once we have an active connection
    # todo: what if re-connect fails?  does this just start hammering reconnect?
    try:
        # todo: log all of these
        tn.write(cmd.encode("utf-8"))
    except:
        telnet_connect()
        telnet_command(cmd)

    # get whatever the response is up until newline> as that's the vlc server's prompt
    response = tn.read_until(b'\r\n>', timeout=2).decode('utf-8')
    response = response.replace('>', '') 
    print('response: ', response) 

    return response

@app.route('/_get_length')
def get_length():
    '''
        get the length of the currently playing track
        used for slider animation and 
    '''
    length = telnet_command('get_length')

    return jsonify(result=length)

@app.route('/_play_pause')
def play_pause():
    '''play song by id, filename or title
        currently using the vlc rpc telnet interface, start vlc with "vlc --rc-host localhost:23"
    '''
    telnet_command('pause')
    return jsonify(result=True)

@app.route('/_play_video')
def play_video():
    '''play song by id, filename or title'''
    video = load_video(request.args.get('videoId'))
    username = load_video(request.args.get('username'))

    longpath = 'file:///' + (path + video.filename).replace('\\','/')
    telnet_command('add '+ longpath + '')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('insert into queue (videoId, addedBy) values (?,?)', (video.videoId, username))

    return jsonify(result='Playing ' + video.filename)

@app.route('/_get_song')
def get_song():
    ''' get current song but look it up in db to get extra info and pass it all back
        need: length, rating, who added
        todo: theoretically the script should know this before it asks as long as vlc
              isn't allowed to progress through it's own playlist
    '''
    res = {}
    res["title"] = '' # find by filename
    res["filename"] = telnet_command('get_title').strip()
    res["played"] = int(telnet_command('get_time').strip())
    res["length"] = int(telnet_command('get_length').strip())

    return jsonify(result=res)

@app.route('/_raw_command')
def raw_command():
    ''' just a test func, maybe get rid of it later '''
    cmd = request.args.get('cmd')

    return jsonify(result=telnet_command(cmd))


def add_video_to_database(title, filename, addedBy):
    '''add new video record into db'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # todo: check if filename exists here and overwrite? if it does
        c.execute('insert into video (title, filename, addedBy) values (?, ?, ?)', (title, filename, addedBy))
        
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

@app.route('/_add_to_queue')
def add_to_queue():
    ''' insert a video into the queue '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')

    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        c.execute('insert into queue (videoId, addedBy) values (?,?)', (videoId, addedBy))
        return jsonify(result=True)

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
            video.rating 
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
        for row in c.execute('SELECT videoId, title, rating, addedBy FROM video ORDER BY dateAdded desc'):
            video = {}
            video['videoId'] = row[0]
            video['title'] = row[1]
            video['rating'] = row[2]
            video['addedBy'] = row[3]

            videos.append(video)

        return jsonify(result=videos)


def ydlhook(s):
    ''' just printing atm, need to pass back to clients '''
    try:
        if(s['status']!='finished'):
            print('ydlhook: ' + s['_percent_str'])
    except:
        print('ydlhook failed: ', s)

@app.route('/_download_video')
def download_video():
    '''download video and set default rating in db'''
    url = request.args.get('url', '', type=str)
    addedBy = request.args.get('addedBy', '', type=str)

    # todo: need to specify download format of h264 for rpi
    # todo: need to catch malformed url
    # todo: check if folder exists probably
    ydl = youtube_dl.YoutubeDL({'outtmpl': '/downloads/%(title)s - %(id)s.%(ext)s'})
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

    # print(video)

    filename = video['title'] + ' - ' + video['id'] + '.' + video['ext']
    print('guessing filename should be: ' + filename)
    # todo: strip stuff like (Official Video) from title
    add_video_to_database(video['title'], filename, addedBy)

    return jsonify(result=video) 

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':

    app.debug = True
    app.run()
