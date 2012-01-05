import time
import random
from datetime import datetime
from datetime import timedelta
from pdb import set_trace as bp

import pymongo
from pymongo import Connection
import pdb
pdb.set_trace()

import lib.reddit as reddit

"""
3. During an update of the list of tracked submissions:
    --Fetch the context (ie. the ordering of other submissions in the subreddit) and create a cached version of SubredditContext object
    --Fetch the next submission and all comments
    --Create SubmissionDatums and CommentDatums
    --If the heuristically calculated activity level of the submission falls below a threshold, disable tracking for that submission
    --Update the cached SubredditContext once every time interval t
"""

"""
-=Update Loop Pseudocode=-
MIN_TRACKING_TIME = timespan(24,0,0)
tracked_submissions = get_tracked_submissions(subreddit)
last_context_update = datetime.now()
context_expiry_interval = timespan(0,0,10)

for sub in tracked_submissions:
    if last_context_update - datetime.now() > context_expiry_interval:
        context = fetch_context(subreddit)
        last_context_update = datetime.now()
    new_sub_data = fetch_submission(sub.url)
    sub = process_submission(new_sub_data)
    if datetime.now() - sub.tracking_start_date > MIN_TRACKING_TIME:
        if is_activity_is_dead(sub):
            sub.tracking = false
            sub.save()
"""


#init mongoDB
dbname = 'redditeye'
conn = Connection()
db = conn[dbname]

db.drop_collection('Trials')
db.drop_collection('SubmissionDatums')
db.drop_collection('SubReddits')


class RedditTrial:
    def Init(self, subreddit_name, db, 
                    min_submission_tracking_time,
                    reddit_request_interval,
                    max_submission_age_for_start_tracking):
        
        self.db = db
        self.subreddit_name = subreddit_name
        self.reddit = reddit.Reddit('REDDITEYE -- version alpha')

        self.subreddit = self.reddit.get_subreddit(subreddit_name)
        log('subreddit retrieved...')
        self.min_submission_tracking_time = min_submission_tracking_time
        self.reddit_request_interval = reddit_request_interval
        self.max_submission_age_for_start_tracking = max_submission_age_for_start_tracking

        self.timer = MinRequestTime(timedelta(0,30))  #one minute
        #self.timer = MinRequestTime(timedelta(0,60))  #one minute

