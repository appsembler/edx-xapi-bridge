"""Statement base classes for courseware blocks."""


from tincan import Activity, ActivityDefinition, ActivityList, ContextActivities, LanguageMap

from . import base
from . import course
from xapi_bridge import constants, settings


class BlockActivityDefinition(ActivityDefinition):
    def __init__(self, event, *args, **kwargs):
        try:
            display_name = event['context']['module']['display_name']
        except KeyError:
            # not all events will have in the context
            display_name = "Course Block"
        kwargs.update({
            'type': constants.XAPI_ACTIVITY_MODULE,
            'name': LanguageMap({'en': display_name}),
            'description': LanguageMap({'en': 'A course block in a course delivered through Open edX'})
        })
        super(BlockActivityDefinition, self).__init__(*args, **kwargs)


class BaseCoursewareBlockStatement(base.LMSTrackingLogStatement):
    """Base for any interaction with a courseware block."""

    def _get_activity_id(self, event):
        format_str = constants.BLOCK_OBJECT_ID_FORMAT
        platform_str = settings.OPENEDX_PLATFORM_URI
        block_id = event['context']['module']['usage_key']
        return format_str.format(platform=platform_str, block_usage_key=block_id)

    def get_context_activities(self, event):
        parent_activities = [
            Activity(
                id='{}/courses/{}'.format(settings.OPENEDX_PLATFORM_URI, event['context']['course_id']),
                definition=course.CourseActivityDefinition(event)
            ),
        ]
        # browser source events don't know as much about their context
        if event['event_source'].lower() == 'server':
            parent_activities.append(
                Activity(
                    id=event['referer'],
                    definition=BlockActivityDefinition(event)
                ),
            )

        other_activities = [
            Activity(
                id=event['referer'],
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
        context = super(BaseCoursewareBlockStatement, self).get_context(event)
        context.context_activities=self.get_context_activities(event)
        return context
