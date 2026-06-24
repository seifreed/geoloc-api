<p align="center">
  <img src="https://img.shields.io/badge/geoloc--api-Cell%20%2F%20WiFi%20%2F%20A--GNSS-blue?style=for-the-badge" alt="geoloc-api">
</p>

<h1 align="center">geoloc-api</h1>

<p align="center">
  <strong>Self-hosted geolocation database for cellular towers, WiFi APs and A-GNSS data</strong>
</p>

<p align="center">
  <a href="https://github.com/seifreed/geoloc-api/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.14-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MariaDB-11-003545?style=flat-square&logo=mariadb&logoColor=white" alt="MariaDB">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

<p align="center">
  <a href="https://github.com/seifreed/geoloc-api/stargazers"><img src="https://img.shields.io/github/stars/seifreed/geoloc-api?style=flat-square" alt="GitHub Stars"></a>
  <a href="https://github.com/seifreed/geoloc-api/issues"><img src="https://img.shields.io/github/issues/seifreed/geoloc-api?style=flat-square" alt="GitHub Issues"></a>
  <a href="https://buymeacoffee.com/seifreed"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow?style=flat-square&logo=buy-me-a-coffee&logoColor=white" alt="Buy Me a Coffee"></a>
</p>

---

## Overview

**geoloc-api** builds your own geolocation database from public data sources and
exposes a REST API to resolve **cellular towers** and **WiFi access points** to
coordinates — and to estimate a device's position from the cells/APs it sees, the
same technique a phone uses to fix its location without (or before) GPS. It also
fetches **A-GNSS** satellite ephemeris, the third leg used to accelerate a GPS fix.

It ingests data from three public sources, stores it in **MariaDB**, and serves it
through a **FastAPI** REST API — all deployed with a single **Docker Compose** command.

### Key Features

| Feature | Description |
|---------|-------------|
| **Cell tower lookup** | Resolve GSM/UMTS/LTE/NR cells (OpenCelliD format) to lat/lon |
| **WiFi AP lookup** | Resolve BSSIDs to lat/lon (WiGLE format) |
| **Geolocation** | Estimate position from seen cells/APs; weights by RSSI when provided |
| **Nearest lookup** | `/nearest` proximity query backed by a MariaDB spatial index |
| **API-key auth** | Optional `X-API-Key` header gate (`API_KEY` in `.env`) |
| **A-GNSS fetch** | Download GNSS broadcast ephemeris (RINEX) from NASA CDDIS |
| **One-command deploy** | `docker compose up` brings up DB + API |
| **Dynamic port** | Docker auto-assigns a free host port; helper resolves it |
| **Credentials via `.env`** | No secrets in code or repo |
| **Batch loaders** | Stream-load multi-MB CSV / JSON into MariaDB |
| **Interactive docs** | Swagger UI auto-generated at `/docs` |

### Data Sources

| Source | Provides | Registration | Download method |
|--------|----------|---------------|-----------------|
| **OpenCelliD** | Cell towers (GSM/UMTS/LTE/NR) | Free API key (`pk.…`) | CSV per country (MCC). Spain = `214` |
| **WiGLE** | Geolocated WiFi APs | Free API name + token | REST bounding-box search (JSON) |
| **CDDIS (NASA)** | GNSS ephemeris (A-GNSS) | Free Earthdata account | RINEX over HTTPS + login |

