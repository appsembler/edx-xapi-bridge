
# the maximum age of an event, in seconds, before it is published to the LRS
PUBLISH_MAX_WAIT_TIME = 60

# the number of statements to publish per batch
PUBLISH_MAX_PAYLOAD = 10

# maximum publish retries on LRS connection error
PUBLISH_MAX_RETRIES = 1

# sleep time between polls of watched log file, in seconds
NOTIFIER_READ_FREQ = 2

# how long to wait for activity when polling, in milliseconds
# https://docs.python.org/2.4/lib/poll-objects.html
# If timeout is omitted, negative, or None, the call will block until
# there is an event for this poll object.
NOTIFIER_POLL_TIMEOUT = 1000

# lrs credentials
LRS_ENDPOINT = 'https://lrs.adlnet.gov/xAPI/'
LRS_USERNAME = 'fakeuser'
LRS_PASSWORD = 'fakepassword'
LRS_BASICAUTH_HASH = None

LRS_BACKEND_TYPE = 'learninglocker'

OPENEDX_PLATFORM_URI = 'https://open.edx.org'
OPENEDX_USER_API_URI = OPENEDX_PLATFORM_URI + "/api/user/v1/"
OPENEDX_OAUTH2_CLIENT_ID = "foo"
OPENEDX_OAUTH2_CLIENT_SECRET = "notasecret"

LMS_API_USE_MEMCACHED = False
MEMCACHED_ADDRESS = "127.0.0.1:11211"

# events configuration
# list of ignored event ids
IGNORED_EVENT_TYPES = []

# Sentry.io integration
SENTRY_DSN = False
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(SENTRY_DSN)

# open a TCP socket and HTTP server for simple OK status response
HTTP_PUBLISH_STATUS = False
HTTP_PUBLISH_IP = '0.0.0.0'
HTTP_PUBLISH_PORT = 9090

# Debugging
DEBUG_MODE = False
EXCEPTIONS_NO_CONTINUE = False  # set to True to always raise, fail application

# Testing
TEST_LOAD_TRACKING_TOTAL_LOG_WRITES = 20
TEST_LOAD_SLEEP_SECS_BETWEEN_WRITES = 5
TEST_LOAD_TRACKING_FILE_SOURCE = "fixtures/test_loadtest_events_0.json"
TEST_LOAD_SUCCESSFUL_STATEMENTS_BENCHMARK = 0
