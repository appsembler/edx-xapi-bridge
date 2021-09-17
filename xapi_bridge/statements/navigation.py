"""xAPI Statements for navigation interactions."""


from . import base, block, course
from xapi_bridge import constants, settings

from tincan import Activity, ActivityDefinition, ActivityList, Context, ContextActivities, Extensions, LanguageMap, Verb


class NavigationSequenceStatement(base.LMSTrackingLogStatement):

    def get_object(self, event):
        """
        Get object for the statement.
        """
        event_data = self.get_event_data(event)
        return Activity(
            id=event['page'],
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_MODULE,
                name=LanguageMap({'en': 'Course Unit Tab'}),  # would use target_name if avail.
                extensions=Extensions({constants.XAPI_ACTIVITY_POSITION:event_data['target_tab']})
            ),
        )

    def get_context(self, event):
        event_data = self.get_event_data(event)
        context = super(NavigationSequenceStatement, self).get_context(event)
        context.extensions = Extensions({
            constants.XAPI_CONTEXT_STARTING_POSITION: event_data['current_tab'],
        })
        context.context_activities = self.get_context_activities(event)
        return context

    def get_context_activities(self, event):
        parent_activities = [
            Activity(
                id=event['page'],
                definition=block.BlockActivityDefinition(event)
            ),
        ]
        return ContextActivities(
            parent=ActivityList(parent_activities),
        )


class NavigationSequenceTabStatement(NavigationSequenceStatement):
    """A new tab selected within a Unit."""

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_INITIALIZED,
            display=LanguageMap({'en': 'initialized'}),
        )


class NavigationLinkStatement(base.LMSTrackingLogStatement):

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_EXPERIENCED,
            display=LanguageMap({'en': 'experienced'})
        )

    def get_object(self, event):
        event_data = self.get_event_data(event)
        return Activity(
            id=event_data['target_url'],
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_LINK,
                name=LanguageMap({'en': 'Link name'})
            )
        )

    def get_context_activities(self, event):
        event_data = self.get_event_data(event)
        parent_activities = [
            Activity(
                id='{}/courses/{}'.format(settings.OPENEDX_PLATFORM_URI, event['context']['course_id']),
                definition=course.CourseActivityDefinition(event)
            ),
        ]
        other_activities = [
            Activity(
                id=event_data['current_url'],
                definition=base.ReferringActivityDefinition(event)
            ),
        ]

        return ContextActivities(
            parent=ActivityList(parent_activities),
            other=ActivityList(other_activities)
        )

    def get_context(self, event):
        """Get Context for the statement.

        For problems this can include the course and the block id.
        """
        return Context(
            platform=settings.OPENEDX_PLATFORM_URI,
            context_activities=self.get_context_activities(event)
        )


class NavigationSectionSelectionStatement(base.LMSTrackingLogStatement):

    def get_object(self, event):
        """
        Get object for the statement.
        """
        event_data = self.get_event_data(event)
        return Activity(
            id=event_data['target_url'],
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_MODULE,
                name=LanguageMap({'en': event_data['target_name']}),
            ),
        )

    def get_verb(self, event):
        return Verb(
            id=constants.XAPI_VERB_INITIALIZED,
            display=LanguageMap({'en': 'initialized'}),
        )

    def get_context_activities(self, event):
        event_data = self.get_event_data(event)
        other_activities = [
            Activity(
                id=event_data['current_url'],
                definition=base.ReferringActivityDefinition(event)
            ),
        ]

        return ContextActivities(
            other=ActivityList(other_activities)
        )

    def get_context(self, event):
        """Get Context for the statement.

        For problems this can include the course and the block id.
        """
        return Context(
            platform=settings.OPENEDX_PLATFORM_URI,
            context_activities=self.get_context_activities(event)
        )
