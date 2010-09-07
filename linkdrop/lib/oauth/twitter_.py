# partially based on code from velruse

import urlparse
import json
import httplib2
import oauth2 as oauth

from pylons import config, request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from linkdrop.lib.oauth.base import OAuth1, get_oauth_config

from twitter.oauth import OAuth
from twitter.api import Twitter, TwitterHTTPError

domain = 'twitter.com'


def twitter_to_poco(user):
    # example record
    #{'id': 33934767,
    # 'verified': False,
    # 'profile_sidebar_fill_color': 'e0ff92',
    # 'profile_text_color': '000000',
    # 'followers_count': 47,
    # 'profile_sidebar_border_color': '87bc44',
    # 'location': '',
    # 'profile_background_color': '9ae4e8',
    # 'utc_offset': None,
    # 'statuses_count': 36,
    # 'description': '',
    # 'friends_count': 58,
    # 'profile_link_color': '0000ff',
    # 'profile_image_url': 'http://a3.twimg.com/profile_images/763050003/me_normal.png',
    # 'notifications': False,
    # 'geo_enabled': False,
    # 'profile_background_image_url': 'http://s.twimg.com/a/1276197224/images/themes/theme1/bg.png',
    # 'screen_name': 'mixedpuppy',
    # 'lang': 'en',
    # 'profile_background_tile': False,
    # 'favourites_count': 0,
    # 'name': 'Shane Caraveo',
    # 'url': 'http://mixedpuppy.wordpress.com',
    # 'created_at': 'Tue Apr 21 15:21:25 +0000 2009',
    # 'contributors_enabled': False,
    # 'time_zone': None,
    # 'protected': False,
    # 'following': False}

    poco = {
        'displayName': user.get('name', user.get('screen_name')),
    }
    if user.get('url', False):
        poco['urls'] = [ { "primary" : False, "value" : user['url'] }]
    if user.get('profile_image_url', False):
        poco['photos'] = [ { 'type': u'profile', "value" : user['profile_image_url'] }]
    if user.get('created_at', None):
        poco['published'] = user['created_at']
    return poco

class responder(OAuth1):
    """Handle Twitter OAuth login/authentication"""
    domain = 'twitter.com'

    def __init__(self):
        OAuth1.__init__(self, domain)
        self.request_token_url = 'https://twitter.com/oauth/request_token'
        self.access_token_url = 'https://twitter.com/oauth/access_token'
        self.authorization_url = 'https://twitter.com/oauth/authenticate'

    def _get_credentials(self, access_token):
        # XXX should call twitter.api.VerifyCredentials to get the user object
        # Setup the normalized poco contact object
        username = access_token['screen_name']
        userid = access_token['user_id']

        profile = {}
        profile['providerName'] = 'Twitter'
        profile['displayName'] = username
        profile['identifier'] = 'http://twitter.com/?id=%s' % userid

        account = {'domain': 'twitter.com',
                   'userid': userid,
                   'username': username }
        profile['accounts'] = [account]

        result_data = {'profile': profile,
                       'oauth_token': access_token['oauth_token'], 
                       'oauth_token_secret': access_token['oauth_token_secret']}
        result, error = api(oauth_token=access_token['oauth_token'],
                   oauth_token_secret=access_token['oauth_token_secret']).profile()
        if result:
            profile.update(twitter_to_poco(result))
        return result_data

class api():
    def __init__(self, account=None, oauth_token=None, oauth_token_secret=None):
        self.oauth_token = account and account.oauth_token or oauth_token
        self.oauth_token_secret = account and account.oauth_token_secret or oauth_token_secret
        self.config = get_oauth_config(domain)

    def rawcall(self, url, body):
        raise Exception("NOT IMPLEMENTED")

    def sendmessage(self, message, options={}):
        auth = OAuth(token=self.oauth_token,
                     token_secret=self.oauth_token_secret,
                     consumer_key=self.config['consumer_key'],
                     consumer_secret=self.config['consumer_secret'])
        result = error = None
        try:
            api = Twitter(auth=auth)
            result = api.statuses.update(status=message)
            result[domain] = result['id']
        except TwitterHTTPError, exc:
            details = json.load(exc.e)
            if 'error' in details:
                msg = details['error']
            else:
                msg = str(details)
            error = {'provider': domain,
                     'reason': msg,
                     'code': exc.e.code
            }
        return result, error
    
    def profile(self):
        auth = OAuth(token=self.oauth_token,
                     token_secret=self.oauth_token_secret,
                     consumer_key=self.config['consumer_key'],
                     consumer_secret=self.config['consumer_secret'])
        result = error = None
        try:
            api = Twitter(auth=auth)
            result = api.account.verify_credentials()
            result[domain] = result['id']
        except TwitterHTTPError, exc:
            import sys; print >> sys.stderr, repr(exc)
            details = "TwitterHTTPError %d" % (exc.e.code)
            if exc.e.code != 404:
                details = json.load(exc.e)
            if 'error' in details:
                msg = details['error']
            else:
                msg = str(details)
            error = {'provider': domain,
                     'reason': msg,
                     'code': exc.e.code
            }
        return result, error
    
