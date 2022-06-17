"""Abstract base class for xapi backend storage services.
"""


from abc import ABCMeta, abstractmethod


class LRSBackendBase(object, metaclass=ABCMeta):
    """
    Base class to handle LRS backend-specific processing and error handling
    """

    @abstractmethod
    def request_unauthorised(self, response_data):
        """Return True if response data includes indication of unauthorised access
        """

    @abstractmethod
    def response_has_errors(self, response_data):
        """Return True if response data indicates error"""

    @abstractmethod
    def response_has_storage_errors(self, response_data):
        """Return True if response data includes indication of errors storing data
        """

    @abstractmethod
    def parse_error_response_for_bad_statement(self, response_data):
        """ Parses backend error message for problematic Statement.

        Returns numeric index of bads statement in StatementList.
        """