class MultipleSubmissionTrial(RedditTrial):
    _NUM_SUBMISSIONS_TO_FETCH = 50
    
    def __init__(self, subreddit_name, db, 
                    min_submission_tracking_time=timedelta(0,2*60*60),
                    reddit_request_interval=timedelta(0, 10*60),
                    max_submission_age_for_start_tracking=timedelta(0, 60*60),
                    tracked_submissions_limit=10):

        self.Init(subreddit_name, db, min_submission_tracking_time, reddit_request_interval, max_submission_age_for_start_tracking)
        self.tracked_submissions_limit = tracked_submissions_limit
        
        self._init_trial()
        self._refresh_subreddit()
        self._choose_tracked_submissions()
        
        self.start_loop()

    def _refresh_trial(self):
        self.trial = db.Trials.find_one({'_id' : self.trial_oid})

    def _start_tracking_submission(self, r_submission):
        #not sure why but each time we're getting different types for r_sub.author
        if type(r_sub.author) == unicode:
            name = r_sub.author
        else:
            name = r_sub.author.name
        
        s = {
            'r_content_id' : r_sub.content_id,
            'r_id' : r_sub.id,
            'author' : name,
            'title' : r_sub.title,
            'selftext' : r_sub.selftext,
            'submission_date' : datetime.fromtimestamp(r_sub.created),
            'submission_date_utc' : datetime.fromtimestamp(r_sub.created_utc),
            'subreddit_name' : self.r_subreddit.title,
            'tracking' : True,
            'tracking_start_date' : datetime.now(),
            'url' : r_sub.url,
            'is_self' : r_sub.is_self
        } 
        
        #self._refresh_trial()
        db.Trials.update({'_id' : self.trial_oid}, {'$push' : {'submissions': s}})
        db.save()

        return s


    def _stop_tracking_submission(self, content_id):
        db.Trials.update({'_id' : self.trial_oid}, {'$pull' : {'submissions' : {'r_content_id': content_id}}})


    def _refresh_subreddit(self):
        self.r_subreddit = self.reddit.get_subreddit(self.subreddit_name)
        sr = db.SubReddits.find_one({'name':self.subreddit_name})
        if sr:
            self.subreddit = sr
        else: 
            sr = {'name':self.subreddit_name, 'url':self.r_subreddit.url, 'subscribers':self.r_subreddit.subscribers}
            db.SubReddits.insert(sr)
            self.subreddit = sr
    
    def _select_tracked_submissions(self):
        self._refresh_trial()
        _submissions = self.trial['submissions']
        
        subs = [] + _submissions
        if len(submissions) >= self.self.tracked_submissions_limit:
            return

        new_subs = self.r_subreddit.get_new()
        for r_sub in new_subs:
            created_on = datetime.fromtimestamp(r_sub.created)
            if datetime.now() - created_on < self.max_submission_age_for_start_tracking:
                log('tracking submission: %s' % r_sub.title)
                sub = self._start_tracking_submission(r_sub)
                subs.append(sub)
                if len(subs) >= self.tracked_submissions_limit:
                    break
    
    def _init_trial(self):
        t = {
            'startdate' : datetime.now(),
            'finishdate' : None,
            'min_submission_track_seconds' : flatten_to_seconds(self.min_submission_tracking_time),
        }

        self.trial_oid = db.Trials.insert(t)
        self.trial = t

    #
    # MAIN LOOP
    #
    def start_loop(self):
        self.tracked_submissions = self._get_tracked_submissions()
        log('Starting monitoring.')
         
        #main fetching loop (continue until not tracking any submissions)
        while self.tracked_submissions:
            self._select_tracked_submissions()
            self.reset_subreddit()

            log('fetching update at %s...' % str(datetime.now()))
            self._process_submissions()
            
            self.tracked_submissions = self._get_tracked_submissions()
            self.timer.Wait()
        print 'DONE!'
   
    def _process_comments(self):
        for sub in self.tracked_submissions:
            if not sub['tracking_comments']: continue
            
            for r_comment in sub.all_comments:
                comment = make_comment_datum(self, r_sub, r_comment)

    def _process_submissions(self):
        _limit = self._NUM_SUBMISSIONS_TO_FETCH
        top_rsubs = list(self.r_subreddit.get_top(limit=_limit))
        hot_rsubs = list(self.r_subreddit.get_hot(limit=_limit))
        new_rsubs = list(self.r_subreddit.get_new(limit=_limit))
        
        for sub in self.tracked_submissions:
            log('processing submission: %s' % sub['title'])
            if not sub['tracking']: continue
            top_pos, hot_pos, new_pos = -1, -1, -1
            match = lambda rsub: rsub.content_id == sub['r_content_id']
            _top_rsubs = filter(match, top_rsubs)
            _hot_rsubs = filter(match, hot_rsubs)
            _new_rsubs = filter(match, new_rsubs)

            rsub = None 
            if _top_rsubs or _hot_rsubs or _new_rsubs:
                _rsubs = _top_rsubs + _hot_rsubs + _new_rsubs
                rsub = _rsubs[0]
            else:
                #fix this to update via mongoDB
                db.Trials.update(
                    {'submissions.r_content_id' : sub['r_content_id'], '_id': self.trial['_id'] }, 
                    { '$set' : {'submissions.$.tracking': False, 'submissions.$.tracking_comments' : False}})
                rsub = self.reddit.get_submission(submission_id=sub['r_id'])

            if _top_rsubs:
                top_pos = top_rsubs.index(_top_rsubs[0])
            
            if _hot_rsubs:
                hot_pos = hot_rsubs.index(_hot_rsubs[0])
            
            if _new_rsubs:
                new_pos = new_rsubs.index(_new_rsubs[0])

            self.make_submission_datum(rsub, hot_pos, top_pos, new_pos)

    def _get_tracked_submissions(self):
        self._refresh_trial()
        subs = self.trial['submissions']
        return filter(lambda sub: sub['tracking'] or sub['tracking_comments'], subs)

    def make_submission_datum(self, r_sub, position_hot, position_top, position_new):
        sub_datum = {
            'comment_count' : r_sub.num_comments,
            'upvotes' : r_sub.ups,
            'downvotes' : r_sub.downs,
            'score' : r_sub.score,
            'r_content_id' : r_sub.content_id,
            'id' : r_sub.id,
            'fetch_date' : datetime.now(),
            'position_hot' : position_hot,
            'position_top' : position_top,
            'position_new' : position_new,
        }
        
        self.db.SubmissionDatums.insert(sub_datum)
        return sub_datum 
    
    def make_comment_datum(self, r_sub, r_comment):
        #if comment document doesn't already exist in db, create it
        comments = self.db.Comments.find({'r_content_id':r_comment.content_id})
        if comments:
            comment = comments[0]
        else:
            comment = self.db.Comment()
            comment.r_content_id = r_comment.content_id
            comment.r_sub_cid = r_sub.content_id
            comment.author = r_comment.author
            comment.r_parent_id = r_comment.parent_id
            comment.created = r_comment.created
            comment.created_utc = r_comment.created_utc
            comment.save()

        #make the comment datum
        cdatum = db.CommentDatum()
        cdatum.comment_oid
        cdatum.fetch_date = datetime.now()
        cdatum.upvotes = r_comment.upvotes
        cdatum.downvotes = r_comment.downvotes
        return cdatum
    
