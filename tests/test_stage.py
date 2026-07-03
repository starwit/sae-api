import threading
from unittest.mock import patch

import pybase64
import pytest
from visionapi.common_pb2 import MessageType
from visionapi.sae_pb2 import EventMessage, SaeMessage

from saeapi.stage import run_stage

# Real Event class captured before any patching, so the helper below can use a
# genuine event internally even while saeapi.stage.threading.Event is patched.
_RealEvent = threading.Event


class _OneShotStopEvent:
    '''Drop-in replacement for the threading.Event used by run_stage that lets a
    smoke test run exactly one frame-forwarding cycle and then shut down cleanly.

    - The poll loop calls wait(timeout); the first such call sets the event and
      returns True, so the loop forwards once and then breaks.
    - The main thread calls wait() (no timeout) and blocks on a real Event until set.'''

    def __init__(self):
        self._event = _RealEvent()

    def set(self):
        self._event.set()

    def is_set(self):
        return self._event.is_set()

    def wait(self, timeout=None):
        if timeout is None:
            return self._event.wait(timeout=5)
        self.set()
        return True


def _make_frame_msg_bytes(timestamp: int) -> bytes:
    msg = SaeMessage()
    msg.frame.timestamp_utc_ms = timestamp
    msg.frame.source_id = 'cam1'
    msg.type = MessageType.SAE
    return msg.SerializeToString()


@pytest.fixture(autouse=True)
def disable_prometheus():
    # We don't want to start the Prometheus server during tests
    with patch('saeapi.stage.start_http_server'):
        yield


@pytest.fixture(autouse=True)
def one_shot_stop_event():
    # Make run_stage's blocking loop terminate after a single forward cycle
    with patch('saeapi.stage.threading.Event', _OneShotStopEvent):
        yield


@pytest.fixture
def stage_config(make_config):
    with patch('saeapi.stage.SaeApiConfig') as mock_config:
        mock_config.return_value = make_config(
            instance_id='inst1',
            video_source_stream_prefix='videosource',
            frame_output_prefix='saeapi-frame',
            event_output_prefix='saeapi-event',
            poll_interval_s=0.01,
        )
        yield mock_config


@pytest.fixture
def source_client_mock():
    with patch('saeapi.frame_forwarder.valkey.Valkey') as mock_valkey:
        yield mock_valkey.return_value


@pytest.fixture
def event_publisher_mock():
    with patch('saeapi.event_reporter.ValkeyPublisher') as mock_publisher:
        yield mock_publisher.return_value.__enter__.return_value


@pytest.fixture
def frame_publisher_mock():
    with patch('saeapi.frame_forwarder.ValkeyPublisher') as mock_publisher:
        yield mock_publisher.return_value.__enter__.return_value


def test_run_stage_startup_forward_shutdown(stage_config, source_client_mock,
                                            event_publisher_mock, frame_publisher_mock):
    '''Integration smoke test: with valkey input/output mocked, run_stage should
    report startup, forward one frame, and report shutdown.'''
    source_client_mock.scan_iter.return_value = iter([b'videosource:cam1'])
    source_client_mock.xrevrange.return_value = [
        (b'1700000000000-0', {b'proto_data_b64': pybase64.b64encode(_make_frame_msg_bytes(99))}),
    ]

    run_stage()

    # A frame was forwarded to the per-source backend stream
    frame_publisher_mock.assert_called_once()
    frame_key, frame_proto = frame_publisher_mock.call_args.args
    assert frame_key == 'saeapi-frame:cam1'
    forwarded = SaeMessage()
    forwarded.ParseFromString(frame_proto)
    assert forwarded.frame.timestamp_utc_ms == 99

    # Startup and shutdown events were both reported
    assert event_publisher_mock.call_count == 2
    event_types = []
    for call in event_publisher_mock.call_args_list:
        _, proto = call.args
        msg = EventMessage()
        msg.ParseFromString(proto)
        assert msg.type == MessageType.SAE_EVENT
        event_types.append(msg.event_type)
    assert event_types == [EventMessage.EventType.STARTUP, EventMessage.EventType.SHUTDOWN]


def test_run_stage_no_source_streams(stage_config, source_client_mock,
                                     event_publisher_mock, frame_publisher_mock):
    '''Smoke test with no source streams: lifecycle events are still reported and
    nothing is forwarded.'''
    source_client_mock.scan_iter.return_value = iter([])

    run_stage()

    frame_publisher_mock.assert_not_called()
    assert event_publisher_mock.call_count == 2
