# Security Policy

## Reporting a vulnerability

Please report security issues privately via
[GitHub Security Advisories](https://github.com/seifreed/geoloc-api/security/advisories/new)
rather than opening a public issue. We aim to respond within a few days.

## Security posture

This is a self-hostable geolocation API. The defaults target **localhost / PoC** use;
read this before exposing it on a network.

**Implemented**

- **Authentication** — optional `X-API-Key` header, compared in constant time
  (`secrets.compare_digest`). Set `API_KEY` in `.env` to enable it.
- **Input validation** — `/nearest` bounds lat/lon/radius/limit; `/geolocate` caps
  batch size and rssi range; all SQL uses parameterized queries (no string-built input).
- **Request body limit** — middleware rejects bodies over 1 MB (HTTP 413) before they
  are read into memory, mitigating memory-exhaustion DoS.
- **Container** — the API image runs as a non-root user; API and DB bind to
  `127.0.0.1` only (no LAN exposure by default).
- **Secrets** — credentials are read from `.env` (git-ignored, never committed) and
  kept out of the process list in `fetch.sh` (netrc / `curl --config`).
- **CI security gate** — every push/PR runs `ruff`, `mypy`, and `bandit` (SAST);
  GitHub Actions are pinned to commit SHAs and the workflow uses least-privilege
  `permissions`.

**Before exposing publicly (not done here, by design)**

- Set a strong `API_KEY`, `DB_PASS`, and `DB_ROOT_PASS`.
- Terminate TLS in front of the API; do not expose MariaDB.
- Add rate limiting and a connection pool for production load.