def output_submission_datums(datums):
    time_zero = datums[0]['fetch_date']

    print ''
    for datum in datums:
        minutes = (datum['fetch_date'] - time_zero).seconds / 60.0
        row = [ minutes, datum['position_hot'], datum['position_new'], datum['position_top'], 
                datum['comment_count'], datum['score'], datum['upvotes'], datum['downvotes']]
        row = map(lambda i: str(i), row)
        print ', '.join(row)

        #'submission_oid' : ObjectId,
        #'r_content_id': unicode,
        #'comment_count' : int,
        #'upvotes' : int,
        #'downvotes' : int,
        #'score' : int,
        #'fetch_date' : datetime,
        #'position_hot' : int,
        #'position_new' : int,
        #'position_top' : int,

class MinRequestTime():
    def __init__(self, time):
       self.minTime = time

    def Wait (self):
        print '.'
        time.sleep(self.minTime.seconds)

class SubmissionSortTypes:
    HOT = u'hot'
    NEW = u'new'
    TOP = u'top'

    @staticmethod
    def get_list():
        return [SubmissionSortTypes.HOT,SubmissionSortTypes.NEW, SubmissionSortTypes.TOP] 

class CommentSortTypes:
    BEST = u'best'
    HOT = u'hot'
    NEW = u'new'
    TOP = u'top'
    CONTROVERSIAL = u'controversial'
    @staticmethod
    def get_list():
        return [CommentSortTypes.BEST , CommentSortTypes.HOT ,CommentSortTypes.NEW ,CommentSortTypes.TOP]
    
def flatten_to_seconds(timedel):
    return timedel.seconds + timedel.days * 86400

def log(string):
    print string

def PrintDatums():
    datums = db.SubmissionDatums.find({'r_content_id':'t3_o0r3l'})
    output_submission_datums(datums)

def Test():
    trial = MultipleSubmissionTrial('AskReddit', db, tracked_submissions_limit=50)


def Run():
    Test()





if __name__ == "__main__":
    Run()



