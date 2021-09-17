"""Utility functions for xapi bridge."""

import logging

import memcache
from requests.exceptions import ConnectionError, Timeout  # pylint: disable=unused-import
from slumber.exceptions import SlumberBaseException

from edx_rest_api_client.client import EdxRestApiClient
from edx_rest_api_client.exceptions import HttpClientError

from xapi_bridge import constants, exceptions, settings


logger = logging.getLogger(__name__)


class UserApiClient(object):
    """
    Object builds an API client to make calls to the edxapp User API.
    Authenticates using settings.OPENEDX_EDX_API_KEY.
    """

    API_BASE_URL = settings.OPENEDX_USER_API_URI
    APPEND_SLASH = False
    CACHE_ACCOUNTS_PREFIX = "userapi_accounts__"

    def __init__(self):
        """
        Create an LMS API client, authenticated with the OAuth2 token for client in settings
        """
        # session = Session()
        # # session.headers = {"X-Edx-Api-Key": settings.OPENEDX_EDX_API_KEY}
        token = EdxRestApiClient.get_oauth_access_token(
            url="{}{}".format(settings.OPENEDX_PLATFORM_URI, constants.OPENEDX_OAUTH2_TOKEN_URL),
            client_id=settings.OPENEDX_OAUTH2_CLIENT_ID,
            client_secret=settings.OPENEDX_OAUTH2_CLIENT_SECRET,
        )
        if settings.LMS_API_USE_MEMCACHED:
            self.cache = memcache.Client([settings.MEMCACHED_ADDRESS], debug=0)
        self.client = EdxRestApiClient(
            self.API_BASE_URL, append_slash=self.APPEND_SLASH,
            username="xapi_bridge", oauth_access_token=token[0]
        )

    def get_edx_user_info(self, username):
        """
        Query the User API for the course details of the given course_id.
        Args:
            username (str): The username of the user
        Returns:
            dict with keys 'email', 'fullname'
        """

        def _get_user_info_from_api(username):

            try:
                resp = self.client.accounts(username).get()

                if resp:
                    return {'email': resp['email'], 'fullname': resp['name']}
                else:
                    # TODO: look at other reasons for no resp.success
                    message = 'Failed to retrieve user details for username {}. User not found in LMS'.format(username)                
                    raise exceptions.XAPIBridgeUserNotFoundError(message)
            except (SlumberBaseException, ConnectionError, Timeout, HttpClientError) as e:
                message = 'Failed to retrieve user details for username {} due to: {}'.format(username, str(e))                
                e = exceptions.XAPIBridgeConnectionError(message)
                e.err_continue_exc()
                raise exceptions.XAPIBridgeUserNotFoundError(message)                   

        if username == '':
            raise exceptions.XAPIBridgeUserNotFoundError()
            # return {'email': '', 'fullname': ''}

        if hasattr(self, 'cache'):
            cached_user_info = self.cache.get(self.CACHE_ACCOUNTS_PREFIX + username)
            if not cached_user_info:
                user_info = _get_user_info_from_api(username)
                self.cache.set(self.CACHE_ACCOUNTS_PREFIX + username, user_info, time=300)
                return user_info
            else:
                return cached_user_info
        else:
            return _get_user_info_from_api(username)


user_api_client = UserApiClient()
