from datetime import datetime
from pymongo.objectid import ObjectId
from mongokit import *

conn = Connection()

@conn.register
class Trial(Document):
    __collection__ = 'Trials'
    __database__ = 'redditeye'
    structure = {
        'startdate' : datetime,
        'finishdate' : datetime,
        'min_submission_track_seconds' : int,
        'submissions' : [{
            'r_id': unicode, #what's the difference between contentid and id?
            'r_contentid': unicode, 
            'author' : unicode,
            'title' : unicode,
            'selftext' : unicode,
            'submission_date' : datetime,
            'subreddit' : unicode, 
            'tracking' : bool,
            'tracking_comments' : bool,
            'url': unicode,
            'is_self': bool,
         }]
    }
    #required_fields = ['startdate', 'finishdate', 'min_submission_track_seconds']

#@conn.register
#class Submission(Document):
#    __collection__ = 'Submissions'
#    __database__ = 'redditeye'
#    structure = {
#        'trialoid': ObjectId,
#        'r_id': unicode, #what's the difference between contentid and id?
#        'r_contentid': unicode, 
#        'author' : unicode,
#        'title' : unicode,
#        'selftext' : unicode,
#        'submission_date' : datetime,
#        'subreddit' : unicode, 
#        'tracking' : bool,
#        'tracking_comments' : bool,
#        'url': unicode,
#        'is_self': bool,
#    }
#    required_fields = ['trialoid', 'title', 'author', 'selftext', 'r_id', 'r_contentid', 'submission_date', 'url', 'is_self']
#    default_values = {}

@conn.register
class Comment(Document):
    __collection__ = 'Comments'
    __database__ = 'redditeye'
    structure = {
        'r_sub_cid' : unicode,
        'author' : unicode,
        'r_parent_id' : unicode,
        'r_content_id':unicode,
        'created' : datetime,
        'created_utc' : datetime,
        #'depth' : int,
     }



@conn.register
class RedditUser(Document):
    __collection__ = 'RedditUsers'
    __database__ = 'redditeye'
    structure = {
        'username' :  unicode,
        'link_karma' : int,
        'comment_karma' : int,
        'join_date' : datetime
    }
    required_fields = ['username', 'link_karma', 'comment_karma', 'join_date']
    default_values = {}


@conn.register
class SubReddit(Document):
    __collection__ = 'SubReddits'
    __database__ = 'redditeye'
    structure = {
        'name' : unicode,
        'url' : unicode,
        'subscribers' : int,
    }
    required_fields = ['name', 'url', 'subscribers']
    default_values = {}



@conn.register
class SubmissionDatum(Document):
    __collection__ = 'SubmissionDatums'
    __database__ = 'redditeye'
    structure = {
        'submission_oid' : ObjectId,
        'r_content_id': unicode,
        'comment_count' : int,
        'upvotes' : int,
        'downvotes' : int,
        'score' : int,
        'fetch_date' : datetime,
        'position_hot' : int,
        'position_new' : int,
        'position_top' : int,

    }
    required_fields = ['submission_oid', 'r_content_id', 'comment_count', 'upvotes', 'downvotes', 'fetch_date']
    default_values = {}


@conn.register
class CommentDatum(Document):
    __collection__ = 'CommentDatums'
    __database__ = 'redditeye'
    structure = {
        'comment_oid' : ObjectId,
        'content_id' : unicode,
        'fetch_date' : datetime,
        'upvotes' : int,
        'downvotes' : int,
    }
    required_fields = ['comment_oid', 'content_id', 'fetch_date', 'upvotes', 'downvotes']
    default_values = {}



