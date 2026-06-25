# 🗺️ Explorador Urbano

> A web app that tracks urban routes in real time, drawing each user's GPS trail on a live map and ranking everyone by daily distance — updates pushed over WebSocket.

<!-- TODO: screenshot do mapa + ranking -->
![demo](docs/demo.png)

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-black?logo=flask)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_mode-003B57?logo=sqlite)](https://sqlite.org)
[![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9.4-199900?logo=leaflet)](https://leafletjs.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-realtime-010101?logo=socket.io)](https://socket.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🇧🇷 Versão em português: [`README.pt.md`](README.pt.md)

---

## What it does

Each user logs in by nickname and starts a tracking session. The browser streams GPS
positions (`navigator.geolocation.watchPosition`) to the server, which stores every point,
accumulates the traveled distance with the Haversine formula, and broadcasts the update to
all connected clients over Socket.IO. The frontend (single-page, four tabs) shows the live
trail on a Leaflet map, the user's session history with a Chart.js evolution chart, a daily
distance ranking with medals for the top 3, and a live feed of who is currently moving.

On the desktop, where real GPS is usually unavailable, a **simulation mode** lets you click
on the map to drop points — the same pipeline runs end to end.

---

## Tech stack

| Layer      | Technology                                          |
|------------|-----------------------------------------------------|
| Backend    | Python 3.10+ · Flask                                |
| Real-time  | Flask-SocketIO (`async_mode="threading"`)           |
| Database   | SQLite3 (stdlib) · WAL journal mode                 |
| Frontend   | HTML5 · CSS3 · vanilla JS ES6+ (single file)        |
| Map        | Leaflet.js 1.9.4 · OpenStreetMap tiles (via CDN)    |
| Charts     | Chart.js (via CDN)                                  |
| Geolocation| Web Geolocation API                                 |
| TLS        | `cryptography` (programmatic self-signed cert), with `openssl` CLI fallback |

No external services: no managed database, no cloud, no ORM.

---

## Running it

The source lives under `src/`. All commands below start from the repository root.

```bash
# 1. clone
git clone https://github.com/EduardoTBuss/explorador-urbano
cd explorador-urbano

# 2. create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. install dependencies
pip install -r src/requirements.txt

# 4. start the server (run from inside src/)
cd src
python main.py
```

Expected output:

```
====================================================
  Explorador Urbano — HTTPS
====================================================
  Notebook : https://localhost:8443
  Celular  : https://192.168.x.x:8443
====================================================
```

Then open **https://localhost:8443** in your browser.

The SQLite database (`explorador.db`) and the self-signed certificate (`cert.pem` /
`key.pem`) are created automatically on first run, inside `src/`.

> ⚠️ The programmatic certificate generation relies on the `cryptography` package, which is
> **not pinned** in `src/requirements.txt`. If it is missing, the app falls back to invoking
> the `openssl` CLI. To guarantee the in-process path: `pip install cryptography`.

### Using it on a phone (real GPS)

Browsers block `navigator.geolocation` over plain HTTP outside `localhost`, so a phone needs
HTTPS. The phone and the host must be on the same network — a phone hotspot is the most
reliable option on isolated university Wi-Fi:

```
1. Turn on the phone hotspot
2. Connect the laptop to that hotspot
3. cd src && python main.py
4. On the phone browser: https://192.168.x.x:8443
5. Accept the "not secure / untrusted" warning (the self-signed cert)
```

The server generates the self-signed certificate with the host's local IP in the SAN
(Subject Alternative Name) field, which is what lets the phone reach it over `https://` and
the browser release the geolocation API.

---

## Technical decisions

**Why WebSocket for real time?** Tracking is inherently push-based: one user's new position
must reach every other connected client without them polling. Flask-SocketIO keeps a
persistent channel and the server emits `location_update`, `session_start` and
`session_stop` events as they happen. Clients react by refreshing the live list, ranking and
their own history — no fixed-interval polling against the API.

**Why SQLite in WAL mode?** The app is single-file and dependency-light by design, so SQLite
fits. But Flask-SocketIO runs in `threading` mode, so multiple requests (and the location
writer) hit the same database file concurrently. The default rollback journal serializes
readers against the writer; `PRAGMA journal_mode=WAL` lets readers proceed without blocking
the writer, which keeps the live ranking and track queries responsive while points are being
ingested. Connections are opened with `check_same_thread=False` for the same reason.

**Incremental distance accumulation.** Each `POST /location` computes only the Haversine
delta from the previous point and adds it to `sessions.distance_m`. Distance is never
recomputed over the full point list on every update — that O(n) recompute would degrade as a
session grows long.

**How the multi-user ranking is computed.** Two distinct views:
- **Daily ranking** (`GET /ranking/daily`): a single aggregated SQL query groups today's
  sessions by user (matched via `started_at LIKE 'YYYY-MM-DD%'`), sums `distance_m` and
  elapsed seconds, and orders by total distance descending. Positions and medals (top 3) are
  assigned from that order. No per-point looping.
- **Live ranking** (`GET /ranking/live`): reads the `online_status` table (one row per user,
  upserted on every location update), drops anyone whose `last_seen` is older than 5 minutes,
  derives current speed from the last 6 points, and sorts by distance. This is what powers
  the "who's moving now" feed.

Movement status is bucketed from current speed: `> 2.0 km/h` → *andando*, `> 0.5` →
*devagar*, else *parado*.

---

## API reference

### Auth
| Method | Route             | Body               | Description            |
|--------|-------------------|--------------------|------------------------|
| POST   | `/auth/register`  | `{name, nickname}` | Create a user          |
| POST   | `/auth/login`     | `{nickname}`       | Log in (nickname only) |
| GET    | `/users`          | —                  | List users             |

### Sessions & location
| Method | Route                         | Body                     | Description           |
|--------|-------------------------------|--------------------------|-----------------------|
| POST   | `/session/start`              | `{user_id}`              | Start a session       |
| POST   | `/session/stop/<id>`          | —                        | End a session         |
| POST   | `/location`                   | `{session_id, lat, lon}` | Record a GPS point    |
| GET    | `/sessions`                   | —                        | All sessions          |
| GET    | `/users/<user_id>/sessions`   | —                        | A user's history      |
| GET    | `/session/<id>/track`         | —                        | A session's GPS points|

### Ranking
| Method | Route             | Description                            |
|--------|-------------------|----------------------------------------|
| GET    | `/ranking/daily`  | Today's ranking by total distance      |
| GET    | `/ranking/live`   | Users active in the last 5 minutes     |

### WebSocket event — `location_update`
```json
{
  "user_id": 1,
  "nickname": "edu",
  "name": "Eduardo",
  "lat": -31.7707,
  "lon": -52.3414,
  "status": "andando",
  "current_speed_kmh": 4.2,
  "distance_m": 380,
  "pace_min_km": 13.7,
  "calories": 23
}
```
Also emitted: `session_start` and `session_stop`.

---

## Data model

```sql
users         → id, name, nickname, created_at
sessions      → id, user_id, started_at, ended_at, distance_m
points        → id, session_id, lat, lon, ts
online_status → user_id, session_id, last_lat, last_lon, last_seen, status
```

---

## Repository layout

```
explorador-urbano/
├── README.md                # this file (English, showcase)
├── README.pt.md             # Portuguese version
├── LICENSE                  # MIT
├── relatorio_explorador.pdf # methodology / AI-assisted process report
└── src/
    ├── main.py              # Flask server: routes, WebSocket, SSL, logic
    ├── requirements.txt     # Python dependencies
    └── static/
        └── index.html       # full frontend (HTML + CSS + JS in one file)
```

`explorador.db`, `cert.pem` and `key.pem` are generated at runtime and are not versioned.

---

## Status & known limitations

This is a portfolio / coursework demo, not hardened for production:

- **No real authentication** — login is by nickname only, with no password or session token.
  Knowing a nickname is enough to act as that user.
- **`SECRET_KEY` is hardcoded** in `main.py`; it should come from an environment variable.
- **No input validation** on the endpoints — out-of-range `lat`/`lon` are accepted, and a
  `/location` body missing keys can raise a `KeyError`.
- **`cryptography` is not pinned** in `requirements.txt` (see the note under "Running it");
  the `-e flask` line in that file is also unusual.
- **CORS is open** (`cors_allowed_origins="*"`) on Socket.IO.
- **Development server** (`socketio.run`) — no production WSGI server.
- **Calories** are a rough estimate (`km × 60`), independent of weight or pace.
- **Everything in two files** — backend logic in `main.py`, the entire frontend in
  `static/index.html`.

### Roadmap
- [ ] Input validation on endpoints
- [ ] Move `SECRET_KEY` to `.env` and pin `cryptography`
- [ ] Heatmap of most-traveled streets (Leaflet heatmap)
- [ ] Export routes as GPX (Strava / Garmin)
- [ ] Installable PWA
- [ ] Split routes into Flask Blueprints (`auth`, `sessions`, `ranking`)

### Suggested deployment
For a public demo, run behind a production WSGI/ASGI server with WebSocket support
(e.g. `gunicorn` with an `eventlet`/`gevent` worker, or `uvicorn` fronting an ASGI bridge),
put it behind a reverse proxy (nginx) terminating a real TLS certificate (Let's Encrypt), and
externalize secrets first. The bundled self-signed certificate is intended only for local
LAN/phone testing.

---

## License

MIT © 2026 Eduardo Timm Buss — see [LICENSE](LICENSE).

---

*Built for the "AI in Software Development" course — Computer Engineering, UFPel (2026).*
