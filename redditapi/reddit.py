import urllib
import urllib2
import cookielib
import warnings
import re
try:
    import json
except ImportError:
    import simplejson as json

from urls import urls
from util import urljoin, memoize, limit_chars

from api_exceptions import APIException, APIWarning, BadCaptcha, \
    NotLoggedInException, InvalidUserPass

from decorators import require_captcha, require_login, sleep_after, \
    parse_api_json_response

from settings import DEFAULT_CONTENT_LIMIT

# Import reddit objects
from base_objects import RedditObject
from comment import Comment
from redditor import Redditor
from submission import Submission
from subreddit import Subreddit
from inbox import Inbox
from helpers import _get_section, _get_sorter, _modify_relationship, _request

class Reddit(RedditObject):
    """A class for a reddit session."""
    DEFAULT_HEADERS = {}

    _friend = _modify_relationship("friend")
    _friend.__doc__ = "Friend the target user."

    _unfriend = _modify_relationship("friend", unlink=True)
    _unfriend.__doc__ = "Unfriend the target user."

    def __init__(self, user_agent=None, debug=False):
        """Specify the user agent for the application. If user_agent
        is None and debug is True, then the user agent will be
         "Reddit API Python Wrapper (Debug Mode)". """
        if user_agent is None:
            if debug:
                user_agent = "Reddit API Python Wrapper (Debug Mode)"
            else:
                raise APIException("You need to set a user_agent to identify "
                                   "your application!")
        self.DEFAULT_HEADERS["User-agent"] = user_agent

        self._cookie_jar = cookielib.CookieJar()
        opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self._cookie_jar))
        urllib2.install_opener(opener)

        self.user = None

    def __str__(self):
        return "Open Session (%s)" % (self.user or "Unauthenticated")

    def _request(self, page_url, params=None, url_data=None):
        """Given a page url and a dict of params, opens and returns the page.

        :param page_url: the url to grab content from.
        :param params: the extra url data to submit
        :param url_data: the GET data to put in the url
        :returns: the open page
        """
        return _request(self, page_url, params, url_data)

    @parse_api_json_response
    def _request_json(self, page_url, params=None, url_data=None,
                      as_objects=True):
        """Gets the JSON processed from a page. Takes the same parameters as
        the _request method, plus a param to control whether objects are
        returned.

        :param page_url
        :param params
        :param url_data
        :param as_objects: Whether to return constructed Reddit objects or the
        raw json dict.
        :returns: JSON processed page
        """
        if not page_url.endswith(".json"):
            page_url += ".json"
        response = self._request(page_url, params, url_data)
        if as_objects:
            hook = self._json_reddit_objecter
        else:
            hook = None
        return json.loads(response, object_hook=hook)

    def _json_reddit_objecter(self, json_data):
        """
        Object hook to be used with json.load(s) to spit out RedditObjects while
        decoding.
        """
        # TODO: This can be nicer. CONTENT_KINDS dict.
        kinds = dict((content.kind, content) for content in
                                    (Comment, Redditor, Subreddit, Submission))
        try:
            kind = kinds[json_data["kind"]]
        except KeyError:
            pass
        else:
            return kind.from_api_response(self, json_data["data"])
        return json_data

    @property
    @require_login
    def content_id(self):
        """
        For most purposes, we can stretch things a bit and just make believe
        this object is the user (and return it's content_id instead of none.)
        """
        return self.user.content_id

    def _found_place_holder(self, children, place_holder=None):
        """
        Helper function, checks if any of the children's id match placeholder.
        Rather useless, but allows breaking all the way out of a nested loop.
        """
        if place_holder is None:
            return False
        for child in children:
            if child.id == place_holder:
                return True

    def _get_content(self, page_url, limit=DEFAULT_CONTENT_LIMIT,
                     url_data=None, place_holder=None, all_content=None):
        """A method to return Reddit content from a URL. Starts at the initial
        page_url, and fetches content using the `after` JSON data until `limit`
        entries have been fetched, or the `place_holder` has been reached.

        :param page_url: the url to start fetching content from
        :param limit: the maximum number of content entries to fetch. if None,
            then fetch unlimited entries--this would be used in conjunction with
            the place_holder param.
        :param url_data: extra GET data to put in the url
        :param place_holder: if not None, the method will fetch `limit`
            content, stopping if it finds content with `id` equal to
            `place_holder`.
        :param all_content: the current list of content (used for recursion)
        :type place_holder: a string corresponding to a Reddit content id, e.g.
            't3_asdfasdf'
        :returns: a list of Reddit content, of type Subreddit, Comment, or
            Submission
        """
        if url_data is None:
            url_data = {}
        if all_content is None:
            # The list which we will populate to return with content
            all_content = []
        if limit is not None:
            limit = int(limit)

        # While we still need to fetch more content to reach our limit, do so.
        while limit and len(all_content) < limit:
            # If the after variable isn't None, add it do the URL of the page
            # we are going to fetch.
            page_data = self._request_json(page_url, url_data=url_data)
            #hamburger
            # if for some reason we didn't get data, then break

            #if not item_index is None and type(page_data) == list:
            #    page_data = page_data[item_index]

            try:
                data = page_data["data"]
            except KeyError:
                break

            after = data.get('after')
            children = data.get('children')
            all_content.extend(children)

            if self._found_place_holder(children, place_holder) or not after:
                break

            url_data["after"] = after
            self._get_content(page_url, limit, url_data, place_holder,
                              all_content)

        # we may have in the last iteration gotten a few extra results, so trim
        # down to limit
        if limit:
            all_content = all_content[:limit]
        return all_content

    @require_login
    def _fetch_modhash(self):
        """Grab the current user's modhash. Basically, just fetch any Reddit
        HTML page (can just get first 1200 chars) and search for
        'modhash: 1233asdfawefasdf', using re.search to grab the modhash.
        """
        # TODO: find the right modhash url, this is only temporary
        URL = urls["help"]
        data = self._request(URL)
        match = re.search(r"modhash[^,]*", data)
        self.modhash = match.group(0).split(": ")[1].strip(" '")

    def get_redditor(self, user_name, *args, **kwargs):
        """Return a Redditor class for the user_name specified."""
        return Redditor(self, user_name, *args, **kwargs)

    def get_subreddit(self, subreddit_name, *args, **kwargs):
        """Returns a Subreddit class for the user_name specified."""
        return Subreddit(self, subreddit_name, *args, **kwargs)

    @require_login
    def get_inbox(self, *args, **kwargs):
        """Return an Inbox object."""
        return Inbox(self, *args, **kwargs)

    def login(self, user=None, password=None):
        """Login to Reddit. If no user or password is provided, the user will
        be prompted with raw_input and getpass.getpass.
        """
        # Prompt user for necessary fields.
        if user is None:
            user = raw_input("Username: ")
        if password is None:
            import getpass
            password = getpass.getpass("Password: ")

        url = urls["login"]
        params = {'id' : '#login_login-main',
                  'op' : 'login-main',
                  'passwd' : password,
                  'user' : user}
        self._request_json(url, params)
        self.user = self.get_redditor(user)
        # Get and store the modhash; it will be needed for API requests
        # which involve this user.
        self._fetch_modhash()

    @require_login
    def logout(self):
        """
        Logs out of a session.
        """
        self.user = None
        url = urls["logout"]
        params = {"uh" : self.modhash}
        return self._request_json(url, params)

    @require_login
    def _subscribe(self, subreddit_id, unsubscribe=False):
        """If logged in, subscribe to the specified subreddit_id."""
        action = "unsub" if unsubscribe else "sub"
        url = urls["subscribe"]
        params = {'sr': subreddit_id,
                  'action': action,
                  'uh': self.modhash}
        return self._request_json(url, params)

    @require_login
    def _add_comment(self, content_id, subreddit_name=None, text=""):
        """Comment on the given content_id with the given text."""
        url = urls["comment"]
        params = {'thing_id': content_id,
                  'text': text,
                  'uh': self.modhash,
                  'r': subreddit_name}
        self._request_json(url, params)

    def get_front_page(self, limit=DEFAULT_CONTENT_LIMIT):
        """Return the reddit front page. Login isn't required, but you'll only
        see your own front page if you are logged in."""
        return self._get_content(urls["reddit_url"], limit=limit)

    @require_login
    def get_saved_links(self, limit=DEFAULT_CONTENT_LIMIT):
        """Return a listing of the logged-in user's saved links."""
        return self._get_content(urls["saved"], limit=limit)

    def get_all_comments(self, limit=DEFAULT_CONTENT_LIMIT, place_holder=None):
        """Returns a listing from reddit.com/comments (which provides all of
        the most recent comments from all users to all submissions)."""
        return self._get_content(urls["comments"], limit=limit, place_holder=place_holder)

    def get_submission_by_url(self, page_url, limit=DEFAULT_CONTENT_LIMIT,
                     url_data=None, place_holder=None, all_content=None):
        #hamburger

        if url_data is None:
            url_data = {}
        if all_content is None:
            # The list which we will populate to return with content
            all_content = []
        if limit is not None:
            limit = int(limit)

        # While we still need to fetch more content to reach our limit, do so.
        while limit and len(all_content) < limit:
            # If the after variable isn't None, add it do the URL of the page
            # we are going to fetch.
            page_data = self._request_json(page_url, url_data=url_data)
            #hamburger
            # if for some reason we didn't get data, then break

            page_data = page_data[0]

            try:
                data = page_data["data"]
            except KeyError:
                break

            after = data.get('after')
            children = data.get('children')
            all_content.extend(children)

            if self._found_place_holder(children, place_holder) or not after:
                break

            url_data["after"] = after
            self._get_content(page_url, limit, url_data, place_holder,
                              all_content)

        # we may have in the last iteration gotten a few extra results, so trim
        # down to limit
        if limit:
            all_content = all_content[:limit]
        submission = all_content[0]
        if type(submission) != Submission:
            raise Exception('Parsing exception')
        return submission

    def info(self, url=None, id=None, limit=DEFAULT_CONTENT_LIMIT):
        """
        Query the API to see if the given URL has been submitted already, and
        if it has, return the submissions.

        One and only one out of url (a url string) and id (a reddit url id) is
        required.
        """
        if bool(url) == bool(id):
            # either both or neither were given, either way:
            raise TypeError("One (and only one) of url or id is required!")
        if url is not None:
            params = {"url" : url}

            if url.startswith(urls["reddit_url"]) and url != urls["reddit_url"]:
                warnings.warn("It looks like you may be trying to get the info"
                              " of a self or internal link. This probably "
                              "won't return any useful results!", APIWarning)
        else:
            params = {"id" : id}
        return self._get_content(urls["info"], url_data=params, limit=limit)

    @require_captcha
    def send_feedback(self, name, email, message, reason="feedback"):
        """
        Send feedback to the admins. Please don't abuse this, read what it says
        on the send feedback page!
        """
        url = urls["send_feedback"]
        params = {"name" : name,
                  "email" : email,
                  "reason" : reason,
                  "text" : message}
        return self._request_json(url, params)

    @require_login
    @require_captcha
    def compose_message(self, recipient, subject, message):
        """
        Send a message to another redditor.
        """
        url = urls["compose_message"]
        params = {"text" : message,
                  "subject" : subject,
                  "to" : str(recipient),
                  "uh" : self.modhash,
                  "user" : self.user}
        return self._request_json(url, params)

    def search_reddit_names(self, query):
        """
        Search the subreddits for a reddit whose name matches the query.
        """
        url = urls["search_reddit_names"]
        params = {"query" : query}
        results = self._request_json(url, params)
        return [self.get_subreddit(name) for name in results.get("names")]

    @require_login
    @require_captcha
    def submit(self, subreddit, url, title, submit_type=None, text=None):
        """
        Submit a new link.

        Accepts either a Subreddit object or a str containing the subreddit
        name.
        """
        sr_name = str(subreddit)

        params = {"kind" : "link",
                  "sr" : sr_name,
                  "title" : title,
                  "uh" : self.modhash,
                  "url" : url,
                  "id" : self.user.id}
        if submit_type == 'self' and text != None:
            params["kind"] = submit_type
            params["text"] = text
            del(params["url"])
        url = urls["submit"]
        return self._request_json(url, params)
    @require_login
    def create_subreddit(self, short_title, full_title, description="", language="English [en]",
            type="public", content_options="any", other_options=None,
            domain=""):
        """Create a new subreddit"""
        url = urls["create"]
        # TODO: Implement the rest of the options.
        params = {"name" : short_title,
                  "title" : full_title,
                  "type" : type,
                  "uh" : self.reddit_session.modhash}
        return self._request_json(url, params)

