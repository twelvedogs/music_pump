# -*- coding: utf-8 -*-
'''
    Video dl/player
    ~~~~~~~~~~~~~~

    FUCK THIS VLC SHIT, it's going in the bin
    move to pychromecast

    web site where user can
        add videos via youtube-dl
        remove videos via mv to deleted directory
        rate videos into database
        play videos via player, locally or remotely

    todo: re-create database if non-existant so can add to .gitignore
    todo: save often can't find filename and breaks
    todo: clear queue on launch (unless re-launched recently?)
    todo: multi directory support
    todo: refresh single video info div in the file list
    todo: scan directory and auto-add missing to db
    todo: !!!!! convert .webm or weird shit to mp4 !!!
    
'''
import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
from datetime import datetime
from pathlib import Path
import sqlite3
import os
import random
import time
import youtube_dl

from video import Video
from player import Player

import cfg

app = Flask(__name__)

# get an instance of the player class that knows how to talk to chromecasts
player = Player()

@app.route('/_get_length')
def get_length():
    '''
    get the length of the currently playing track
    used for slider animation and 
    '''
    return jsonify(result=player.crnt_video.length)


@app.route('/_delete_video')
def delete_video():
    video = Video.load(request.args.get('videoId'))
    video.delete()
    # TODO: remove from queue
    # TODO: update list
    return jsonify(result=True)

#controls

@app.route('/_next')
def next():
    '''
    next button
    '''
    return jsonify(player.next())

@app.route('/_prev')
def prev():
    '''
    prev button
    '''
    return jsonify(player.prev())

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
    # after = request.args.get('after')=='True' # after is false if param "after" != "True"

    player.queue_video(request.args.get('videoId'), request.args.get('addedBy'))

    return jsonify(result=True) # {'title': player.crntVideo.title})


@app.route('/_get_play_targets')
def get_play_targets():

    targets = Player.get_play_targets()

    # after = request.args.get('after')=='True' # after is false if param "after" != "true"
    # player.play_video(request.args.get('videoId'), request.args.get('addedBy'), after=after)

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
    return jsonify(result=player.get_video())

@app.route('/_rate')
def rate_video():
    # TODO: validate input
    # TODO: video.rate(id, rating)
    videoId = request.args.get('videoId')
    rating = request.args.get('rating')

    conn = sqlite3.connect(cfg.db_path)
    with conn:
        c = conn.cursor()

        c.execute('update video set rating=? where videoId=?', (rating, videoId))

    return jsonify(result=list_videos())

@app.route('/_process_queue')
def process_queue():
    ''' 
    play the queue
    '''
    return jsonify(result=player.process_queue())

@app.route('/_add_to_queue')
def add_to_queue():
    '''
    add a video to the end of queue
    '''
    videoId = request.args.get('videoId')
    addedBy = request.args.get('addedBy')

    return jsonify(result=player.queue_video(videoId, addedBy))

@app.route('/_clear_queue')
def clear_queue():
    '''
    clear out the database queue
    '''
    return jsonify(result=player.clear_queue())


@app.route('/_get_queue')
def get_queue():
    '''
    return current queue to client
    '''

    return jsonify(result=player.get_queue())


@app.route('/_list_videos')
def list_videos():
    '''
    return big video list to client
    # TODO: video.get_all() or something
    '''
    # Video.get_all()
    conn = sqlite3.connect(cfg.db_path)
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

    # todo: need to specify download format of h264 for rpi & chromecast
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
    # todo: this is dumb, maybe have a list of banned phrases
    title = youtubeResponse['title'].replace('(Music Video)','').replace('(Official Video)', '').replace('(Official Music Video)', '')
    vid = Video(title=title, filename=filename, dateAdded=datetime.now(), addedBy=addedBy, url=url)
    vid.save()
    
    return str(vid) #jsonify(result=vid)

# allow downloads from directory, should be just served by the webserver
@app.route('/downloads/<path:path>')
def send_js(path):
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
    app.debug = False
    # this isn't setting the ip/port correctly
    app.run(host= '0.0.0.0', port=80)
