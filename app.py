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
    TODO: multiple files for each video?
    TODO: popup file info
    TODO: add filtering on mature/user
    TODO: add videojs
    TODO: db backups
    TODO: list box to the right of the songs list, can drag songs in to create playlist (name box at top, save at bottom), adding playlist just jams all the songs at the end of current playlist, playlists just show up at top of song list
    TODO: remove black bars from videos in convert function
    TODO: store youtube data blob
    TODO: youtube search rather than just input file
    TODO: remove all content that may cause some kind of strike
    TODO: deal with currently playing on chromecast video on restart
'''



import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
# from flask_socketio import SocketIO, emit
# from videoprops import get_video_properties
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

import cfg, file_utility

app = Flask(__name__)

# get an instance of the player class that knows how to talk to chromecasts
player = Player()

@app.route('/_scan_folder')
def scan_folder():
    file_utility.scan_folder_for_missing()

    return jsonify(files=Video.get_all())

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
    order = request.args.get('order', type=int)
    player.crnt_order = order - 1
    player.advance_queue()
    
    return jsonify(queue=player.get_queue())


@app.route('/_get_file_info')
def get_file_info():
    
    video = Video.load(request.args.get('videoId', type=int))
    video.update_file_properties()

    return jsonify(video = dict.copy(video.__dict__))

@app.route('/_delete_video')
def delete_video():
    delete_file = request.args.get('delete_file', type=bool)
    video = Video.load(request.args.get('videoId', type=int))
    video.delete(delete_file=delete_file)
    # return jsonify(videos=Video.get_all())
    return jsonify(video = str(video), videos = Video.get_all())

#controls
# these can probably be collapsed into something like player_command('next')
@app.route('/_next')
def next():
    '''
    next button
    '''
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
    add video with videoId after this and then go to queue next
    '''
    added_by = request.args.get('addedBy', str)
    video_id = request.args.get('videoId', int)
    
    player.insert_video_in_queue(video_id, added_by)

    return jsonify(video=player.play_next(), queue=player.get_queue()) # {'title': player.crntVideo.title})

# TODO: rename _queue_video
@app.route('/_queue_video')
def queue_video():
    '''
    add a video to the end of queue
    '''
    videoId = request.args.get('videoId', int)
    addedBy = request.args.get('addedBy', str)
    # can i just put this in the __str__ function?
    video = dict.copy(player.queue_video(videoId, addedBy).__dict__)
    #                 return dict.copy(self.crnt_video.__dict__)
    return jsonify(video = video, queue=player.get_queue())

@app.route('/_set_play_target')
def set_play_target():
    device_id = request.args.get('device_id', type=int)
    player.set_play_target(device_id)

@app.route('/_get_play_targets')
def get_play_targets():
    targets = Player.get_play_targets()

    return jsonify(result=targets) # {'title': player.crntVideo.title}) # probably won't be updated for a second

# TODO: rename to _get_video or something
@app.route('/_get_video_by_id')
def get_video_by_id():

    videoId = request.args.get('videoId', type=int)

    return jsonify(Video.load(videoId).__dict__)

    # return jsonify(time_started= player.time_started, video=player.get_video())

@app.route('/_get_status')
def get_status():
    '''
    get all information required to update the interface
    todo: should this just be maintained and returned when requested?
            probably just return player
    '''

    download_status = {'url': 'http://youtube.com/whatevs', 'progress': 50 }

    return jsonify(video = player.get_video(), queue = player.get_queue(), download_status = download_status)

# TODO: rename to _get_status or something
@app.route('/_get_video')
def get_video():
    client_queue_last_updated = request.args.get('queue_last_updated', type=int)

    obj = {'time_started': player.time_started, 'video': player.get_video()}

    if(client_queue_last_updated<player.queue_last_updated):
        obj['queue'] = player.get_queue()

    #if(client_files_last_updated<player):
    #    obj.videos = Video.get_all()

    return jsonify(obj)

@app.route('/_subtitles')
def subtitles():
    return """WEBVTT

00:00.000 --> 00:13.000
<v Roger Bingham>We are in New York City
"""

@app.route('/_rate')
def rate_video():
    videoId = request.args.get('videoId', type=int)
    rating = request.args.get('rating', type=int)

    # Video.set_rating(videoId, rating)
    conn = sqlite3.connect(cfg.db_path)
    with conn:
        c = conn.cursor()
        c.execute('update video set rating=? where videoId=?', (rating, videoId))

    return jsonify(videos=Video.get_all())

def long_running_test():
    # probably call websocket to make sure it's running
    print('doing a long running test')
    time.sleep(15)

@app.route('/_process_queue')
def process_queue():
    ''' 
    play the queue
    TODO: this doesn't work, what should it even do?
    '''
    long_running_test()

    return jsonify(True)


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
    '''
    return jsonify(videos= Video.get_all())


@app.route('/_clean_video_list')
def clean_video_list():
    ''' cull bad entries and other cleanup stuff'''
    file_utility.remove_duplicate_entries()

    return jsonify(result=True)

@app.route('/_convert_video')
def convert_video():
    # TODO: stop this from being accessed more than once
    # TODO: check for black bars with "ffmpeg -ss 90 -i input.mp4 -vframes 10 -vf cropdetect -f null -" from https://superuser.com/questions/810471/remove-mp4-video-top-and-bottom-black-bars-using-ffmpeg and change crop on vlc to match
    # TODO: check original resolution, don't change if under 1080p
    # TODO: check not overwriting lowercase filename
    videoId = request.args.get('videoId', '', type=int)
    file_utility.convert_video(videoId)
    
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

    file_utility.do_download(url, addedBy)

    # sio.start_background_task(do_download, url, addedBy)
    # eventlet.greenthread.spawn(do_download, url, addedBy)

    return jsonify(videos = Video.get_all())

# allow downloads from directory, should be just served by the webserver
@app.route('/downloads/<path:path>')
def send_video(path):
    return send_from_directory('downloads', path)

@app.route('/')
def index():
    return render_template('index.html')

#controls
# these can probably be collapsed into something like player_command('next')
@app.route('/list')
def list():
    '''
    big video list page
    '''

    return render_template('list.html', videos=Video.get_all(order_by_date = True))

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
    app.run(host= '0.0.0.0', port=5000)
    #socketio.run(sapp)

