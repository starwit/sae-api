import logging

import pybase64
import valkey
from prometheus_client import Counter, Histogram
from visionapi.common_pb2 import MessageType
from visionapi.sae_pb2 import SaeMessage
from visionlib.pipeline import ValkeyPublisher

from .config import SaeApiConfig

logger = logging.getLogger(__name__)

FRAMES_FORWARDED = Counter('sae_api_frames_forwarded', 'How many frames have been forwarded to the backend')
FORWARD_CYCLE_DURATION = Histogram('sae_api_forward_cycle_duration', 'The time it takes to run one full frame forwarding cycle')


class FrameForwarder:
    '''Periodically pulls the latest frame from every video source stream on the source Valkey
    and forwards a frame-only SaeMessage to the backend Valkey (one output stream per source).'''

    def __init__(self, config: SaeApiConfig) -> None:
        self._config = config
        self._scan_pattern = f'{config.frame_forwarding.video_source_stream_prefix}:*'
        self._output_prefix = config.frame_forwarding.output_stream_prefix

        self._source_client = None
        self._publish_ctx = ValkeyPublisher(config.backend_valkey.host, config.backend_valkey.port)
        self._publish = None

    def __enter__(self):
        self._source_client = valkey.Valkey(self._config.source_valkey.host, self._config.source_valkey.port)
        self._publish = self._publish_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._source_client.close()
        except Exception as e:
            logger.warning('Error while closing source valkey client', exc_info=e)
        return self._publish_ctx.__exit__(exc_type, exc_value, traceback)

    @FORWARD_CYCLE_DURATION.time()
    def forward_once(self):
        stream_keys = list(self._source_client.scan_iter(match=self._scan_pattern, _type='STREAM'))
        logger.debug(f'Discovered {len(stream_keys)} source stream(s) matching {self._scan_pattern}')

        for stream_key in stream_keys:
            try:
                self._forward_stream(stream_key)
            except Exception as e:
                logger.warning(f'Error while forwarding latest frame from {stream_key!r}', exc_info=e)

    def _forward_stream(self, stream_key: bytes):
        entries = self._source_client.xrevrange(stream_key, count=1)
        if not entries:
            return

        _, fields = entries[0]
        proto_data = fields.get(b'proto_data_b64')
        if proto_data is not None:
            proto_data = pybase64.b64decode(proto_data, validate=True)
        else:
            proto_data = fields.get(b'proto_data')
        if proto_data is None:
            logger.warning(f'No proto data field found in latest entry of {stream_key!r}')
            return

        sae_msg = SaeMessage()
        sae_msg.ParseFromString(proto_data)

        if not sae_msg.HasField('frame'):
            logger.debug(f'Latest message in {stream_key!r} has no frame; skipping')
            return

        out_msg = SaeMessage()
        out_msg.frame.CopyFrom(sae_msg.frame)
        out_msg.type = MessageType.SAE

        source_id = stream_key.decode('utf-8').split(':', 1)[1]
        output_key = f'{self._output_prefix}:{source_id}'
        self._publish(output_key, out_msg.SerializeToString())

        FRAMES_FORWARDED.inc()
        logger.debug(f'Forwarded latest frame from {stream_key!r} to {output_key}')
