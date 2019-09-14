# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~

    web site where user can
        add songs via youtube-dl
        remove songs via mv to deleted directory
        rate songs into database
        play songs via vlc (or possibly but preferably not omxplayer) instance on this machine (or remote machine!)
'''
from flask import Flask, jsonify, render_template, request
import sqlite3
import os

import telnetlib
import youtube_dl

app = Flask(__name__)

path = 'F:\\code\\music_pump\\downloads\\'

def load_video(videoId = 0):
    print('videoId', videoId)
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
        return self.title + ' ' + self.filename + ' ' + str(self.videoId)

    def save(self):
        conn = sqlite3.connect('video.db')
        with conn:
            c = conn.cursor()
            if(self.videoId>0):
                c.execute('update video set title=:title, filename=:filename, rating=:rating, lastPlayed=:lastPlayed, dateAdded=:dateAdded, mature=:mature, videoType=:videoType, addedBy=:addedBy where videoId=:videoId', 
                    self)
            else:
                # c.execute('insert into video set (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (?,?,?,?,?,?,?,?) where videoId=?', 
                #     {title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy, videoId})
                c.execute('insert into video set (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (:title, :filename, :rating, :lastPlayed, :dateAdded, :mature, :videoType, :addedBy)', 
                    self)
            



tn = None
pause_toggle = False
def telnet_connect():
    global tn

    host = 'localhost' # ip/hostname
    # password = '' # currently not set
    port = '23'

    print('Connecting', host, port)
    tn = telnetlib.Telnet(host, port) # default telnet: 23

def telnet_command(cmd):
    global tn
    if(tn == None):
        telnet_connect()
    cmd += '\n'
    print('running cmd: ' + str(cmd))
    tn.write(cmd.encode("utf-8"))

     # just get whatever is in the buffer
    response = str(tn.read_eager())
    print('response: ', response)

    return response

@app.route('/_get_length')
def get_length():
    '''play song by id, filename or title
        currently using the vlc rpc telnet interface, start vlc with "vlc --rc-host localhost:23"
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
    print(video)
    telnet_command('add "'+ path + video.filename + '"')

    return jsonify(result='Playing ' + video.filename)

@app.route('/_get_song')
def get_song():
    '''not sure, maybe get current song info'''
    
    return jsonify(result=telnet_command('get_title'))

@app.route('/_raw_command')
def raw_command():
    '''not sure, maybe get current song info'''
    cmd = request.args.get('cmd')

    return jsonify(result=telnet_command(cmd))

def add_video_to_database(title, filename, addedBy):
    '''add new video record into db'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # todo: check if filename exists here and overwrite if it does
        c.execute('insert into video (title, filename, addedBy) values (?, ?, ?)', (title, filename, addedBy))
        
        print('videoId', 'title', 'filename', 'rating', 'lastPlayed', 'dateAdded', 'mature', 'videoType', 'added by')
        for row in c.execute('SELECT * FROM video ORDER BY dateAdded desc'):
            print(row)
        
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
        for row in c.execute('SELECT videoId, title, rating FROM video ORDER BY dateAdded desc'):
            video = {}
            video['videoId'] = row[0]
            video['title'] = row[1]
            video['rating'] = row[2]

            videos.append(video)

        return jsonify(result=videos)


@app.route('/_download_video')
def download_video():
    '''download video and set default rating in db'''
    url = request.args.get('url', '', type=str)
    addedBy = request.args.get('addedBy', '', type=str)

    # need to specify download format of h264 for rpi
    # need to catch malformed url
    ydl = youtube_dl.YoutubeDL({'outtmpl': '/downloads/%(title)s - %(id)s.%(ext)s'})

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

    print(video)
    #video_url = video['url']
    filename = video['title'] + ' - ' + video['id'] + '.' + video['ext']
    print('guessing filename should be: ' + filename)

    add_video_to_database(video['title'], filename, addedBy)

    return jsonify(result=video) 

# @app.route('/_add_numbers')
# def add_numbers():
#     '''Add two numbers server side, ridiculous but well...'''
#     a = request.args.get('a', 0, type=int)
#     b = request.args.get('b', 0, type=int)
#     return jsonify(result=a + b +1)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':

    app.debug = True
    app.run()