> Paid alternatives for real-time accuracy: **UnwiredLabs**, **Combain**,
> **Google Geolocation API** (they resolve positions but don't hand over the raw dataset).

### Architecture

```text
   public sources                your machine (Docker)
  ┌───────────────┐   fetch.sh   ┌──────────┐   REST API   ┌──────────┐
  │  OpenCelliD   │ ───────────► │  MariaDB │ ◄─────────►  │ FastAPI  │ ◄── curl / app
  │  WiGLE        │   load.py    │ (cells,  │              │ :dynamic │
  │  CDDIS (AGNSS)│              │   wifi)  │              └──────────┘
  └───────────────┘              └──────────┘
```

---

## Installation

### Requirements

- Docker + Docker Compose
- Python 3.14 (host-side, for the loader scripts and tests)
- Free accounts: [OpenCelliD](https://opencellid.org), [WiGLE](https://wigle.net/account), [NASA Earthdata](https://urs.earthdata.nasa.gov)

### From Source

```bash
git clone https://github.com/seifreed/geoloc-api.git
cd geoloc-api
cp .env.example .env          # fill in your own API keys (never committed)
pip install -e .              # installs the app + deps (add [dev] for tests/lint)
```

`.env` keys:

```text
OCID_TOKEN        OpenCelliD API key (starts with pk.)
WIGLE_USER/PASS   WiGLE API name and token
EARTHDATA_USER/PASS   NASA Earthdata credentials
API_KEY           optional; if set, the API requires header X-API-Key (empty = open, localhost only)
DB_PASS / DB_ROOT_PASS   MariaDB passwords (defaults are fine locally; change to deploy)
```

---

## Quick Start

```bash
# 1. Bring up DB + API (Docker picks a free host port)
./geo.sh up
./geo.sh url                              # -> http://localhost:<port>

# 2. Download data from the public sources
./fetch.sh cells 214                      # cell towers for Spain (OpenCelliD)
./fetch.sh wifi  41.38 2.15 41.40 2.17    # WiFi APs in a bounding box (WiGLE)
./fetch.sh agnss 2024 001                 # broadcast ephemeris, day 001 of 2024 (CDDIS)

# 3. Load into MariaDB
./geo.sh load cells data/ocid_214.csv.gz
./geo.sh load wifi  data/wigle.json
```

Open `<url>/docs` for the interactive Swagger UI.

---

## Usage

### REST API

All data endpoints require the `X-API-Key` header **when `API_KEY` is set** in `.env`
(if unset, the API is open — localhost only). `/health` is always open.

| Method | Route | Example |
|--------|-------|---------|
| `GET` | `/health` | health check (no auth) |
| `GET` | `/cell` | `?radio=GSM&mcc=214&mnc=7&area=2816&cid=3573` |
| `GET` | `/wifi` | `?bssid=00:00:08:EE:7A:A5` |
| `GET` | `/nearest` | `?lat=40.42&lon=-3.72&kind=cell&radius=2000&limit=5` → nearest towers/APs by distance |
| `POST` | `/geolocate` | JSON with `cells[]` and/or `wifi[]` → estimated position |

```bash
URL=$(./geo.sh url)
KEY='-H "X-API-Key: $API_KEY"'   # omit if API_KEY is empty

# Resolve a single tower
curl -H "X-API-Key: $API_KEY" "$URL/cell?radio=GSM&mcc=214&mnc=7&area=2816&cid=3573"
# -> {"lon":-3.7221,"lat":40.4257,"range":7094,"samples":23}

# Nearest cell towers to a point (uses the spatial index)
curl -H "X-API-Key: $API_KEY" "$URL/nearest?lat=40.42&lon=-3.72&kind=cell&radius=2000&limit=3"
# -> [{... "distance_m": 34.4}, ...]  (sorted by distance)

# Estimate position from seen cells + APs (optional rssi in dBm → weights by signal power)
curl -X POST -H "X-API-Key: $API_KEY" -H 'content-type: application/json' "$URL/geolocate" -d '{
  "cells": [{"radio":"GSM","mcc":214,"mnc":7,"area":2816,"cid":3573,"rssi":-65}],
  "wifi":  [{"bssid":"00:00:08:EE:7A:A5","rssi":-40}]
}'
# -> {"lat":..., "lon":..., "matched":2}
```

`/geolocate` returns the **weighted centroid** of the matched cells/APs. If `rssi`
(dBm) is given for an observation, its weight is the linear signal power
(`10^(rssi/10)`) so stronger signals pull the result toward them; otherwise the
weight is the cell's sample count (or 1 for WiFi). `wifi[]` entries are objects
`{bssid, rssi?}`.

### Command Reference

| Command | Description |
|---------|-------------|
| `./geo.sh up` | Build and start DB + API (dynamic port) |
| `./geo.sh url` | Print the API URL |
| `./geo.sh load cells <FILE>` | Load cell towers (OpenCelliD CSV) |
| `./geo.sh load wifi <FILE>` | Load WiFi APs (WiGLE JSON or web CSV) |
| `./geo.sh down` | Stop everything |
| `./fetch.sh cells <MCC>` | Download cell towers for a country |
| `./fetch.sh wifi <lat1> <lon1> <lat2> <lon2>` | Download WiFi APs in a box |
| `./fetch.sh agnss <YYYY> <DDD>` | Download GNSS ephemeris (day of year) |

---

## Project Structure

Layered so dependencies point inward (domain depends on nothing):

```text
app/
  config.py       Settings — single source of truth for env vars
  db.py           MariaDB connection factory (shared by API + loader)
  domain.py       PURE business logic: signal_weight, weighted_centroid, bounding_box
  repository.py   Data access — all SQL lives here
  schemas.py      Pydantic request/response models
  security.py     X-API-Key auth dependency (constant-time compare)
  middleware.py   ASGI middleware: request body-size limit + security headers
  loaders.py      Parse OpenCelliD/WiGLE files → rows (no DB)
  main.py         Presentation — thin FastAPI routes wiring domain + repository
load.py           CLI: loaders + repository.bulk_replace
tests/            Unit tests: domain, loaders, API routes, middleware (no DB)
```

## Tests

```bash
pip install -e .[dev]
python -m ruff check .                # lint
python -m mypy app load.py            # type check
python -m bandit -q -r app load.py    # security (SAST)
python -m pytest                      # tests (domain, loaders, API, middleware)
```

The domain logic and file parsing are pure functions, unit-tested without a database;
the API routes are tested with FastAPI's `TestClient` and a mocked repository. CI
(GitHub Actions) runs **ruff + mypy + bandit + pytest** on every push and PR, and a
separate **CodeQL** workflow runs `security-extended` analysis on push/PR and weekly.

## Database Schema

```sql
cells(radio, mcc, mnc, area, cid, lon, lat, range, samples, pt)   -- OpenCelliD format
wifi (bssid, ssid, lon, lat, pt)                                  -- WiGLE format
```

`area` = LAC (2G/3G) or TAC (4G/5G). `cid` = cell identifier. `mcc` = country
(Spain `214`), `mnc` = operator (Movistar `07`, etc.).

`pt` is a `POINT` column with a **SPATIAL INDEX**, used by `/nearest`. It's filled
automatically by a `BEFORE INSERT` trigger from `lon`/`lat` (MariaDB can't put a
spatial index on a generated column, so the loaders stay unchanged).

---

## About A-GNSS

A-GNSS (*Assisted GNSS*) is satellite orbit data a phone downloads so the GPS chip
fixes position in seconds instead of minutes. It needs no database — it's served by:

- **CDDIS / IGS** — RINEX broadcast ephemeris files (what `./fetch.sh agnss` downloads).
- **SUPL servers** — the actual A-GNSS protocol, e.g. `supl.google.com:7275`.

The downloaded file is a RINEX navigation file (`IGS BROADCAST EPHEMERIS`).
Demonstrating retrieval is enough here; integrating it into a real GNSS receiver is
a separate project.

---

## Security

See [SECURITY.md](SECURITY.md) for the full posture and how to report issues. Highlights:

- **Auth** — optional `X-API-Key`, compared in constant time.
- **Input validation** — `/nearest` bounds lat/lon/radius/limit; `/geolocate` caps batch
  size and rssi range; all SQL is parameterized.
- **Request body limit** — bodies over 1 MB are rejected with `413` (covers chunked too).
- **Hardened responses** — `X-Content-Type-Options: nosniff`, no `Server` header.
- **Container** — runs as a non-root user; API and DB bind to `127.0.0.1` only.
- **CI security gate** — `bandit` + `CodeQL` (SAST); GitHub Actions pinned to SHAs.

---

## Design Notes

- **Geolocation is a weighted centroid, not full least-squares multilateration** —
  RSSI weighting (signal power) and a spatial index for `/nearest` are implemented;
  solving the actual circle intersection would improve sub-500 m accuracy further.
- **Auth is a single API key, not OAuth/JWT** — enough to gate the API before
  exposing it; add token-based auth if you need per-user access.
- **MariaDB and the API bind to dynamic localhost ports** — do not expose MariaDB in
  production.
- **One DB connection per operation, no pool** — the repository encapsulates each
  query with its own short-lived connection. Fine at this scale; add a connection pool
  (e.g. via a FastAPI lifespan) if request volume grows.

> **Schema changes need a volume reset.** `init.sql` runs only on an empty MariaDB
> volume. After pulling schema changes, recreate it and reload data:
> ```bash
> docker compose down -v && ./geo.sh up
> ```

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support the Project

If this project is useful in your workflows, you can support development:

<a href="https://buymeacoffee.com/seifreed" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50">
</a>

---

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE).

**Attribution**
- Author: **Marc Rivero López** | [@seifreed](https://github.com/seifreed) | mriverolopez@gmail.com
- Repository: [github.com/seifreed/geoloc-api](https://github.com/seifreed/geoloc-api)

---

<p align="center">
  <sub>Built for practical geolocation and GNSS engineering</sub>
</p>
