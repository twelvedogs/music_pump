# -*- coding: utf-8 -*-

import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
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

def scan_folder_for_missing():
    scanpath = cfg.download_path
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

def ydlhook(s):
    ''' 
    just printing atm, need to pass back to clients 
    TODO: status via websocket
    '''
    try:
        if(s['status']!='finished'):
            print('ydlhook: ' + s['_percent_str'])
            # sio.emit('my_response', {'data':  s['_percent_str']})
            # announce to websocket
    except:
        print('ydlhook failed: ', s)

def remove_duplicate_entries():
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

def convert_video(videoId):
    # note: this doesn't block, subprocess.call is probably a different thread
    # TODO: stop this from being accessed more than once
    # TODO: check for black bars with "ffmpeg -ss 90 -i input.mp4 -vframes 10 -vf cropdetect -f null -" from https://superuser.com/questions/810471/remove-mp4-video-top-and-bottom-black-bars-using-ffmpeg and change crop on vlc to match
    # TODO: check original resolution, don't change if under 1080p
    # TODO: check not overwriting lowercase filename
    video = Video.load(videoId)
    lastDot = video.filename.rindex('.')
    # not sure i'm happy with this rename
    newfilename = video.filename[:lastDot] + '_h264.mp4'

    print('ffmpeg -y -i "downloads/'+video.filename+'" -vf scale=1920:-1 "downloads/' + newfilename + '"' )
    
    if(video.filename == newfilename):
        print('don\'t want to overwrite')
        return jsonify(result=False)

    print('gonna convert up "' + video.filename + '" to "' + newfilename +'"')
    # TODO: make os independent
    os.chdir(cfg.path) # 'F://code//music_pump//'

    # the scale thing doesn't add black bars or anything dumb
    subprocess.call(['ffmpeg', '-y', '-i', cfg.download_path + video.filename, '-vf', 'scale=1920:-1', cfg.download_path + newfilename])
    
    print('finished')

    video.filename=newfilename
    video.save()

    return True

def do_download(url, addedBy):
    
    isPlaylist = url.find('&list=')
    if(isPlaylist>-1):
        url=url[0:isPlaylist]

    # TODO: need h264 for rpi & chromecast - probably just convert file as specifying format will get lower quality
    # TODO: need to catch malformed url
    # TODO: check if folder exists probably
    # TODO: this is blocking, stop that
    ydl = youtube_dl.YoutubeDL({'outtmpl': cfg.download_path + '%(title)s - %(id)s.%(ext)s', 
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
        logging.info('looking for downloaded video at \"%s%s.%s\" ', cfg.download_path, filename, youtubeResponse['ext'])
        my_file = Path(cfg.download_path + filename + '.' + youtubeResponse['ext']) # use os.join
        if not my_file.is_file():
            logging.info('couldn\'t find \"%s%s.%s\"', cfg.download_path, filename, youtubeResponse['ext'])
            # print(youtubeResponse['ext'] + ' not found trying mkv')
        else:
            logging.info('found file \"%s%s.%s\" using youtube-dls extention', cfg.download_path, filename, youtubeResponse['ext'])
            filename += '.' + youtubeResponse['ext']

        # print('trying ' + cfg.path + filename + '.mkv')
        my_file = Path( cfg.download_path + filename + '.mkv') # use os.join
        if not my_file.is_file():
            logging.info('couldn\'t find ' + cfg.download_path + filename + '.mkv')
        else:
            logging.info('video found at ' + cfg.download_path + filename + '.mkv')
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

