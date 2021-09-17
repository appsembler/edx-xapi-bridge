"""xAPI Client to send payload data."""

import importlib
import json
import logging
import socket

from tincan.remote_lrs import RemoteLRS

from xapi_bridge import exceptions
from xapi_bridge import settings


kw = {
    'endpoint': settings.LRS_ENDPOINT,
}
if settings.LRS_BASICAUTH_HASH:
    kw['auth'] = "Basic {}".format(settings.LRS_BASICAUTH_HASH)
else:
    kw['username'] = settings.LRS_USERNAME
    kw['password'] = settings.LRS_PASSWORD


logger = logging.getLogger(__name__)

lrs = RemoteLRS(**kw)


class XAPIBridgeLRSPublisher(object):
    """Publishing wrapper around tincan.remote_lrs.RemoteLRS.
    Raise custom error types when LRS publishing activity not successful.
    """

    @property
    def lrs_backend(self):
        try:
            module = importlib.import_module('xapi_bridge.lrs_backends.' + settings.LRS_BACKEND_TYPE)
            class_ = getattr(module, 'LRSBackend')
            return class_()
        except (AttributeError, ImportError):
            raise ImproperlyConfigured("No LRS backend class matching specified LRS_BACKEND_TYPE in settings or unspecifed LRS_BACKEND_TYPE.")

    def _get_response_erroring_statement(self, lrs_response):
        req_data = lrs_response.data
        return self.lrs_backend.parse_error_response_for_bad_statement(req_data) 

    # RemoteLRS will use auth if passed otherwise BasicAuth with un/pw
    def publish_statements(self, statements):
        """
        params:
        statements tincan.statement_list.StatementList
        """
        try:
            lrs_resp = lrs.save_statements(statements)
        except (socket.gaierror, ):  # can't connect at all, no response
            raise exceptions.XAPIBridgeLRSConnectionError(queue=statements)

        if lrs_resp.success:
            for st in lrs_resp.content:
                logger.info("Succeeded sending statement {}".format(st.to_json()))
            return lrs_resp
        else:
            resp_dict = json.loads(lrs_resp.data)

            # error message from LRS
            if self.lrs_backend.response_has_errors(lrs_resp.data):
                # authorization failure
                if self.lrs_backend.request_unauthorised(lrs_resp.data):
                    raise exceptions.XAPIBridgeLRSConnectionError(lrs_resp)
                elif self.lrs_backend.response_has_storage_errors(lrs_resp.data):
                    badstmt = self._get_response_erroring_statement(lrs_resp)
                    raise exceptions.XAPIBridgeStatementStorageError(statement=statements[badstmt], message=resp_dict.get('message', ''))


lrs_publisher = XAPIBridgeLRSPublisher()
