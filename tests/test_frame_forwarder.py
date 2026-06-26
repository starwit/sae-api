from unittest.mock import MagicMock, patch

import pybase64
import pytest
from visionapi.common_pb2 import MessageType
from visionapi.sae_pb2 import SaeMessage

from saeapi.frame_forwarder import FrameForwarder


# Stand-in for raw image bytes carried in a frame
FRAME_DATA = b'\x01\x02\x03fake-frame-bytes\xff'


def _make_frame_msg_bytes(timestamp: int = 1) -> bytes:
    '''A SaeMessage carrying a frame (the kind FrameForwarder should forward).'''
    msg = SaeMessage()
    msg.frame.timestamp_utc_ms = timestamp
    msg.frame.source_id = 'cam1'
    msg.frame.frame_data = FRAME_DATA
    msg.type = MessageType.SAE
    return msg.SerializeToString()


def _stream_entry(proto_data: bytes, b64=True):
    '''Mimics a single Valkey stream entry as returned by xrevrange.'''
    if b64:
        fields = {b'proto_data_b64': pybase64.b64encode(proto_data)}
    else:
        fields = {b'proto_data': proto_data}
    return (b'1700000000000-0', fields)


@pytest.fixture
def source_client_mock():
    '''Mocks the source valkey.Valkey client used by FrameForwarder.'''
    with patch('saeapi.frame_forwarder.valkey.Valkey') as mock_valkey:
        yield mock_valkey.return_value


@pytest.fixture
def publisher_mock():
    '''Mocks the ValkeyPublisher and yields the publish callable.'''
    with patch('saeapi.frame_forwarder.ValkeyPublisher') as mock_publisher:
        yield mock_publisher.return_value.__enter__.return_value


def test_forward_once_forwards_latest_frame(make_config, source_client_mock, publisher_mock):
    config = make_config(
        instance_id='inst1',
        video_source_stream_prefix='test',
        frame_output_prefix='saeapi-frame',
    )

    source_client_mock.scan_iter.return_value = iter([b'test:cam1'])
    source_client_mock.xrevrange.return_value = [_stream_entry(_make_frame_msg_bytes(42))]

    with FrameForwarder(config) as forwarder:
        forwarder.forward_once()

    # The source stream was scanned with the configured prefix pattern
    source_client_mock.scan_iter.assert_called_once_with(match='test:*', _type='STREAM')

    # A single frame-only message was published to the per-source output stream
    publisher_mock.assert_called_once()
    output_key, proto_data = publisher_mock.call_args.args
    assert output_key == 'saeapi-frame:cam1'

    out_msg = SaeMessage()
    out_msg.ParseFromString(proto_data)
    assert out_msg.HasField('frame')
    assert out_msg.frame.timestamp_utc_ms == 42
    # The frame image data must be forwarded untouched
    assert out_msg.frame.frame_data == FRAME_DATA
    assert out_msg.type == MessageType.SAE


def test_forward_once_handles_base64_and_plain_proto(make_config, source_client_mock, publisher_mock):
    config = make_config(instance_id='inst1', video_source_stream_prefix='videosource')

    source_client_mock.scan_iter.return_value = iter([b'videosource:cam1'])
    # Entry without b64 encoding, using the plain proto_data field
    source_client_mock.xrevrange.return_value = [_stream_entry(_make_frame_msg_bytes(7), b64=False)]

    with FrameForwarder(config) as forwarder:
        forwarder.forward_once()

    publisher_mock.assert_called_once()
    _, proto_data = publisher_mock.call_args.args
    out_msg = SaeMessage()
    out_msg.ParseFromString(proto_data)
    assert out_msg.frame.timestamp_utc_ms == 7
