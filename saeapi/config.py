import os
from pydantic import BaseModel, Field
from pydantic_settings import (BaseSettings, SettingsConfigDict,
                               YamlConfigSettingsSource)
from typing_extensions import Annotated
from visionlib.pipeline.settings import LogLevel


class ValkeyConfig(BaseModel):
    host: str = 'localhost'
    port: Annotated[int, Field(ge=1, le=65535)] = 6379


class EventReportingConfig(BaseModel):
    # Event messages are written to '{output_stream_prefix}:{instance_id}'
    output_stream_prefix: str = 'saeapi-event'


class FrameForwardingConfig(BaseModel):
    # Source streams are discovered by scanning '{video_source_stream_prefix}:*'
    video_source_stream_prefix: str
    # Forwarded frames are written to '{output_stream_prefix}:{source_id}'
    output_stream_prefix: str = 'saeapi-frame'
    poll_interval_s: float = 600.0


class SaeApiConfig(BaseSettings):
    log_level: LogLevel = LogLevel.WARNING
    # Identifies this SAE instance; reflected in all output stream names
    instance_id: str
    # Local instance SAE Valkey, where we read video source frames from
    source_valkey: ValkeyConfig
    # Remote cloud backend Valkey, where we write all output to
    backend_valkey: ValkeyConfig
    event_reporting: EventReportingConfig = EventReportingConfig()
    frame_forwarding: FrameForwardingConfig
    prometheus_port: Annotated[int, Field(ge=1024, le=65536)] = 8000

    model_config = SettingsConfigDict(env_nested_delimiter='__')

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        YAML_LOCATION = os.environ.get('SETTINGS_FILE', 'settings.yaml')
        return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls, yaml_file=YAML_LOCATION), file_secret_settings)
