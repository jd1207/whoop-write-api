# Contributing

## Setup

```
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```
pytest
```

## Lint

```
ruff check .
ruff format --check .
```

## Code Style

- All lowercase comments
- No emojis in code or logs
- One class per file where practical
- 200-line max per file

## Unofficial Endpoints

The write API uses reverse-engineered endpoints. If you discover new endpoints
via mitmproxy/Charles Proxy, document them in ENDPOINTS.md with the payload
format and any required headers.

## Versioning

This project follows semver. v0.x releases may include breaking changes.
The public API is everything exported from `whoop.__init__`.
