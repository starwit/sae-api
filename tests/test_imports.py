import pytest


def test_modules_import():
    '''Smoke test that the top-level components import cleanly.'''
    try:
        from saeapi.config import SaeApiConfig
        from saeapi.event_reporter import EventReporter
        from saeapi.frame_forwarder import FrameForwarder
        from saeapi.stage import run_stage
    except ImportError as e:
        pytest.fail(f'Failed to import saeapi components: {e}')

    assert SaeApiConfig is not None
    assert EventReporter is not None
    assert FrameForwarder is not None
    assert run_stage is not None
