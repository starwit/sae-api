import pytest
from pydantic import ValidationError

from saeapi.config import SaeApiConfig, RedisConfig


def test_incomplete_config():
    with pytest.raises(ValidationError):
        SaeApiConfig(
            log_level="INFO",
            redis=RedisConfig(
                host="localhost",
                port=6379
                # Missing stream_id and input_stream_prefix
            )
        )

def test_complete_config():
    config = SaeApiConfig(
        log_level="INFO",
        redis=RedisConfig(
            host="localhost",
            port=6379,
            stream_id="stream1",
            input_stream_prefix="saeapi_input"
        ),
        prometheus_port=9000
    )

    assert config.log_level.name == "INFO"
    assert config.redis.host == "localhost"
    assert config.redis.port == 6379
    assert config.redis.stream_id == "stream1"
    assert config.redis.input_stream_prefix == "saeapi_input"
    assert config.prometheus_port == 9000