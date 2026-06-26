import pytest

from saeapi.config import (EventReportingConfig, FrameForwardingConfig,
                           SaeApiConfig, ValkeyConfig)


# This is necessary to prevent tests from accidentally loading real config files
@pytest.fixture(autouse=True)
def set_settings_file_location(monkeypatch):
    monkeypatch.setenv('SETTINGS_FILE', '/tmp/should_not_exist.yaml')


@pytest.fixture
def make_config():
    '''Factory for a fully-populated SaeApiConfig, so tests don't depend on
    settings.yaml or environment variables.'''
    def _make_config(
        instance_id='inst1',
        video_source_stream_prefix='videosource',
        frame_output_prefix='saeapi-frame',
        event_output_prefix='saeapi-event',
        poll_interval_s=600.0,
    ):
        return SaeApiConfig(
            log_level='WARNING',
            instance_id=instance_id,
            source_valkey=ValkeyConfig(host='source-host', port=6379),
            backend_valkey=ValkeyConfig(host='backend-host', port=6380),
            event_reporting=EventReportingConfig(
                output_stream_prefix=event_output_prefix,
            ),
            frame_forwarding=FrameForwardingConfig(
                video_source_stream_prefix=video_source_stream_prefix,
                output_stream_prefix=frame_output_prefix,
                poll_interval_s=poll_interval_s,
            ),
        )
    return _make_config
