# SAE sae-api

The API layer between a SAE instance and the outside world (e.g. a cloud backend
system). It publishes information about the local SAE instance to a backend Valkey,
and is the place where inbound communication from the backend will be handled in the
future.

## What it does

- **Reports lifecycle events** — on startup and shutdown it publishes an
  `EventMessage` describing the instance to the backend.
- **Forwards frames** — periodically pulls the latest frame from each local video
  source stream and forwards a frame-only `SaeMessage` to the backend (one output
  stream per source).

## Interfaces

It reads from a local **source Valkey** and writes to a remote **backend Valkey**.
Stream keys are built from the prefixes and IDs in the configuration:

| Direction | Valkey   | Stream key                                          | Payload        |
| --------- | -------- | --------------------------------------------------- | -------------- |
| Input     | source   | `{video_source_stream_prefix}:{source_id}`          | `SaeMessage`   |
| Output    | backend  | `{frame_forwarding.output_stream_prefix}:{source_id}` | frame-only `SaeMessage` |
| Output    | backend  | `{event_reporting.output_stream_prefix}:{instance_id}` | `EventMessage` |

Source streams are discovered by scanning the source Valkey for keys matching
`{video_source_stream_prefix}:*`.

## Running it

Configuration is read from `settings.yaml` (see `settings.template.yaml` for all
options); every value can be overridden via environment variables, using `__` as the
nesting delimiter (e.g. `BACKEND_VALKEY__HOST`). Point `SETTINGS_FILE` at a different
file to use another location.

```sh
poetry install
poetry run python main.py
```

A Prometheus metrics endpoint is served on `prometheus_port` (8000 by default).

## Tests

```sh
poetry run pytest
```
