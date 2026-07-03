from unittest.mock import patch

import pytest
from visionapi.common_pb2 import MessageType
from visionapi.sae_pb2 import EventMessage

from saeapi.event_reporter import EventReporter


@pytest.fixture
def publisher_mock():
    '''Mocks the ValkeyPublisher used by the EventReporter and yields the
    publish callable (what `__enter__` returns), so tests can assert on the
    messages that were published.'''
    with patch('saeapi.event_reporter.ValkeyPublisher') as mock_publisher:
        yield mock_publisher.return_value.__enter__.return_value


def test_report_startup_publishes_event(make_config, publisher_mock):
    config = make_config(instance_id='inst1', event_output_prefix='saeapi-event')

    with EventReporter(config) as reporter:
        reporter.report_startup()

    publisher_mock.assert_called_once()
    stream_key, proto_data = publisher_mock.call_args.args

    assert stream_key == 'saeapi-event:inst1'

    msg = EventMessage()
    msg.ParseFromString(proto_data)
    assert msg.instance_id == 'inst1'
    assert msg.event_type == EventMessage.EventType.STARTUP
    assert msg.type == MessageType.SAE_EVENT
    assert msg.timestamp_utc_ms > 0


def test_report_shutdown_publishes_event(make_config, publisher_mock):
    config = make_config(instance_id='inst1')

    with EventReporter(config) as reporter:
        reporter.report_shutdown()

    publisher_mock.assert_called_once()
    _, proto_data = publisher_mock.call_args.args

    msg = EventMessage()
    msg.ParseFromString(proto_data)
    assert msg.event_type == EventMessage.EventType.SHUTDOWN
