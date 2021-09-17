"""Exception types for xAPI operations."""

import logging
import json
import os
import time

from xapi_bridge import settings

HAS_SENTRY_INTEGRATION = False


logger = logging.getLogger(__name__)


try:
    from sentry_sdk import capture_exception, capture_message, configure_scope
    HAS_SENTRY_INTEGRATION = True
except ImportError:
    logger.info("No Sentry.io integration defined for xapi Bridge")



class XAPIBridgeSentryMixin(object):
    """Defines exception class methods for exceptions to explicityly send messages or exceptions to Sentry.io."""

    MSG_SENT_TO_SENTRY = 'Sent to Sentry.io' if HAS_SENTRY_INTEGRATION else ''

    def update_sentry_scope(self, scope, level='warning', user=None, **kwargs):
        """Set up Scope context for Sentry logging."""
        scope.level = level
        if user:
            scope.user = {"username": user}  # TODO: get email if possible
        if kwargs:
            for key, value in list(kwargs.items()):
                scope.set_extra(key, value)
        return scope

    def log_error(self, log_type):
        """Send exception information to Sentry if integrated.
        Typically called if we need to know about the exception but we don't want to fail the application.
        """
        if HAS_SENTRY_INTEGRATION:
            with configure_scope() as scope:
                extra_context = dict()
                user = None
                if hasattr(self, 'statement'):
                    extra_context.update({'xAPI Statement': self.statement.to_json()})
                if hasattr(self, 'event'):
                    user = self.event['username']
                    extra_context.update({'Tracking Log Event': json.dumps(self.event)})
                if hasattr(self, 'queue') and self.queue is not None:
                    extra_context.update({'Queued unsent Statements': '\n'.join(st.to_json() for st in self.queue)})
                scope = self.update_sentry_scope(scope, 'warning', **extra_context)
                if log_type == 'exception':
                    capture_exception(self)
                else:
                    capture_message(self.message)
        logger.warn('xAPI Bridge caught exception type {}:{}. {}'.format(str(self.__class__), self.message, self.MSG_SENT_TO_SENTRY))


class XAPIBridgeException(Exception, XAPIBridgeSentryMixin):
    """Base exception class for xAPI bridge application."""

    def __init__(self, message=None, *args):
        if message is None:
            self.message = 'An XAPIBridgeException occurred without a specific message'
        super(XAPIBridgeException, self).__init__(message, *args)

    def err_continue_exc(self):
        """Handle non-fatal errors, tracking an exception in Sentry.io."""

        if settings.EXCEPTIONS_NO_CONTINUE:  # debug setting
            self.err_fail()
        else:
            self.log_error('exception')

    def err_continue_msg(self):
        """Handle non-fatal errors, tracking just a message in Sentry.io."""

        if settings.EXCEPTIONS_NO_CONTINUE:  # debug setting
            self.err_fail()
        else:
            self.log_error('message')

    def err_fail(self):
        self.log_error('exception')
        time.sleep(4)
        SystemExit("Terminal exception: {}".format(self.message))
        os._exit(os.EX_UNAVAILABLE)  # TODO: for some reason SystemExit isn't killing the program


class XAPIBridgeConnectionError(XAPIBridgeException):
    """Base exception class for errors connecting to external services in xAPI bridge application."""

    def __init__(self, message=None, *args):
        self.message = "External connection error in xapi-bridge application. {}".format(message)
        super(XAPIBridgeConnectionError, self).__init__(self.message, *args)


class XAPIBridgeLRSConnectionError(XAPIBridgeConnectionError):
    """Exception class for problems connecting to an LRS."""

    def __init__(self, response=None, message=None, queue=None, *args):
        self.queue = queue
        if not message:
            self.message="Error connecting to remote LRS at {}.".format(settings.LRS_ENDPOINT)
            if response:
                self.message+=" Requested resource was '{}'".format(response.request.resource)
        super(XAPIBridgeLRSConnectionError, self).__init__(self.message, *args)


class XAPIBridgeUserNotFoundError(XAPIBridgeException):
    """Exception class for no LMS use found."""


class XAPIBridgeStatementConversionError(XAPIBridgeException):
    """Catch-all exception for bad Staements."""

    def __init__(self, event=None, message=None, *args):
        self.event = event
        self.message = message
        super(XAPIBridgeStatementConversionError, self).__init__(self.message, *args)


class XAPIBridgeStatementStorageError(XAPIBridgeException):
    """Exception for Statements that are rejected for storage by LRS."""

    def __init__(self, statement=None, message=None, *args):
        self.statement = statement
        self.message = message
        super(XAPIBridgeStatementStorageError, self).__init__(self.message, *args)


class XAPIBridgeLRSBackendResponseParseError(XAPIBridgeException):
    """Exception for parsing information from backend error response."""

    def __init__(self, response_data='', *args):
        self.message = "Problem parsing problem from backend response: {}".format(response_data)
        super(XAPILRSBridgeBackendResponseParseError, self).__init__(self.message, *args)


class XAPIBridgeSkippedConversion(XAPIBridgeException):
    """Raised if statement conversion is skipped due to some internal logic of Statement class.
    """
