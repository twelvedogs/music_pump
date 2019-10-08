import sqlite3


# this not being serialisable sucks balls
class Video:
    def __init__(self, videoId=0, title='', filename='', rating=3, lastPlayed=None, 
                dateAdded=None, mature=False, videoType='music', addedBy='Unknown', length = -1):
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
        self.length = length

    def __str__(self):
        return '{ videoId: \"' + str(self.videoId)  + '\", title: \"' + self.title  + '\", filename: \"' + self.filename + '\"}'

    def load(self, videoId=0):
        '''
        get database record for video by id
        '''
        conn = sqlite3.connect('video.db')
        with conn:
            c = conn.cursor()
            # videos=[]
            for row in c.execute('SELECT * FROM video where videoId = ? ORDER BY dateAdded desc', (videoId,)):
                video = Video(videoId = row[0], title = row[1], filename = row[2], rating = row[3], lastPlayed = row[4], dateAdded = row[5], mature = row[6], videoType = row[7], addedBy = row[8])
                # videos += video
                return video

            return None


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

