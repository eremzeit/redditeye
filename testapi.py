import redditapi

r = redditapi.Reddit('Redditeye user agent')
sr = r.get_subreddit('all')
subs = sr.get_hot()
sub = subs[0]
comments = sub.comments

