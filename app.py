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

import youtube_dl

app = Flask(__name__)

@app.route('/_play_song')
def play_song():
    '''play song by id, filename or title'''
    file_name = request.args.get('file_name')



    return jsonify(result='Playing ' + file_name)

@app.route('/_get_song')
def get_song():
    '''not sure, maybe get current song info'''
    file_name = request.args.get('file_name')
    
    # b = request.args.get('b', 0, type=int)
    
    return jsonify(result=True)

@app.route('/_database')
def database():
    '''test database function'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # filenames = next(os.walk('downloads'))[2]

        # t = ('RHAT',)
        # c.execute('SELECT * FROM video WHERE symbol=?', t)
        # c.execute('SELECT * FROM video')
        # print(c.fetchone())

        # c.execute('CREATE TABLE t(songId INTEGER PRIMARY KEY ASC, y, z);', t)

        # Larger example that inserts many records at a time
        # purchases = [('2006-03-28', 'BUY', 'IBM', 1000, 45.00),
        #              ('2006-04-05', 'BUY', 'MSFT', 1000, 72.00),
        #              ('2006-04-06', 'SELL', 'IBM', 500, 53.00),
        #             ]
        # c.executemany('INSERT INTO stocks VALUES (?,?,?,?,?)', purchases)

        # c.execute('insert into video (title, filename) values (?,?)', ('test name','test.mp4'))
        
        for row in c.execute('SELECT * FROM video ORDER BY dateAdded desc'):
            print(row)

        # conn.commit()

        # (u'2006-01-05', u'BUY', u'RHAT', 100, 35.14)
        # (u'2006-03-28', u'BUY', u'IBM', 1000, 45.0)
        # (u'2006-04-06', u'SELL', u'IBM', 500, 53.0)
        # (u'2006-04-05', u'BUY', u'MSFT', 1000, 72.0)
        
        return jsonify(result=True)

def add_video_to_database(title, filename):
    '''add new video record into db'''
    conn = sqlite3.connect('video.db')
    with conn:
        c = conn.cursor()
        # todo: check if filename exists here and overwrite if it does
        c.execute('insert into video (title, filename) values (?,?)', (title, filename))
        
        print('videoId', 'title', 'filename', 'rating', 'lastPlayed', 'dateAdded', 'mature', 'type', 'added by')
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

        for row in c.execute('SELECT * FROM video ORDER BY dateAdded desc'):
            print(row)

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
    url = request.args.get('url', '', str)

    # need to specify download format of h264 for rpi
    # need to catch malformed url
    # need to not download entire fucking playlist
    ydl = youtube_dl.YoutubeDL({'outtmpl': '/downloads/%(title)s - %(id)s.%(ext)s'})

    with ydl:
        result = ydl.extract_info(
            url
            # ,download=False # We just want to extract the info
        )

    if 'entries' in result:
        # Can be a playlist or a list of videos
        video = result['entries'][0]
    else:
        # Just a video
        video = result

    print(video)
    #video_url = video['url']
    filename = video['title'] + ' - ' + video['id'] + '.' + video['ext']
    print('guessing filename should be: ' + filename)

    add_video_to_database(filename, video['title'])

    return jsonify(result=video) 

@app.route('/_add_numbers')
def add_numbers():
    '''Add two numbers server side, ridiculous but well...'''
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b +1)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':

    app.debug = True
    app.run()
