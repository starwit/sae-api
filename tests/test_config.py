import pytest
from pydantic import ValidationError

from saeapi.config import (FrameForwardingConfig, SaeApiConfig, ValkeyConfig)


def test_incomplete_config():
    with pytest.raises(ValidationError):
        SaeApiConfig(
            log_level='INFO',
            # Missing instance_id, source_valkey, backend_valkey, frame_forwarding
        )


def test_minimal_config():
    config = SaeApiConfig(
        log_level='INFO',
        instance_id='inst1',
        source_valkey=ValkeyConfig(host='source-host', port=6379),
        backend_valkey=ValkeyConfig(host='backend-host', port=6380),
        frame_forwarding=FrameForwardingConfig(
            video_source_stream_prefix='videosource',
        ),
        prometheus_port=9000,
    )

    assert config.log_level.name == 'INFO'
    assert config.instance_id == 'inst1'
    assert config.source_valkey.host == 'source-host'
    assert config.backend_valkey.port == 6380
    assert config.frame_forwarding.video_source_stream_prefix == 'videosource'
    # Defaults are applied
    assert config.frame_forwarding.output_stream_prefix == 'saeapi-frame'
    assert config.event_reporting.output_stream_prefix == 'saeapi-event'
    assert config.prometheus_port == 9000
