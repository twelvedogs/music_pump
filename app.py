# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~
    web site where user can
        add videos via youtube-dl
        remove videos via mv to deleted directory
        rate videos into database
        play videos via player, locally or remotely

    TODO: thumbnails like
          ffmpeg -i InputFile.FLV -vframes 1 -an       -s 400x222 -ss 30 OutputFile.jpg
                                  1 frame    no audio  size       30 sec in
    TODO: re-create database if non-existant so can add to .gitignore
    TODO: youtube-dl functionality often can't find filename and breaks
    TODO: block youtube-dl while downloading
    TODO: clear queue on launch (unless re-launched recently?)
    TODO: multi directory support
    TODO: refresh single video info div in the file list
    TODO: improve directory scan to have smarter file name matching
    TODO: update player area to show progress etc
    TODO: multiple files for each video
    TODO: popup file info
    TODO: add filtering on mature/user
    TODO: add videojs
    TODO: WEBSOCKETS!
    TODO: db backups
    TODO: list box to the right of the songs list, can drag songs in to create playlist (name box at top, save at bottom), adding playlist just jams all the songs at the end of current playlist, playlists just show up at top of song list
    TODO: remove black bars from videos in convert function
    TODO: store youtube data blob
    TODO: youtube search rather than just input file
    TODO: remove all content that may cause some kind of strike
'''
import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
# from flask_socketio import SocketIO, emit
from videoprops import get_video_properties
from datetime import datetime
from pathlib import Path
import sqlite3
import os
import subprocess
import random
import time
import youtube_dl
import json

from video import Video
from player import Player

import cfg

app = Flask(__name__)

# get an instance of the player class that knows how to talk to chromecasts
player = Player()

@app.route('/_scan_folder')
def scan_folder():
    scanpath = cfg.path
    # exclude directories
    files = [f for f in os.listdir(scanpath) if os.path.isfile(os.path.join(scanpath, f))]
    for file in files:
        lastDot = file.rindex('.')
        extension = file[lastDot:]
        if(extension.lower() == '.mp4' or extension.lower() == '.mkv'):
            # TODO: should probably use an in-memory file list
            if(Video.find_by_filename(file) == None):
                vid = Video(0, file, file, addedBy='Folder Scan')
                vid.save()
                print('added', file[:lastDot], file[lastDot:])

        else:
            print('not adding '+file+' wrong file type')

        time.sleep(0.01) # i'm abusing the shit out of the db so ease off a bit

    return jsonify(files=files)

@app.route('/_get_length')
def get_length():
    '''
    get the length of the currently playing track
    used for slider animation and 
    '''
    return jsonify(result=player.crnt_video.length)

@app.route('/_set_queue_position')
def set_queue_position():
    '''
    this works ridiculously well, must be something wrong lol
    TODO: what happens when we're out of queue bounds - probably nothing since they'd have to provide an order that is out of bound manually
    '''
    order = int(request.args.get('order'))
    player.crnt_order = order - 1
    player.advance_queue()
    
    return jsonify(result=True)


@app.route('/_get_file_info')
def get_file_info():
    video = Video.load(request.args.get('videoId'))
    video.file_properties = get_video_properties(cfg.path + video.filename)
    video.save()
    return jsonify(video = dict.copy(video.__dict__))

@app.route('/_delete_video')
def delete_video():
    delete_file = request.args.get('delete_file', bool)
    video = Video.load(request.args.get('videoId'))
    video.delete(delete_file=delete_file)
    # return jsonify(videos=Video.get_all())
    return list_videos()

#controls
# these can probably be collapsed into something like player_command('next')
@app.route('/_next')
def next():
    '''
    next button
    '''
    # player.play_next()

    return jsonify(video=player.play_next(), queue=player.get_queue())

@app.route('/_prev')
def prev():
    '''
    prev button
    '''
    return jsonify(video=player.play_prev(), queue=player.get_queue())

@app.route('/_play_pause')
def play_pause():
    '''
    play/pause button
    '''
    return jsonify(player.play_pause())

@app.route('/_stop')
def stop():
    '''
    stop button
    '''
    return jsonify(player.stop())

@app.route('/_play_video')
def play_video():
    '''
    play video on current player by videoId
    '''
    added_by = request.args.get('addedBy')
    video_id = request.args.get('videoId')
    
    player.insert_video_in_queue(video_id, added_by)

    return jsonify(video=player.play_next(), queue=player.get_queue()) # {'title': player.crntVideo.title})

# TODO: rename _queue_video
@app.route('/_add_to_queue')
def add_to_queue():
    '''
    add a video to the end of queue
    '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')
    player.queue_video(videoId, addedBy)

    return jsonify(queue=player.get_queue())

