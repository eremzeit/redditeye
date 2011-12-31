from settings import WAIT_BETWEEN_CALL_TIME 
from urls import urls
from functools import wraps
import time

class require_captcha(object):
    """
    Decorator for methods that require captchas.
    """
    URL = urls["new_captcha"]
    VIEW_URL = urls["view_captcha"]

    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.captcha_id = None
        self.captcha = None

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return self.__class__(self.func.__get__(obj, type))

    def __call__(self, *args, **kwargs):
        # use the captcha passed in if given, otherwise get one
        self.captcha_id, self.captcha = kwargs.get("captcha",
                                                   self.get_captcha())
        result = self.func(*args, **kwargs)
        result.update(self.captcha_as_dict)
        return result

    @property
    def captcha_as_dict(self):
        return {"iden" : self.captcha_id,
                "captcha" : self.captcha}

    @property
    def captcha_url(self):
        if self.captcha_id:
            return urljoin(self.VIEW_URL, self.captcha_id + ".png")

    def get_captcha(self):
        data = Reddit()._request_json(self.URL, {"renderstyle" : "html"})
        # TODO: fix this, it kills kittens
        self.captcha_id = data["jquery"][-1][-1][-1]
        print "Captcha URL: " + self.captcha_url
        self.captcha = raw_input("Captcha: ")
        return self.captcha_id, self.captcha

def require_login(func):
    """A decorator to ensure that a user has logged in before calling the
    function."""
    @wraps(func)
    def login_reqd_func(self, *args, **kwargs):
        try:
            user = self.user
        except AttributeError:
            user = self.reddit_session.user

        if user is None:
            raise NotLoggedInException()
        else:
            return func(self, *args, **kwargs)
    return login_reqd_func

class sleep_after(object):
    """
    A decorator to add to API functions that shouldn't be called too
    rapidly, in order to be nice to the reddit server.

    Every function wrapped with this decorator will use a collective
    last_call_time attribute, so that collectively any one of the funcs won't
    be callable within the WAIT_BETWEEN_CALL_TIME; they'll automatically be
    delayed until the proper duration is reached.
    """
    last_call_time = 0     # init to 0 to always allow the 1st call
    WAIT_BETWEEN_CALL_TIME = WAIT_BETWEEN_CALL_TIME

    def __init__(self, func):
        wraps(func)(self)
        self.func = func

    def __call__(self, *args, **kwargs):
        call_time = time.time()

        since_last_call = call_time - self.last_call_time
        if since_last_call < WAIT_BETWEEN_CALL_TIME:
            time.sleep(WAIT_BETWEEN_CALL_TIME - since_last_call)

        self.__class__.last_call_time = call_time
        return self.func(*args, **kwargs)

def parse_api_json_response(func):
    """Decorator to look at the Reddit API response to an API POST request like
    vote, subscribe, login, etc. Basically, it just looks for certain errors in
    the return string. If it doesn't find one, then it just returns True.
    """
    @wraps(func)
    def error_checked_func(*args, **kwargs):
        return_value = func(*args, **kwargs)
        if not return_value:
            return
	else:
	    # todo, clean up this code. for right now, i just surrounded
	    # it with a try, except. basically the issue is when the _json_request
	    # wants to return a list, for example when you request the page for a 
	    # story; the reddit api returns json for the story and the comments.
	    try:
 	    	for k in return_value.keys():
		    if k not in (u"jquery", "iden", "captcha", "kind", "data"):
			warnings.warn("Return value keys contained "
				      "{0}!".format(return_value.keys()))
		jquery = return_value.get("jquery")
	 	if jquery:
		    values = [x[-1] for x in jquery]
	   	    if [".error.USER_REQUIRED"] in values:
			raise NotLoggedInException()
  	    except AttributeError:
		pass
        return return_value
    return error_checked_func
