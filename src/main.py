import math
import sqlite3
import ssl
import os
import socket
from datetime import datetime, date

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO

DB = "explorador.db"
CERT_FILE = "cert.pem"
KEY_FILE  = "key.pem"

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "explorador-urbano-2025"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ── SSL autoassinado ──────────────────────────────────────────────────────────

def get_local_ip():
    """Descobre o IP local da máquina na rede."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_self_signed_cert(certfile=CERT_FILE, keyfile=KEY_FILE):
    """Gera certificado autoassinado se ainda não existir."""
    if os.path.exists(certfile) and os.path.exists(keyfile):
        print("[SSL] Usando certificado existente.")
        return

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress
        import datetime as dt

        print("[SSL] Gerando certificado autoassinado…")
        local_ip = get_local_ip()

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ExploradorUrbano"),
            x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(dt.datetime.utcnow())
            .not_valid_after(dt.datetime.utcnow() + dt.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv4Address(local_ip)),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(certfile, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        with open(keyfile, "wb") as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))

        print(f"[SSL] Certificado criado para IP {local_ip}.")

    except ImportError:
        # fallback: usa openssl via subprocess
        import subprocess
        local_ip = get_local_ip()
        san = f"subjectAltName=IP:{local_ip},IP:127.0.0.1,DNS:localhost"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", keyfile, "-out", certfile,
            "-days", "3650", "-nodes",
            "-subj", f"/CN={local_ip}",
            "-addext", san,
        ], check=True, capture_output=True)
        print(f"[SSL] Certificado criado via openssl para IP {local_ip}.")


# ── banco de dados ─────────────────────────────────────────────────────────────

def get_db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with get_db() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                nickname   TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                started_at  TEXT NOT NULL,
                ended_at    TEXT,
                distance_m  REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS points (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                lat        REAL NOT NULL,
                lon        REAL NOT NULL,
                ts         TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS online_status (
                user_id    INTEGER PRIMARY KEY,
                session_id INTEGER,
                last_lat   REAL,
                last_lon   REAL,
                last_seen  TEXT,
                status     TEXT DEFAULT 'parado',
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

        cols = [r[1] for r in con.execute("PRAGMA table_info(sessions)").fetchall()]
        if "user_id" not in cols:
            con.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER")
        if "distance_m" not in cols:
            con.execute("ALTER TABLE sessions ADD COLUMN distance_m REAL DEFAULT 0")


init_db()


# ── helpers ───────────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calc_elapsed(started_at, ended_at=None):
    end_str = ended_at or datetime.now().isoformat()
    try:
        return (datetime.fromisoformat(end_str) - datetime.fromisoformat(started_at)).total_seconds()
    except Exception:
        return 0


def build_stats(distance_m, elapsed_s):
    dist_km  = distance_m / 1000
    pace     = (elapsed_s / 60) / dist_km if dist_km > 0.05 else 0
    avg_speed = dist_km / (elapsed_s / 3600) if elapsed_s > 0 else 0
    calories  = dist_km * 60
    h = int(elapsed_s // 3600)
    m = int((elapsed_s % 3600) // 60)
    s = int(elapsed_s % 60)
    elapsed_fmt = f"{h}h {m:02d}min" if h else f"{m}:{s:02d}"
    return {
        "distance_m":        round(distance_m),
        "distance_km":       round(dist_km, 3),
        "elapsed_s":         round(elapsed_s),
        "elapsed_formatted": elapsed_fmt,
        "pace_min_km":       round(pace, 1),
        "avg_speed_kmh":     round(avg_speed, 1),
        "calories":          round(calories),
    }


def calc_current_speed(con, session_id, window=6):
    pts = con.execute(
        "SELECT lat, lon, ts FROM points WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, window),
    ).fetchall()
    if len(pts) < 2:
        return 0.0
    pts = list(reversed(pts))
    dist = sum(
        haversine(pts[i]["lat"], pts[i]["lon"], pts[i + 1]["lat"], pts[i + 1]["lon"])
        for i in range(len(pts) - 1)
    )
    try:
        t1 = datetime.fromisoformat(pts[0]["ts"])
        t2 = datetime.fromisoformat(pts[-1]["ts"])
        elapsed_s = (t2 - t1).total_seconds()
    except Exception:
        elapsed_s = 0
    return round((dist / elapsed_s) * 3.6, 1) if elapsed_s >= 1 else 0.0


def movement_status(speed_kmh):
    if speed_kmh > 2.0:
        return "andando"
    if speed_kmh > 0.5:
        return "devagar"
    return "parado"


# ── auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register():
    data     = request.get_json() or {}
    name     = data.get("name", "").strip()
    nickname = data.get("nickname", "").strip().lower()
    if not name or not nickname:
        return jsonify(error="Nome e apelido são obrigatórios"), 400
    with get_db() as con:
        if con.execute("SELECT 1 FROM users WHERE nickname=?", (nickname,)).fetchone():
            return jsonify(error="Apelido já em uso"), 409
        cur = con.execute(
            "INSERT INTO users (name, nickname, created_at) VALUES (?,?,?)",
            (name, nickname, datetime.now().isoformat()),
        )
    return jsonify(user_id=cur.lastrowid, name=name, nickname=nickname)


@app.post("/auth/login")
def login():
    data     = request.get_json() or {}
    nickname = data.get("nickname", "").strip().lower()
    with get_db() as con:
        user = con.execute(
            "SELECT id, name, nickname FROM users WHERE nickname=?", (nickname,)
        ).fetchone()
        if not user:
            return jsonify(error="Usuário não encontrado"), 404
    return jsonify(user_id=user["id"], name=user["name"], nickname=user["nickname"])


@app.get("/users")
def list_users():
    with get_db() as con:
        rows = con.execute("SELECT id, name, nickname FROM users ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


# ── sessões ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return send_from_directory("static", "index.html")


@app.post("/session/start")
def start_session():
    data    = request.get_json() or {}
    user_id = data.get("user_id")
    ts      = datetime.now().isoformat()
    with get_db() as con:
        cur = con.execute(
            "INSERT INTO sessions (user_id, started_at, distance_m) VALUES (?,?,0)",
            (user_id, ts),
        )
        session_id = cur.lastrowid
        if user_id:
            con.execute(
                """INSERT INTO online_status (user_id, session_id, last_seen, status)
                   VALUES (?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       session_id=excluded.session_id,
                       last_seen=excluded.last_seen,
                       status=excluded.status""",
                (user_id, session_id, ts, "parado"),
            )
    socketio.emit("session_start", {"user_id": user_id, "session_id": session_id})
    return jsonify(session_id=session_id)


@app.post("/session/stop/<int:session_id>")
def stop_session(session_id):
    ts = datetime.now().isoformat()
    with get_db() as con:
        con.execute("UPDATE sessions SET ended_at=? WHERE id=?", (ts, session_id))
        row = con.execute("SELECT user_id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row and row["user_id"]:
            con.execute(
                "DELETE FROM online_status WHERE user_id=? AND session_id=?",
                (row["user_id"], session_id),
            )
    socketio.emit("session_stop", {"session_id": session_id})
    return jsonify(ok=True)


@app.post("/location")
def receive_location():
    data = request.get_json()
    sid, lat, lon = data["session_id"], data["lat"], data["lon"]
    ts = datetime.now().isoformat()

    with get_db() as con:
        last = con.execute(
            "SELECT lat, lon FROM points WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()
        delta = haversine(last["lat"], last["lon"], lat, lon) if last else 0.0
        con.execute(
            "INSERT INTO points (session_id, lat, lon, ts) VALUES (?,?,?,?)",
            (sid, lat, lon, ts),
        )
        con.execute(
            "UPDATE sessions SET distance_m = COALESCE(distance_m, 0) + ? WHERE id=?",
            (delta, sid),
        )
        sess = con.execute(
            "SELECT user_id, started_at, distance_m FROM sessions WHERE id=?", (sid,)
        ).fetchone()

        if sess and sess["user_id"]:
            cur_spd = calc_current_speed(con, sid)
            status  = movement_status(cur_spd)
            elapsed = calc_elapsed(sess["started_at"])
            stats   = build_stats(sess["distance_m"] or 0, elapsed)
            con.execute(
                """INSERT INTO online_status
                       (user_id, session_id, last_lat, last_lon, last_seen, status)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       session_id=excluded.session_id,
                       last_lat=excluded.last_lat,
                       last_lon=excluded.last_lon,
                       last_seen=excluded.last_seen,
                       status=excluded.status""",
                (sess["user_id"], sid, lat, lon, ts, status),
            )
            user = con.execute(
                "SELECT name, nickname FROM users WHERE id=?", (sess["user_id"],)
            ).fetchone()
            socketio.emit("location_update", {
                "user_id":           sess["user_id"],
                "nickname":          user["nickname"] if user else "anon",
                "name":              user["name"] if user else "Anônimo",
                "lat":               lat,
                "lon":               lon,
                "status":            status,
                "current_speed_kmh": cur_spd,
                **stats,
            })

    return jsonify(ok=True)


@app.get("/sessions")
def list_sessions():
    with get_db() as con:
        rows = con.execute(
            "SELECT id, user_id, started_at, ended_at, distance_m FROM sessions ORDER BY id DESC"
        ).fetchall()
        result = []
        for row in rows:
            elapsed  = calc_elapsed(row["started_at"], row["ended_at"])
            stats    = build_stats(row["distance_m"] or 0, elapsed)
            pt_count = con.execute(
                "SELECT COUNT(*) FROM points WHERE session_id=?", (row["id"],)
            ).fetchone()[0]
            result.append({
                "id":         row["id"],
                "user_id":    row["user_id"],
                "started_at": row["started_at"],
                "ended_at":   row["ended_at"],
                "point_count": pt_count,
                **stats,
            })
    return jsonify(result)


@app.get("/users/<int:user_id>/sessions")
def user_sessions(user_id):
    with get_db() as con:
        rows = con.execute(
            "SELECT id, started_at, ended_at, distance_m FROM sessions WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        result = []
        for row in rows:
            elapsed  = calc_elapsed(row["started_at"], row["ended_at"])
            stats    = build_stats(row["distance_m"] or 0, elapsed)
            pt_count = con.execute(
                "SELECT COUNT(*) FROM points WHERE session_id=?", (row["id"],)
            ).fetchone()[0]
            result.append({
                "id":          row["id"],
                "started_at":  row["started_at"],
                "ended_at":    row["ended_at"],
                "point_count": pt_count,
                **stats,
            })
    return jsonify(result)


@app.get("/session/<int:session_id>/track")
def get_track(session_id):
    with get_db() as con:
        pts = con.execute(
            "SELECT lat, lon, ts FROM points WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
    return jsonify([{"lat": p["lat"], "lon": p["lon"], "ts": p["ts"]} for p in pts])


# ── ranking ───────────────────────────────────────────────────────────────────

@app.get("/ranking/daily")
def daily_ranking():
    today = date.today().isoformat()
    with get_db() as con:
        rows = con.execute(
            """SELECT s.user_id, u.name, u.nickname,
                      SUM(COALESCE(s.distance_m, 0)) AS total_dist,
                      SUM(CASE
                            WHEN s.ended_at IS NOT NULL
                            THEN (julianday(s.ended_at) - julianday(s.started_at)) * 86400
                            ELSE (julianday('now') - julianday(s.started_at)) * 86400
                          END) AS total_elapsed,
                      COUNT(*) AS session_count
               FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.started_at LIKE ? AND s.user_id IS NOT NULL
               GROUP BY s.user_id
               ORDER BY total_dist DESC""",
            (today + "%",),
        ).fetchall()

    ranking = []
    for i, r in enumerate(rows):
        dist_m  = r["total_dist"] or 0
        elapsed = r["total_elapsed"] or 0
        stats   = build_stats(dist_m, elapsed)
        ranking.append({
            "position":         i + 1,
            "user_id":          r["user_id"],
            "name":             r["name"],
            "nickname":         r["nickname"],
            "session_count":    r["session_count"],
            **stats,
            "total_distance_m": round(dist_m),
        })
    return jsonify(ranking)


@app.get("/ranking/live")
def live_ranking():
    with get_db() as con:
        online = con.execute(
            """SELECT os.*, u.name, u.nickname, s.started_at, s.distance_m
               FROM online_status os
               JOIN users u ON os.user_id = u.id
               LEFT JOIN sessions s ON os.session_id = s.id
               WHERE os.last_seen IS NOT NULL""",
        ).fetchall()

        result = []
        now = datetime.now()
        for row in online:
            try:
                diff_s = (now - datetime.fromisoformat(row["last_seen"])).total_seconds()
                if diff_s > 300:
                    continue
            except Exception:
                continue

            cur_spd = calc_current_speed(con, row["session_id"]) if row["session_id"] else 0
            elapsed = calc_elapsed(row["started_at"]) if row["started_at"] else 0
            stats   = build_stats(row["distance_m"] or 0, elapsed)
            result.append({
                "user_id":           row["user_id"],
                "name":              row["name"],
                "nickname":          row["nickname"],
                "status":            row["status"],
                "current_speed_kmh": cur_spd,
                "last_seen_s":       round(diff_s),
                **stats,
            })

    result.sort(key=lambda x: x.get("distance_m", 0), reverse=True)
    return jsonify(result)


# ── websocket ──────────────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    pass

@socketio.on("disconnect")
def on_disconnect():
    pass


# ── start ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PORT = 8443  # porta HTTPS padrão alternativa
    generate_self_signed_cert()

    local_ip = get_local_ip()
    print("=" * 52)
    print("  Explorador Urbano — HTTPS")
    print("=" * 52)
    print(f"  Notebook : https://localhost:{PORT}")
    print(f"  Celular  : https://{local_ip}:{PORT}")
    print()
    print("  ⚠  No celular, aceite o aviso de 'conexão")
    print("     não confiável' para liberar o GPS.")
    print("=" * 52)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(CERT_FILE, KEY_FILE)

    socketio.run(
        app,
        host="0.0.0.0",
        port=PORT,
        debug=False,
        ssl_context=ssl_context,
    )