@app.route('/_get_play_targets')
def get_play_targets():
    targets = Player.get_play_targets()

    return jsonify(result=targets) # {'title': player.crntVideo.title}) # probably won't be updated for a second


@app.route('/_get_status')
def get_status():
    '''
    get all information required to update the interface
    todo: should this just be maintained and returned when requested?
            probably just return player
    '''
    result = {}
    result.video = player.get_video()
    result.queue = player.get_queue()

    return jsonify(result=result)

@app.route('/_get_video')
def get_video():
    return jsonify(video=player.get_video())

@app.route('/_subtitles')
def subtitles():
    return """WEBVTT

00:00.000 --> 00:13.000
<v Roger Bingham>We are in New York City
"""

@app.route('/_rate')
def rate_video():
    videoId = request.args.get('videoId')
    rating = request.args.get('rating')

    conn = sqlite3.connect(cfg.db_path)
    with conn:
        c = conn.cursor()
        c.execute('update video set rating=? where videoId=?', (rating, videoId))

    return list_videos()
    # return jsonify(videos=Video.get_all())

@app.route('/_process_queue')
def process_queue():
    ''' 
    play the queue
    TODO: this doesn't work, what should it even do?
    '''
    return jsonify(result=player.process_queue())


@app.route('/_clear_queue')
def clear_queue():
    '''
    clear out the database queue
    '''
    player.clear_queue()
    return jsonify(queue=[])


@app.route('/_get_queue')
def get_queue():
    '''
    return current queue to client
    '''

    return jsonify(queue=player.get_queue())


@app.route('/_list_videos')
def list_videos():
    '''
    return big video list to client
    # TODO: video.get_all() or something
    '''
    return jsonify(videos= Video.get_all())


def ydlhook(s):
    ''' 
    just printing atm, need to pass back to clients 
    TODO: status via websocket
    '''
    try:
        if(s['status']!='finished'):
            print('ydlhook: ' + s['_percent_str'])
    except:
        print('ydlhook failed: ', s)


@app.route('/_clean_video_list')
def clean_video_list():
    ''' cull bad entries and other cleanup stuff'''
    conn = sqlite3.connect(cfg.db_path)
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

@app.route('/_convert_video')
def convert_video():
    # TODO: block this from being accessed more than once
    # TODO: check for black bars with "ffmpeg -ss 90 -i input.mp4 -vframes 10 -vf cropdetect -f null -" from https://superuser.com/questions/810471/remove-mp4-video-top-and-bottom-black-bars-using-ffmpeg and change crop on vlc to match
    # TODO: check original resolution, don't change if under 1080p
    # TODO: check not overwriting lowercase filename
    videoId = request.args.get('videoId', '', type=int)
    video = Video.load(videoId)
    lastDot = video.filename.rindex('.')
    newfilename = video.filename[:lastDot] + '.mp4'

    print('ffmpeg -y -i "downloads/'+video.filename+'" -vf scale=1920:-1 "downloads/' + newfilename + '"' )
    
    if(video.filename == newfilename):
        print('don\'t want to overwrite')
        return jsonify(result=False)

    print('gonna convert up "' + video.filename + '" to "' + newfilename +'"')
    # TODO: make os independent
    os.chdir('F://code//music_pump//')

    # this actually blocks
    subprocess.call(['ffmpeg', '-y', '-i', 'downloads/' + video.filename, '-vf', 'scale=1920:-1', 'downloads/' + newfilename])
    
    print('finished')

    video.filename=newfilename
    video.save()

    return jsonify(result=True)

