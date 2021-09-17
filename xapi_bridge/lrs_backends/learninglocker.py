"""H2Labs LearningLocker xAPI backend."""

import json
import re

from . import base

from xapi_bridge import exceptions


class LRSBackend(base.LRSBackendBase):

    def parse_error_response_for_bad_statement(self, response_data):

        # error data from LearningLocker will look something like:
        # u'{"errorId":"65e87d1c-131d-458a-bac0-5bf16a34e565","warnings":["Problem in \'statements.0.actor\'. Received \'{\\"name\\":\\"Bry\xe1\xe9\xefn Wilson\\",\\"objectType\\":\\"Agent\\"}\'","Problem in \'statements.1.actor\'. Received \'{\\"name\\":\\"Bry\xe1\xe9\xefn Wilson\\",\\"objectType\\":\\"Agent\\"}\'","Problem in \'statements.2.actor\'. Received \'{\\"name\\":\\"Bry\xe1\xe9\xefn Wilson\\",\\"objectType\\":\\"Agent\\"}\'","Problem in \'statements.3.actor\'. Received \'{\\"name\\":\\"Bry\xe1\xe9\xefn Wilson\\",\\"objectType\\":\\"Agent\\"}\'"]}'

        error = json.loads(response_data)
        try:
            warnings = error.get('warnings')
            problem_msg = warnings[0]
            object_matcher = re.search('^Problem in \'statements\.(\d)', problem_msg, re.UNICODE)
            if object_matcher:
                return int(object_matcher.group(1))
            else:
                raise exceptions.XAPIBridgeLRSBackendResponseParseError(response_data)
        except KeyError:
            raise exceptions.XAPIBridgeLRSBackendResponseParseError(response_data)

    def response_has_errors(self, response_data):
        return 'errorId' in json.loads(response_data)

    def request_unauthorised(self, response_data):
        return json.loads(response_data).get('message', '') == 'Unauthorised'

    def response_has_storage_errors(self, response_data):
        return 'warnings' in json.loads(response_data)
