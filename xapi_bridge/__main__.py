"""Main process with queue management and remote LRS communication."""


from datetime import datetime
import json
import logging
import os
import signal
import sys
import threading


from pyinotify import WatchManager, Notifier, NotifierError, EventsCodes, ProcessEvent
from tincan import statement_list

from xapi_bridge import client
from xapi_bridge import converter
from xapi_bridge import exceptions
from xapi_bridge import settings

if settings.HTTP_PUBLISH_STATUS is True:
    from xapi_bridge import server


logger = logging.getLogger('edX-xapi-bridge main')


class QueueManager:
    """Manages the batching and publishing of statements in a thread-safe way."""

    def __init__(self):
        self.cache = []
        self.cache_lock = threading.Lock()
        self.publish_timer = None
        self.publish_retries = 0
        self.total_published_successfully = 0

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self.publish_timer is not None:
            self.publish_timer.cancel()

    def push(self, stmt):
        """Add a statement to the outgoing queue."""
        # push statement to queue
        with self.cache_lock:
            self.cache.append(stmt)

        # set timeout to publish statements
        if len(self.cache) == 1 and settings.PUBLISH_MAX_WAIT_TIME > 0:
            self.publish_timer = threading.Timer(settings.PUBLISH_MAX_WAIT_TIME, self.publish)
            self.publish_timer.start()

        # publish immediately if statement threshold is reached
        if settings.PUBLISH_MAX_PAYLOAD <= len(self.cache):
            self.publish()

    def publish(self):
        """Publish the queued statements to the LRS and clear the queue."""
        # make sure no new statements are added while publishing
        with self.cache_lock:

            # build StatementList

            lrs_success = False
            statements = statement_list.StatementList(self.cache)

            while lrs_success is False and len(statements) > 0:
                try:
                    lrs_resp = client.lrs_publisher.publish_statements(statements)
                    lrs_success = True
                    self.publish_retries = 0  # reset retries
                    self.total_published_successfully += len(statements)
                    logger.debug("{} statements published successfully".format(self.total_published_successfully))
                    if getattr(settings, 'TEST_LOAD_SUCCESSFUL_STATEMENTS_BENCHMARK', 0) > 0:
                        benchmark = settings.TEST_LOAD_SUCCESSFUL_STATEMENTS_BENCHMARK
                        if self.total_published_successfully >= benchmark:
                            logger.debug("published {} or more statements at {}".format(benchmark, datetime.now()))
                except exceptions.XAPIBridgeLRSConnectionError as e:
                    # if it was an auth problem, fail
                    # if it was a connection problem, retry
                    if self.publish_retries <= settings.PUBLISH_MAX_RETRIES:
                        self.publish_retries += 1
                    else:
                        e.err_fail()
                        break
                except exceptions.XAPIBridgeStatementStorageError as e:
                    # remove the failed Statement from StatementList
                    # and retry, logging non-failing exception
                    e.message = "Removing rejected Statement and retrying publishing StatementList. Rejected Statement was {}. LRS message was {}".format(e.statement.to_json(), e.message)
                    e.err_continue_msg()
                    statements.remove(e.statement)

            # clear the cache and cancel publish timer whether successful or not
            self.cache = []
            if self.publish_timer is not None:
                self.publish_timer.cancel()


class NotifierLostINodeException(NotifierError):
    """Exception to handle inotify loss of current watched inode."""