@app.route('/_download_video')
def download_video():
    '''
    download video and set default rating in db
    TODO: big cleanup
    TODO: move out of this file
    '''
    url = request.args.get('url', '', type=str)
    addedBy = request.args.get('addedBy', '', type=str)

    isPlaylist = url.find('&list=')
    if(isPlaylist>-1):
        url=url[0:isPlaylist]

    # todo: need to specify download format of h264 for rpi & chromecast - probably just convert file as specifying format will get lower quality
    # todo: need to catch malformed url
    # todo: check if folder exists probably
    ydl = youtube_dl.YoutubeDL({'outtmpl': cfg.path + '%(title)s - %(id)s.%(ext)s', 
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
    # todo: this is dumb, pull name from youtube dl somehow (who knows)
    # badChars = '"\'/&|'
    filename = (youtubeResponse['title'] + ' - ' + youtubeResponse['id']).replace('"','\'').replace('/','_').replace('|','_').replace('__','_')
	# todo: youtubedl replaces multiple underscores with a single underscore
    # test if we had to merge the files into an mkv
    # todo: clean up
    try:
        logging.info('looking for downloaded video at \"%s%s.%s\" ', cfg.path, filename, youtubeResponse['ext'])
        my_file = Path(cfg.path + filename + '.' + youtubeResponse['ext']) # use os.join
        if not my_file.is_file():
            logging.info('couldn\'t find \"%s%s.%s\"', cfg.path, filename, youtubeResponse['ext'])
            # print(youtubeResponse['ext'] + ' not found trying mkv')
        else:
            logging.info('found file \"%s%s.%s\" using youtube-dls extention', cfg.path, filename, youtubeResponse['ext'])
            filename += '.' + youtubeResponse['ext']

        # print('trying ' + cfg.path + filename + '.mkv')
        my_file = Path( cfg.path + filename + '.mkv') # use os.join
        if not my_file.is_file():
            logging.info('couldn\'t find ' + cfg.path + filename + '.mkv')
        else:
            logging.info('video found at ' + cfg.path + filename + '.mkv')
            filename += '.mkv'

    except Exception as err:
        logging.error('failed to determine filename error:\n %s', str(err))
        filename += '.webm' # pretty hacky, most likely couldn't find because webm though

    print('guessing filename should be: ' + filename)
    # strip stuff like (Official Video) from title
    # todo: this is dumb, maybe have a list of banned phrases, maybe just regex out everything between () or [] or ""
    title = youtubeResponse['title'].replace('(Music Video)','').replace('(Official Video)', '').replace('(Official Music Video)', '')
    vid = Video(title=title, filename=filename, dateAdded=datetime.now(), addedBy=addedBy, url=url)
    vid.save()
    # list_videos()
    return jsonify(videos = Video.get_all(), video = str(vid))

# allow downloads from directory, should be just served by the webserver
@app.route('/downloads/<path:path>')
def send_video(path):
    return send_from_directory('downloads', path)

@app.route('/')
def index():
    return render_template('index.html')

def setup_logging():
    logging.basicConfig(filename='app.log', level=logging.INFO)
    # logger = logging.get_logger()
    logging.info('Started')
    # shut up the werkzeug logger 
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

if __name__ == '__main__':
    setup_logging()
    #app.debug = False
    # this isn't setting the ip/port correctly
    app.run(host= '0.0.0.0', port=80)
    #socketio.run(sapp)

