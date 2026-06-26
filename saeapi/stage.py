import logging
import signal
import threading

from prometheus_client import start_http_server

from .config import SaeApiConfig
from .frame_forwarder import FrameForwarder
from .event_reporter import EventReporter

logging.basicConfig(format='%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s')
logger = logging.getLogger(__name__)


def run_stage():

    stop_event = threading.Event()

    # Register signal handlers. Any termination signal (SIGTERM from an orchestrator,
    # SIGINT from Ctrl-C) sets the stop event and triggers a graceful shutdown, including
    # the shutdown status report.
    def sig_handler(signum, _):
        signame = signal.Signals(signum).name
        logger.info(f'Caught signal {signame} ({signum}). Exiting...')
        stop_event.set()

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    # Load config from settings.yaml / env vars
    CONFIG = SaeApiConfig()

    logger.setLevel(CONFIG.log_level.value)

    logger.info(f'Starting prometheus metrics endpoint on port {CONFIG.prometheus_port}')
    start_http_server(CONFIG.prometheus_port)

    logger.info(f'Starting sae-api stage. Config: {CONFIG.model_dump_json(indent=2)}')

    with EventReporter(CONFIG) as status, FrameForwarder(CONFIG) as forwarder:
        status.report_startup()

        def poll_loop():
            while not stop_event.is_set():
                try:
                    forwarder.forward_once()
                except Exception as e:
                    logger.error('Error during frame forwarding cycle', exc_info=e)
                # Wait returns True as soon as the stop event is set, otherwise after the interval
                if stop_event.wait(CONFIG.frame_forwarding.poll_interval_s):
                    break

        poll_thread = threading.Thread(target=poll_loop, name='frame-forwarder', daemon=True)
        poll_thread.start()

        # Block the main thread until a termination signal arrives
        stop_event.wait()

        poll_thread.join(timeout=10)

        status.report_shutdown()
