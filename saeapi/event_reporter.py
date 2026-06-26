import logging
import time

from prometheus_client import Counter
from visionapi.sae_pb2 import EventMessage
from visionapi.common_pb2 import MessageType
from visionlib.pipeline import ValkeyPublisher

from .config import SaeApiConfig

logger = logging.getLogger(__name__)

EVENT_MESSAGE_COUNTER = Counter('sae_api_event_message_counter', 'How many event messages have been published',
                                labelnames=('event',))


class EventReporter:
    '''Publishes lifecycle EventMessages about this SAE instance to the backend Valkey.'''

    def __init__(self, config: SaeApiConfig) -> None:
        self._config = config
        self._stream_key = f'{config.event_reporting.output_stream_prefix}:{config.instance_id}'
        self._publish_ctx = ValkeyPublisher(config.backend_valkey.host, config.backend_valkey.port)
        self._publish = None

    def __enter__(self):
        self._publish = self._publish_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._publish_ctx.__exit__(exc_type, exc_value, traceback)

    def report_startup(self):
        self.report(EventMessage.EventType.STARTUP)

    def report_shutdown(self):
        self.report(EventMessage.EventType.SHUTDOWN)

    def report(self, event_type: EventMessage.EventType):
        msg = EventMessage()
        msg.instance_id = self._config.instance_id
        msg.timestamp_utc_ms = int(time.time() * 1000)
        msg.event_type = event_type
        msg.type = MessageType.SAE_EVENT

        self._publish(self._stream_key, msg.SerializeToString())

        event_name = EventMessage.EventType.Name(event_type)
        EVENT_MESSAGE_COUNTER.labels(event=event_name).inc()
        logger.info(f'Published event message ({event_name}) to {self._stream_key}')
