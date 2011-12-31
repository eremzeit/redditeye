from datetime import datetime
from pymongo.objectid import ObjectID
from mongokit import *
import redditapi as reddit


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

#init redditapi


import random
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



class MultipleSubmissionTrial(object):
    _MIN_SUBMISSION_TRACKING_TIME = timespan(24,0,0)
    _REDDIT_REQUEST_INTERVAL = timespan(0,0,4)


    def __init__(self, subreddit_name, db, 
                    min_submission_tracking_time=timedelta(0,2*60*60),
                    reddit_request_interval=timedelta(0, 10*60),
                    max_submission_age_for_start_tracking=timedelta(0, 10*60),
                    tracked_submissions_limit=10):
        self.subreddit_name = subreddit_name
        self.reddit = reddit.Reddit('REDDITEYE -- version alpha')
        self.reddit.login(user='redditeye', password='redditeye')
        self.r_subreddit = self.reddit.get_subreddit(subreddit_name)
        self.subreddit = self.process_subreddit(self.r_subreddit)
        
        self.min_submission_tracking_time = min_submission_tracking_time
        self.reddit_request_interval = reddit_request_interval
        self.max_submission_age_for_start_tracking = max_submission_age_for_start_tracking
        self.tracked_submissions_limit = tracked_submissions_limit
        #self.initial_tracked_submissions = self._initial_tracked_submissions()
    
    def process_subreddit(self, r_subreddit):
        raise Exception()

    def _initial_tracked_submissions(self, trial_id):
        """ 
        Make Submission objects


        This is arbitrary, but mainly we want to:
            -exclude any submissions we are already tracking
            -exclude any submissions older than a few minutes
            -keep the number of tracked items to a minimum at first
        """

        tracked_submissions = []
        new_subs = self.r_subreddit.get_new()
        for r_sub in new_subs:
            created_on = datetime.fromtimestamp(r_sub.created)
            if datetime.now() - created_on < self.max_submission_age_for_start_tracking:
                self.init_submission(r_sub, trial_id)
            else:
                pass

    def init_submission(self, r_sub, now, trial_id, position_hot, position_top, position_new):
        submission = self.db.Submission()
        submission.r_content_id = r_sub.content_id
        submission.r_id = r_sub.id
        submission.author = r_sub.author.user_name
        submission.title = r_sub.title
        submission.selftext = r_sub.selftext
        submission.submission_date = datetime.fromtimestamp(r_sub.created)
        submission.submission_date_utc = datetime.fromtimestamp(r_sub.created_utc)
        submission.subreddit_name = self.subreddit.name
        submission.tracking = True
        submission.tracking_start_date = now
        submission.url = r_sub.url
        submission.is_self = r_sub.is_self
        submission._trialid = trial_id
        submission.save()
        

        sdatum = self.db.SubmissionDatum()
        sdatum.submission = submission._id
         
        sdatum.r_content_id = r_sub.content_id
        sdatum.r_id = r_sub.id
        sdatum.comment_count = r_sub.num_comments
        sdatum.upvotes = r_sub.ups
        sdatum.downvowes = r_sub.downs
        sdatum.fetch_date = now
        sdatum.position_hot = position_hot
        sdatum.position_top = position_top
        sdatum.position_new = position_new
        sdatum.save()


        #make initial comments and commentdatums
        

    def init_comments(self, r_sub):
        """
        class Comment(Document):
            structure = {
                'r_submission_id' : ObjectID,
                'author' : unicode,
                'r_parent_id' : unicode,
                'content_id':unicode,
                'comment_date' : datetime,
                'depth' : int,
                'permalink':unicode
             }
        """
        for r_comment in r_sub.comments:
            comment = self.db.Comment()
            comment.r_submission_id = r_sub.content_id
            comment.r_parent_id = r_comment.parent_id
            comment.content_id = r_comment.content_id
            comment.created = datetime.fromtimestamp(r_comment.created)
            comment.created_utc = datetime.fromtimestamp(r_comment.created_utc)
            comment.depth = 0

            """
            PROBLEM: CAN'T GET CHILDREN

            """

    """Assume r_comment has already been processed"""
    def _init_comments(self, r_comment):
        pass
    
    
    def make_comment_datum(self, r_comment, now):
        comment = None
        raise Exception()
        return comment

    """ Initialize Trial in db """
    def begin(self):
        """
        'trialid' : int,
        'startdate' : datetime,
        'finishdate' : datetime,
        'min_submission_track_minutes' : int,"""

        self.trialid = random.randint(10000000)
        
        if min_submission_tracking_time is None:
            self.min_submission_tracking_time = _MIN_SUBMISSION_TRACKING_TIME 
        
        if reddit_request_interval is None:
            self.reddit_request_interval = _REDDIT_REQUEST_INTERVAL 
        
        self.reddit

        trial = db.Trial()
        trial.trialid = self.trialid
        trial.startdate = datetime.now()
        trial.min_submission_track_minutes =  self.min_submission_tracking_time.minutes
        trial.save()
        
        
        
        self.start_loop()

    def start_loop(self):
        #main fetching loop (continue until not tracking any submissions)
        tracked_submissions = get_tracked_submissions(self.db, subreddit, self.trialid)
        while tracked_submissions: 
            for sub in tracked_submissions:
                if last_context_update - datetime.now() > context_expiry_interval:
                    last_context_update_date = datetime.now()
                    #process_context(context_data, last_context_update)
                    results =  make_contexts(self.db, self.r_subreddit, tracked_submissions):
                    hot_context, top_context, newsort_context, existing_sub_datums = results

                new_sub_data = fetch_submission(sub.url)
                sub = process_submission(new_sub_data, context)
                if datetime.now() - sub.tracking_start_date > self.min_submission_tracking_time:
                    if self.is_activity_dead(sub):
                        sub.tracking = false
                        sub.save()
                        tracked_submissions.remove(sub)
            #tracked_submissions = fetch_tracked_submissions(self.db, subreddit, self.trialid)

    def is_submission_dead(self, submission):
        raise Exception()
    """ Creates a SubredditContext and a list of SubmissionDatums """
    def make_contexts(db, r_subreddit, tracked_submissions):
           
        hot_subs, top_subs, newsort_subs = None, None, None
        hot_context, top_subs, newsort_subs = None, None, None,
        
        d_tracked_sub_ids = {}
        [(d_tracked_sub_ids[sub_id] = sub_id) for sub_id in tracked_submissions]

        existing_subs_datums = {}
        for sort_type in SubmissionSortTypes.get_list():
            if sort_type == SubmissionSortType.HOT:
                hot_subs = r_subreddit.get_hot()
                 
                hot_context = db.SubredditContext()
                hot_context.fetch_date = datetime.now()
                hot_context.sort_type = sort_type
                hot_context.submissions = None
                hot_context.save()
                
                for i in xrange(len(hot_subs)):
                    sub = hot_subs[i]
                    sub_datum_ids = []
                    if sub.content_id in existing_sub_datums:
                        sub_datum = existing_sub_datums[sub.content_id]
                        sub_datum.position_hot = i
                        sub_datum_ids.append(sub_datum.r_content_id)
                        sub_datum.save()
                    else:
                        #don't make datums for not-tracked submissions
                        if sub.content_id in d_tracked_sub_ids:
                            sub_datum = make_submission_datum(sub, position_hot = i)
                            sub_datum_ids.append(sub_datum.r_content_id)
                            existing_sub_datums[sub.content_id] = sub.content_id
                    
                    hot_context.submissions = sub_datum_ids
                    hot_context.save()
                hot_subs = None
                hot_context = None
            if sort_type == SubmissionSortType.TOP:
                top_subs = r_subreddit.get_top()
                 
                top_context = db.SubredditContext()
                top_context.fetch_date = datetime.now()
                top_context.sort_type = sort_type
                top_context.submissions = None
                top_context.save()
                
                for i in xrange(len(hot_subs)):
                    sub = top_subs[i]
                    sub_datum_ids = []
                    if sub.content_id in existing_sub_datums:
                        sub_datum = existing_sub_datums[sub.content_id]
                        sub_datum.position_top = i
                        sub_datum_ids.append(sub_datum.r_content_id)
                        sub_datum.save()
                    else:
                        #don't make datums for not-tracked submissions
                        if sub.content_id in d_tracked_sub_ids:
                            sub_datum = make_submission_datum(sub, position_top = i)
                            sub_datum_ids.append(sub_datum.r_content_id)
                            existing_sub_datums[sub.content_id] = sub.content_id
                    
                    top_context.submissions = sub_datum_ids
                    top_context.save()
            if sort_type == SubmissionSortType.NEW:
                newsort_subs = r_subreddit.get_new()
                 
                newsort_context = db.SubredditContext()
                newsort_context.fetch_date = datetime.now()
                newsort_context.sort_type = sort_type
                newsort_context.submissions = None
                newsort_context.save()
                
                for i in xrange(len(hot_subs)):
                    sub = newsort_subs[i]
                    sub_datum_ids = []
                    if sub.content_id in existing_sub_datums:
                        sub_datum = existing_sub_datums[sub.content_id]
                        sub_datum.position_new = i
                        sub_datum_ids.append(sub_datum.r_content_id)
                        sub_datum.save()
                    else:
                        #don't make datums for not-tracked submissions
                        if sub.content_id in d_tracked_sub_ids:
                            sub_datum = make_submission_datum(sub, position_new = i)
                            sub_datum_ids.append(sub_datum.r_content_id)
                            existing_sub_datums[sub.content_id] = sub.content_id
                    
                    newsort_context.submissions = sub_datum_ids
                    newsort_context.save()

        return hot_context, top_context, newsort_context, existing_sub_datums

                
    def make_submission_datum(self, r_sub, position_hot = None, position_top = None, position_new = None):
        sub_datum = db.SubmissionDatum()
        sub_datum.comment_count = r_sub.num_comments
        sub_datum.upvotes = r_sub.ups
        sub_datum.downvotes = r_sub.downs
        sub_datum.r_content_id = r_sub.content_id
        sub_datum.fetch_date = datetime.now()
        sub_datum.id = r_sub.r_id
        
        if position_hot:
            sub_datum.position_hot = position_hot
        if position_top:
            sub_datum.position_top = position_top
        if position_new:
            sub_datum.position_new = position_new
        
        sub_datum.save()
        return sub_datum 

def get_tracked_submissions(db, trialid):
    return db.Submission.find({'tracking': true, '_trialid':trialid})

"""Returns a list of reddit submission objects, as returned by the reddit api"""
def fetch_context(subreddit_conn):
    return subreddit_conn



    
    
    
    



    



