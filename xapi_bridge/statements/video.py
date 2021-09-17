"""xAPI Statements and Activities for verbs on courses as a whole.

Conformant with ADLNet Video xAPI Profile https://w3id.org/xapi/video/v1.0.2
"""

from tincan import Activity, ActivityDefinition, Extensions, LanguageMap, Result, Verb

from . import block
from xapi_bridge import constants, exceptions, settings


VIDEO_STATE_CHANGE_VERB_MAP = {
    'load_video': {
        'id': constants.XAPI_VERB_INITIALIZED,
        'display': LanguageMap({'en': 'loaded'})
    },
    'ready_video': {
        'id': constants.XAPI_VERB_INITIALIZED,
        'display': LanguageMap({'en': 'loaded'})
    },
    'play_video': {
        'id': constants.XAPI_VERB_PLAYED,
        'display': LanguageMap({'en': 'played'})
    },
    'pause_video': {
        'id': constants.XAPI_VERB_PAUSED,
        'display': LanguageMap({'en': 'paused'})
    },
    'stop_video': {
        'id': constants.XAPI_VERB_COMPLETED,
        'display': LanguageMap({'en': 'completed'})
    },
    'seek_video': {
        'id': constants.XAPI_VERB_SEEKED,
        'display': LanguageMap({'en': 'seeked'})
    },
    'show_transcript': {
        'id': constants.XAPI_VERB_INTERACTED,
        'display': LanguageMap({'en': 'video transcript shown'})
    },
    'hide_transcript': {
        'id': constants.XAPI_VERB_INTERACTED,
        'display': LanguageMap({'en': 'video transcript hidden'})
    },
    'edx.video.closed_captions.shown': {
        'id': constants.XAPI_VERB_INTERACTED,
        'display': LanguageMap({'en': 'video captions shown'})
    },
    'edx.video.closed_captions.hidden': {
        'id': constants.XAPI_VERB_INTERACTED,
        'display': LanguageMap({'en': 'video captions hidden'})
    },

}


class VideoStatement(block.BaseCoursewareBlockStatement):
    """ Statement base for video interaction events."""

    def _get_activity_id(self, event):
        if event['event_source'] == 'server':
            return super(VideoStatement, self)._get_activity_id(event)

        # TODO: Yuck.  Try to use course blocks API or other way to get a proper id
        # browser event source event won't have the module id
        # event only passes a bare id like '1f7c045b23084e2b8f9f8a2a303c0940'
        format_str = constants.BLOCK_OBJECT_ID_FORMAT
        platform_str = settings.OPENEDX_PLATFORM_URI
        bare_course_id = event['context']['course_id'].replace("course-v1:", "")
        block_type = "video+xblock" if 'xblock-video' in event['event_type'] else "video+block"
        block_id = 'block-v1:{}+type@{}@{}'.format(bare_course_id, block_type, self.get_event_data(event)['id'])
        return format_str.format(platform=platform_str, block_usage_key=block_id)

    def get_object(self, event):
        """
        Get object for the statement.
        """
        return Activity(
            id=self._get_activity_id(event),
            definition=ActivityDefinition(
                type=constants.XAPI_ACTIVITY_VIDEO,
                name=LanguageMap({'en': 'Video'}),  # TODO: get video name if possible, but not in tracking logs
                description=LanguageMap({'en': 'A video in an Open edX course'}),
            ),
        )

    def get_verb(self, event):
        event_type = event['event_type'].replace("xblock-video.", "")
        try:
            verb_props = VIDEO_STATE_CHANGE_VERB_MAP[event_type]
        except KeyError:
            return exceptions.XAPIBridgeSkippedConversion("unhandled video event: {}".event_type)
        return Verb(
            id=verb_props['id'],
            display=verb_props['display'],
        )

    def get_result(self, event):
        event_data = self.get_event_data(event)
        cur_time = event_data.get('currentTime', event_data.get('current_time', 0))
        return Result(
            extensions={
                constants.XAPI_RESULT_VIDEO_TIME: cur_time,
            })

    def get_context(self, event):
        return super(VideoStatement, self).get_context(event)


class VideoPlayStatement(VideoStatement):
    pass


class VideoPauseStatement(VideoStatement):
    def get_context(self, event):
        # TODO: not implemented but float video length value required for spec
        # info is not included in tracking log event.  We should add that information
        # in the Video XBlock
        context = super(VideoPauseStatement, self).get_context(event)
        context.extensions = {
            constants.XAPI_CONTEXT_VIDEO_LENGTH: 0.0
        }
        return context


class VideoSeekStatement(VideoStatement):
    def get_result(self, event):
        result = super(VideoSeekStatement, self).get_result(event)
        event_data = self.get_event_data(event)
        prev_time = event_data.get('old_time', event_data['previous_time'])
        new_time = event_data.get('new_time')
        result.extensions.update({
            constants.XAPI_RESULT_VIDEO_TIME_FROM: prev_time,
            constants.XAPI_RESULT_VIDEO_TIME_TO: new_time
        })
        return result


class VideoCompleteStatement(VideoStatement):
    def get_context(self, event):
        context = super(VideoCompleteStatement, self).get_context(event)
        event_data = self.get_event_data(event)
        cur_time = event_data.get('currentTime', event_data.get('current_time', 0))
        context.extensions = Extensions({
            #  length will be same as current time once stopped
            constants.XAPI_CONTEXT_VIDEO_LENGTH: cur_time
        })
        return context

    def get_result(self, event):
        # TODO: consider calculating real progress. For now assume 100% if played til end
        # profile includes concept of a completion threshold which could be below 100% anyhow
        result = super(VideoCompleteStatement, self).get_result(event)
        result.completion = True
        result.extensions.update({
            constants.XAPI_RESULT_VIDEO_PROGRESS: 100  # this isn't necessarily true if student skipped content
        })
        return result


class VideoTranscriptStatement(VideoStatement):

    def get_result(self, event):
        # xAPI video profile doesn't differentiate between transcripts, subtitles, and closed captioning :(
        result = super(VideoTranscriptStatement, self).get_result(event)
        result.extensions.update({
            constants.XAPI_RESULT_VIDEO_CC_ENABLED: True if 'show_transcript' in event['event_type'] or
            'closed_captions.shown' in event['event_type'] else False,
        })
        return result

    def get_context(self, event):
        # Show transcript and hide transcript only offer currentTime as context data.
        # TODO: get language from Video XBlock events at least, once available
        context = super(VideoTranscriptStatement, self).get_context(event)
        context.extensions = Extensions({
            constants.XAPI_CONTEXT_VIDEO_CC_LANGUAGE: "en"  # we don't get this info from tracking log
        })
        return context