class TailHandler(ProcessEvent):
    """Parse incoming log events, convert to xapi, and add to publish queue."""

    # watch create and moved to events since tracking log may be re-created during log rotation
    # example inotifywatch /edx/var/log/tracking/tracking.log output:
    # (after performing a sudo logrotate --force /edx/var/log/tracking/tracking.log)
    # total  access  modify  attrib  close_write  open  move_self  delete_self  filename
    # 30     16      7       1       2            1     1          1            /edx/var/log/tracking/tracking.log
    # depending on the kernel and underlying inotify, either or both of IN_MOVE_SELF or IN_DELETE_SELF will fire
    # exit the handler on whichever fires first
    MASK = EventsCodes.OP_FLAGS['IN_MODIFY'] | EventsCodes.OP_FLAGS['IN_MOVE_SELF'] | EventsCodes.OP_FLAGS['IN_DELETE_SELF']

    def my_init(self, **kw):
        # called via __init__ on superclass
        # prepare file input stream
        self.ifp = open(kw['filename'], 'r', 1)
        self.ifp.seek(0, 2)
        self.publish_queue = QueueManager()
        self.raceBuffer = ''

    def __enter__(self):
        return self

    def __exit__(self, etype, value, traceback):
        # flush queue before exiting
        self.publish_queue.publish()
        self.publish_queue.destroy()
        self.ifp.close()

    def process_IN_MODIFY(self, event):
        """Handle any changes to the log file."""
        # read all new contents from the end of the file
        buff = self.raceBuffer + self.ifp.read()

        # if there's no newline at end of file, we probably read it before edx finished writing
        # add read contents to a buffer and return
        if len(buff) != 0 and buff[-1] != '\n':
            self.raceBuffer = buff

        else:
            self.raceBuffer = ''
            evts = [i for i in buff.split('\n') if len(i) != 0]
            for e in evts:
                try:
                    evt_obj = json.loads(e)
                except ValueError:
                    logger.warn('Could not parse JSON for', e)
                    continue

                xapi = None
                try:
                    xapi = converter.to_xapi(evt_obj)
                except (exceptions.XAPIBridgeStatementConversionError, ) as e:
                    e.err_continue_msg()

                if xapi is not None:
                    for i in xapi:
                        self.publish_queue.push(i)
                        # print u'{} - {} {} {}'.format(i['timestamp'], i['actor']['name'], i['verb']['display']['en-US'], i['object']['definition']['name']['en-US'])

    def process_IN_MOVE_SELF(self, event):
        """Handle moved tracking log file; e.g., during log rotation."""
        msg = "caught inotify IN_MOVE_SELF (tracking log file moved)"
        logger.info(msg)
        raise NotifierLostINodeException(msg)

    def process_IN_DELETE_SELF(self, event):
        """Handle deletion of tracking log file e.g., during log rotation."""
        msg = "caught inotify IN_DELETE_SELF (tracking log file deleted)"
        logger.info(msg)
        raise NotifierLostINodeException(msg)


def watch(watch_file):
    """Watch the given file for changes."""
    logger.info('Starting watch')
    wm = WatchManager()

    try:
        with TailHandler(filename=watch_file) as th:
            logger.debug('adding pyinotify watcher/notifier')
            notifier = Notifier(wm, th, read_freq=settings.NOTIFIER_READ_FREQ, timeout=settings.NOTIFIER_POLL_TIMEOUT)
            wm.add_watch(watch_file, TailHandler.MASK)
            notifier.loop()
    except NotifierLostINodeException:
        # end and restart watch
        logger.info("stopping notifier and restarting watch")
        notifier.stop()  # close inotify instance
        watch(watch_file)
    finally:
        logger.info('Exiting watch')


def signal_terminate_handler(signum, frame):
    """Handle terminating signals from terminal or sysctl to properly shut down."""
    if settings.HTTP_PUBLISH_STATUS is True:
        logger.info("Shutting down http server")
        http_server.shutdown()
        http_server.socket.close()
        thread.join(2.0)

    raise SystemExit


for sig in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
    signal.signal(sig, signal_terminate_handler)


if __name__ == '__main__':

    if getattr(settings, 'DEBUG_MODE', False):
        logging.basicConfig(
            format='%(levelname)s:%(message)s',
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            filename='/edx/var/log/xapi/xapi_bridge.log',
            filemode='a+',
            format='%(levelname)s:%(message)s',
            level=logging.INFO
        )

    if settings.HTTP_PUBLISH_STATUS is True:
        # open a TCP socket and HTTP server for simple OK status response
        # for service uptime monitoring
        http_server = server.httpd
        thread = threading.Thread(target=http_server.serve_forever)
        thread.daemon = True
        thread.start()

    # try to connect to the LRS immediately
    lrs = client.lrs
    resp = lrs.about()
    if resp.success:
        logger.info('Successfully connected to remote LRS at {}. Described by {}'.format(settings.LRS_ENDPOINT, resp.data))
        logger.debug(resp.data)
    else:
        e = exceptions.XAPIBridgeLRSConnectionError(resp)
        e.err_fail()

    log_path = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else '/edx/var/log/tracking/tracking.log'
    logger.debug('Watching file {}, starting time {}'.format(log_path, str(datetime.now())))
    watch(log_path)
