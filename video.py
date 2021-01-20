import os
import logging
import sqlite3
import cfg
from datetime import datetime
# from flask import jsonify
import json
from videoprops import get_video_properties


class Video:
    '''
    video class, represents a video you can play
    '''
    def __init__(self, videoId=0, title='', filename='', rating=3, lastPlayed='2000-01-01',
                 dateAdded=None, mature=False, videoType='music', addedBy='Unknown',
                 length=-1, url='', file_properties=None):
        self.videoId = videoId
        self.title = title
        self.filename = filename
        self.rating = rating
        self.lastPlayed = lastPlayed
        if(dateAdded is None):
            dateAdded = datetime.now()
        self.dateAdded = dateAdded
        self.mature = mature
        self.videoType = videoType
        self.addedBy = addedBy
        self.length = length
        self.url = url
        self.file_properties = file_properties

    def __str__(self):
        return '{ \"videoId\": \"' + str(self.videoId) + '\", \"title\": \"' + self.title + '\", \"filename\": \"' + \
            self.filename + '\",' + '\"length\": ' + str(self.length) + '}'

    @staticmethod
    def scan_folder():
        # if(path=='' or path==None):
        #     logging.error('scan_folder called with no filename')
        #     return None

        # exclude directories
        files = [f for f in os.listdir(cfg.path) if os.path.isfile(os.path.join(cfg.path, f))]
        for file in files:
            # print(file)
            if(Video.find_by_filename(file) is None):
                # TODO: addedBy, dateAdded
                vid = Video(0, file, file, addedBy="Folder Scan")
                vid.save()
                print('added', file)

    def update_file_properties(self):
        try:
            self.file_properties = get_video_properties(os.path.join(cfg.download_path, self.filename))
            # self.file_properties = get_video_properties(cfg.path + self.filename)
            # do the length
            length = -1
            try:
                length = self.file_properties['duration']
            except:
                logging.info('video.file_properties.duration error')

            if(length == -1):
                try:
                    arr = self.file_properties['tags']['DURATION'].split(':')
                    length = int(arr[0]) * 60 * 60 + int(arr[1]) * 60 + float(arr[2])
                except:
                    logging.info('video.file_properties.tags.DURATION error')

            self.length = length
            print(self)

            self.save()
            return True
        except:
            print('probably couldn\'t find' + self.filename)
            return False

    @staticmethod
    def find_by_filename(filename):
        if(filename == '' or filename is None):
            logging.error('find_by_filename called with no filename')
            return None

        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            # videos=[] # probably impliment search in another function
            for row in c.execute('SELECT * FROM video where filename like ? ORDER BY dateAdded desc', (filename,)):
                video = Video(videoId=row[0], title=row[1], filename=row[2], rating=row[3], lastPlayed=row[4],
                              dateAdded=row[5], mature=row[6], videoType=row[7], addedBy=row[8])
                # videos += video
                return video

            logging.info('Video.find_by_filename - video not found in db with filename: ' + filename)
            return None

    @staticmethod
    def get_all(order_by_date=False):
        # Video.get_all()
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()

            videos = []
            sql_str = 'SELECT videoId, title, filename, rating, addedBy, file_properties, length FROM video'
            if(order_by_date):
                sql_str = sql_str + ' ORDER BY dateAdded DESC'
            else:
                sql_str = sql_str + ' ORDER BY title COLLATE NOCASE asc'

            # dunno if this can be simplified
            for row in c.execute(sql_str):
                video = {}
                video['videoId'] = row[0]
                video['title'] = row[1]
                video['filename'] = row[2]
                video['rating'] = row[3]
                video['addedBy'] = row[4]
                if(row[5] is not None):
                    video['file_properties'] = json.loads(row[5])

                video['length'] = row[6]

                videos.append(video)

            return videos

    @staticmethod
    def load(videoId):
        '''
        get database record for video by id
        TODO: named columns
        '''
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            for row in c.execute('SELECT * FROM video where videoId=?', (videoId,)):
                video = Video(videoId=row[0], title=row[1], filename=row[2], rating=row[3], lastPlayed=row[4],
                              dateAdded=row[5], mature=row[6], videoType=row[7], addedBy=row[8],
                              url=row[9], file_properties=row[10], length=row[11])
                return video

            logging.error('Video.load - video id not found: ' + videoId)

            return None

    def delete(self, delete_file=False):
        '''
        deletes from db only
        TODO: move file to another folder and mark as deleted in db
        TODO: manage if currently playing video, update queue on player
        '''
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            c.execute('delete from video where videoId =:videoId;', (self.videoId, ))
            conn.commit()
            c.execute('delete from queue where videoId =:videoId;', (self.videoId, ))
            conn.commit()
        if(delete_file):
            os.remove(cfg.download_path + self.filename)

    def save(self):
        '''
        update video database record or create if videoId < 1
        '''

        file_properties = json.dumps(self.file_properties)
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()

            # could probably have some kind of simple object returned by a function on Video
            if(self.videoId > 0):
                c.execute('update video set title=:title, filename=:filename, rating=:rating, lastPlayed=:lastPlayed, dateAdded=:dateAdded, mature=:mature, videoType=:videoType, addedBy=:addedBy, file_properties=:file_properties, length=:length where videoId=:videoId',
                          {'title': self.title, 'filename': self.filename, 'rating': self.rating, 'lastPlayed': self.lastPlayed, 'dateAdded': self.dateAdded, 'mature': self.mature, 'videoType': self.videoType, 'addedBy': self.addedBy, 'videoId': self.videoId, 'file_properties': file_properties, 'length': self.length})
            else:
                c.execute('insert into video (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (:title, :filename, :rating, :lastPlayed, :dateAdded, :mature, :videoType, :addedBy)',
                          (self.title, self.filename, self.rating, self.lastPlayed, self.dateAdded, self.mature, self.videoType, self.addedBy))
