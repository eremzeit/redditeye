from datetime import datetime
from pymongo.objectid import ObjectID
from mongokit import *
conn = Connection()




@conn.register()
"""
Question: How many submissions are tracked in a single trial?

Multiple?
    Pros:
        
    Cons:

Single?
    Pros:
        Better control over what posts are studied
    Cons:
        Each time you fetch, you need to 

"""
class Trial(Document):
    structure = {
        'trialid' : int,
        'startdate' : datetime,
        'finishdate' : datetime,
        'min_submission_track_minutes' : int,
        'initial_submission_ids' : [unicode],
    }


"""
RedditStory
	ID
	author						Foreign key
	Title						Text
	Content					    Text
	Postdate					Datetime
	Subreddit
"""
@conn.register()
class Submission(Document):
	structure = {
        'r_content_id': unicode,
        'r_id': unicode,
		'author' : unicode,
		'title' : unicode,
		'selftext' : unicode,
		'submission_date' : datetime,
		'submission_date_utc' : datetime,
		'subreddit' : unicode, 
        'tracking' : bool,
        'tracking_start_date' : datetime,
        'url': unicode,
        'is_self' bool,
        '_trialid': long
	}
    required_fields = ['author', 'title', 'content', 'submission_date', 'subreddit', 'tracking']
    default_values = {}

"""	
Comment
	ID
	RedditStory 				Foreignkey
	Author					Foreignkey
	ParentComment			Foreignkey
	CommentDate					Datetime
	Depth						int
"""

@conn.register()
class Comment(Document):
	structure = {
        'r_submission_id' : unicode,
        'author' : unicode,
        'r_parent_id' : unicode,
        'r_content_id':unicode,
        'created' : datetime,
        'created_utc' : datetime,
        'depth' : int,
        'permalink':unicode
     }


"""
Author
	Username					string
	LinkKarma				int
	CommentKarma			int
	JoinDate					Datetime
"""

@conn.register()
class RedditUser(Document):
    structure = {
        'username' :  unicode,
        'link_karma' : int,
        'comment_karma' : int,
        'join_date' : datetime
    }
    required_fields = ['username', 'link_karma', 'comment_karma', 'join_date']
    default_values = {}

"""
SubReddit
	name
	url
"""

@conn.register()
class SubReddit(Document):
    structure = {
        'name' : unicode,
        'url' : unicode,
        'subscribers' : int,
    }
    required_fields = ['name', 'url', 'subscribers']
    default_values = {}


"""

-=Dynamic Model=-
StoryDataPoint
	RedditPost				Foreignkey
	CommentsCount			int
	Upvotes					int
	Downvotes				int
	FetchedOn				DateTime
	PositionHot				int
	PositionNew				int
	PositionTop				int
"""

@conn.register()
class SubredditContext(Document):
    structure = {
        'content_id': unicode,
        'fetch_time':datetime,
        'sort_type':unicode,
        'submission_rate': double,
        'submission_ids':[unicode],
    }

@conn.register()
class SubmissionDatum(Document):
    structure = {
        'submission' : ObjectID,
        'r_content_id': unicode,
        'r_id': unicode,
        'comment_count' : int,
        'upvotes' : int,
        'downvotes' : int,
        'fetch_date' : datetime,
        'position_hot' : int,
        'position_new' : int,
        'position_top' : int,

    }
    required_fields = ['submission', 'comment_count', 'upvotes', 'downvotes', 'fetched_on']
    default_values = {}

"""

CommentDataPoint
	Comment					Foreignkey
	FetchedOn				DateTime

	Upvotes					int
	Downvotes 				int

	PositionRoot				int
	PositionBestInSiblings	int
	SiblingsCount				int

	Downvotes				int
	EPositionBest			int
	EPositionTop				int
	EPositionHot				int

"""

@conn.register()
class CommentDatum(Document):
    structure = {
        'comment' : ObjectID,
        'fetch_date' : datetime,
        'upvotes' : int,
        'downvotes' : int,
        'position_root' : int,
        'position_in_siblings_best' : int,
        'position_in_siblings_top' : int,
        'position_in_siblings_hot' : int,
        
        'aposition_best' : int,
        'aposition_top' : int,
        'aposition_hot' : int,
        
        'eposition_best' : int,
        'eposition_top' : int,
        'eposition_hot' : int,
    }
    required_fields = ['comment', 'fetch_date', 'upvotes', 'downvotes', 'position_root']
    default_values = {}



