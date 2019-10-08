# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~

    web site where user can
        add videos via youtube-dl
        remove videos via mv to deleted directory
        rate videos into database
        play videos via vlc, locally or remotely
    
    todo: set renderer to chromecasts via command line
    todo: launch/relaunch vlc with new chromecast target using https://github.com/balloob/pychromecast (render change not supported via telnet yet)
'''
from flask import Flask, jsonify, render_template, request
from pathlib import Path
import sqlite3
import os
import random
import time
import youtube_dl

from video import Video
from vlc import Vlc

app = Flask(__name__)

path = 'F:\\code\\music_pump\\downloads\\'

vlc = Vlc()

@app.route('/_get_length')
def get_length():
    '''
    get the length of the currently playing track
    used for slider animation and 
    '''
    return jsonify(result=vlc.crntVideo.length)

@app.route('/_play_pause')
def play_pause():
    '''
    fire play/pause button press at vlc
    '''
    vlc.pause()

    # telnet_command('pause')
    return jsonify(result=True)

@app.route('/_delete_video')
def delete_video():
    video = Video.load(request.args.get('videoId'))
    video.delete()

    return jsonify(result=True)

@app.route('/_play_video')
def play_video():
    vlc.play_video(request.args.get('videoId'), request.args.get('addedBy'), after=False) # todo: after should be True

    return jsonify(result=True) # {'title': vlc.crntVideo.title}) # probably won't be updated for a second

@app.route('/_get_video')
def get_video():
    return jsonify(result=vlc.get_video())

@app.route('/_raw_command')
def raw_command():
    ''' pass command directly to VLC, get rid of this later '''
    cmd = request.args.get('cmd')

    return jsonify(result=vlc.raw(cmd))

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

# @app.route('/_insert_in_queue')
# def insert_in_queue():
#     ''' insert a video into the queue '''
#     videoId = request.args.get('videoId')
#     addedBy = request.args.get('addedBy')
# 
#     vlc.play_video(videoId, addedBy, after=True)
# 
#     conn = sqlite3.connect('video.db')
#     with conn:
#         c = conn.cursor()
#         # make a gap by moving all videos after this one along one
#         c.execute('update queue set order = order + 1 where order > ?', (vlc.crntOrder, ))
#         # insert after current
#         # vlc.play_next(videoId)
#         # vlc.play_video(videoId)
#         c.execute('insert into queue (videoId, addedBy, [order]) values (?, ?, ?)', (videoId, addedBy, vlc.crntOrder + 1 ))
# 
#     return jsonify(result=True)

@app.route('/_auto_queue')
def auto_queue():
    ''' 
    currently: check if queue is down to one or less videos, then queue one
    todo: this doesn't need to be called from interface
    '''
    return jsonify(result=vlc.auto_queue())


# def play_queue():
#     conn = sqlite3.connect('video.db')
#     with conn:
#         c = conn.cursor()
#         c.execute('select * from queue order by order asc')
#         if(c.rowcount==0):
#             auto_queue()
#             return
# 
#         return jsonify(result=True)

@app.route('/_add_to_queue')
def add_to_queue():
    ''' add a video to the end of queue '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')

    return jsonify(result=vlc.play_video(videoId, addedBy))

@app.route('/_clear_queue')
def clear_queue():
    '''
    clear out the database queue
    '''
    return jsonify(result=vlc.clear_queue())


@app.route('/_get_queue')
def get_queue():
    '''return current queue to client'''

    return jsonify(result=vlc.get_queue())




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
    '''
    download video and set default rating in db
    todo: big cleanup
    '''
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
        youtubeResponse = result

    # not sure where to find the actual filename it was saved as
    # todo: this is dumb
    # badChars = '"\'/&'
    filename = (youtubeResponse['title'] + ' - ' + youtubeResponse['id']).replace('"','\'').replace('/','_')

    

    # test if we had to merge the files into an mkv
    # todo: clean up
    try:
        print('trying downloads/' + filename + '.' + youtubeResponse['ext'])
        my_file = Path('downloads/'+ filename + '.' + youtubeResponse['ext']) # use os.join
        if not my_file.is_file():
            print(youtubeResponse['ext'] + ' not found trying mkv')
        else:
            filename += '.'+youtubeResponse['ext']

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
    title = youtubeResponse['title'].replace('(Music Video)','').replace('(Official Video)', '').replace('(Official Music Video)', '')
    vid = Video(title=title, filename=filename, addedBy=addedBy, url=url)

    return jsonify(result=vid)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':

    app.debug = True
    app.run(host= '0.0.0.0', port=80)
