"""
So far unsophisticated utility for load-testing xapi_bridge
Run this as a separate python process using defined settings.
Run the xapi_bridge process pointing at xapi_bridge/test/fixtures/test_loadtest_event_log.log
and then separately, this file, like
python xapi_bridge/test/test_load.py

Populate test_loadtest_event_log.log with events from users in the LMS you are
testing against.
"""

import os
import sys
import time

from xapi_bridge import settings


def main(srcfile):

    # create the fake tracking event log
    with open(os.path.join("xapi_bridge", "test", "fixtures", "test_loadtest_event_log.log"), "a+") as log:
        with open(srcfile, "r") as src:
            for i in range(0, settings.TEST_LOAD_TRACKING_TOTAL_LOG_WRITES):
                print("appending another copy of src events to test tracking log")
                src.seek(0)
                log.write(src.read()+"\n")
                log.flush()
                time.sleep(settings.TEST_LOAD_SLEEP_SECS_BETWEEN_WRITES)


if __name__ == '__main__':
    srcfile = sys.argv[1] if len(sys.argv) > 1 else os.path.join("xapi_bridge", "test", "fixtures", "test_loadtest_events_0.json")
    main(srcfile)
