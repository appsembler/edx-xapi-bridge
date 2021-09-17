"""xAPI Statements and Activities for verbs on courses as a whole."""


import json

from tincan import Activity, ActivityDefinition, LanguageMap, Result, Verb

from . import block
from xapi_bridge import constants, exceptions, settings



class ProblemStatement(block.BaseCoursewareBlockStatement):
    """ Statement base for problem events."""

    def get_object(self, event):
        """
        Get object for the statement.
        """
        try:
            display_name = event['context']['module']['display_name']
        except KeyError:
            display_name = "Problem"
        return Activity(
            id=self._get_activity_id(event),
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_INTERACTION, # could be _QUESTION if not CAPA
                name=LanguageMap({'en': display_name}),
                description=LanguageMap({'en': 'A problem in an Open edX course'}),
                # TODO: interactionType, correctResponsesPattern, choices, if possible
            ),
        )


class ProblemCheckStatement(ProblemStatement):
    """Statement for student checking answer to a problem."""

    def __init__(self, event, *args, **kwargs):
        # 'problem_check' events are emitted from both browser and server
        # and we only want the server event
        if event['event_source'].lower() != 'server':
            raise exceptions.XAPIBridgeSkippedConversion("Don't convert problem checks from server")
        super(ProblemCheckStatement, self).__init__(event, *args, **kwargs)

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_ANSWERED,
            display=LanguageMap({'en': 'answered'}),
        )

    def get_result(self, event):
        event_data = self.get_event_data(event)
        # for now we are going to assume one submission
        # TODO: when is that not true? is it ever not true? What problem types?
        submission = event_data['submission'][list(event_data['submission'].keys())[0]]
        return Result(
            score={
                'raw': event_data['grade'],
                'min': 0,
                'max': event_data['max_grade'],
                'scaled': float(event_data['grade'] / event_data['max_grade'])
            },
            success=event_data['success'] == 'correct',
            # TODO: to determine completion would need to know max allowed attempts?
            # probably should return True here but uswe a result extension for num attempts/attempts left 
            response=json.dumps(submission['answer'])
        )


class ProblemSubmittedStatement(ProblemStatement):
    """Statement for student submitting an answer.

    Recorded in some problem types instead of problem_check; e.g., drag and drop v2.
    """

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_ATTEMPTED,
            display=LanguageMap({'en': 'attempted'}),
        )

    def get_result(self, event):
        event_data = self.get_event_data(event)
        earned = event_data['weighted_earned']
        possible = event_data['weighted_possible']
        return Result(
            score={
                'raw': earned,
                'min': 0,
                'max': possible,
                'scaled': float(earned / possible) if possible > 0 else 0
            },
            success=True if earned >= possible else False,
        )


class ProblemResetStatement(ProblemStatement):
    """Statement for student resetting answer to a problem."""

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_INITIALIZED,
            display=LanguageMap({'en': 'reset'}),
        )

    def get_result(self, event):
        event_data = self.get_event_data(event)
        return Result(
            completion=False,
            response=json.dumps("[]")
        )
