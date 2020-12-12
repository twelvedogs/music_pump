import os
import logging
import sqlite3
import cfg
from datetime import datetime
# from flask import jsonify
import json

# this not being serialisable sucks balls, there's probably a library for that
class Video:
    '''
    video class, represents a video you can play
    '''
    def __init__(self, videoId=0, title='', filename='', rating=3, lastPlayed='2000-01-01', 
                dateAdded=None, mature=False, videoType='music', addedBy='Unknown', length = -1, url='', file_properties = None):
        self.videoId = videoId
        self.title = title
        self.filename = filename
        self.rating = rating
        self.lastPlayed = lastPlayed
        if(dateAdded == None):
            dateAdded = datetime.now()
        self.dateAdded = dateAdded
        self.mature = mature
        self.videoType = videoType
        self.addedBy = addedBy
        self.length = length
        self.url = url
        self.file_properties = file_properties

    def __str__(self):
        return '{ \"videoId\": \"' + str(self.videoId) + '\", \"title\": \"' + self.title + '\", \"filename\": \"' + self.filename + '\",' + '\"length\": ' + str(self.length) + '}'
   
    @staticmethod
    def scan_folder():
        # if(path=='' or path==None):
        #     logging.error('scan_folder called with no filename')
        #     return None

        # exclude directories
        files = [f for f in os.listdir(cfg.path) if os.path.isfile(os.path.join(cfg.path, f))]
        for file in files:
            # print(file)
            if(Video.find_by_filename(file) == None):
                # TODO: addedBy, dateAdded
                vid = Video(0, file, file, addedBy="Folder Scan")
                vid.save()
                print('added', file)

    @staticmethod
    def find_by_filename(filename):
        if(filename=='' or filename==None):
            logging.error('find_by_filename called with no filename')
            return None

        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()
            # videos=[] # probably impliment search in another function
            for row in c.execute('SELECT * FROM video where filename like ? ORDER BY dateAdded desc', (filename,)):
                video = Video(videoId = row[0], title = row[1], filename = row[2], rating = row[3], lastPlayed = row[4], dateAdded = row[5], mature = row[6], videoType = row[7], addedBy = row[8])
                # videos += video
                return video

            logging.info('Video.find_by_filename - video not found in db with filename: ' + filename)
            return None

    @staticmethod
    def get_all():
        # Video.get_all()
        conn = sqlite3.connect(cfg.db_path)
        with conn:
            c = conn.cursor()

            videos = []

            # dunno if this can be simplified
            for row in c.execute('SELECT videoId, title, filename, rating, addedBy, file_properties FROM video ORDER BY videoId desc'):
                video = {}
                video['videoId'] = row[0]
                video['title'] = row[1]
                video['filename'] = row[2]
                video['rating'] = row[3]
                video['addedBy'] = row[4]
                if(row[5] != None):
                    video['file_properties'] = json.loads(row[5])
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
            for row in c.execute('SELECT * FROM video where videoId = ? ORDER BY dateAdded desc', (videoId,)):
                video = Video(videoId = row[0], title = row[1], filename = row[2], rating = row[3], lastPlayed = row[4], dateAdded = row[5], mature = row[6], videoType = row[7], addedBy = row[8])
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
            if(self.videoId>0):
                c.execute('update video set title=:title, filename=:filename, rating=:rating, lastPlayed=:lastPlayed, dateAdded=:dateAdded, mature=:mature, videoType=:videoType, addedBy=:addedBy, file_properties=:file_properties where videoId=:videoId', 
                    { 'title': self.title, 'filename': self.filename, 'rating': self.rating, 'lastPlayed': self.lastPlayed, 'dateAdded': self.dateAdded, 'mature': self.mature, 'videoType': self.videoType, 'addedBy': self.addedBy, 'videoId': self.videoId, 'file_properties': file_properties })
            else:
                c.execute('insert into video (title, filename, rating, lastPlayed, dateAdded, mature, videoType, addedBy) values (:title, :filename, :rating, :lastPlayed, :dateAdded, :mature, :videoType, :addedBy)', 
                    (self.title, self.filename, self.rating, self.lastPlayed, self.dateAdded, self.mature, self.videoType, self.addedBy))

