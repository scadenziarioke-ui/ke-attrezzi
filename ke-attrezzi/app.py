import os
import json
import time
from datetime import datetime, timedelta
from functools import wraps
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "ke-attrezzi-secret-changeme")
app.permanent_session_lifetime = timedelta(hours=8)

LOGIN_USERNAME = os.environ.get("LOGIN_USERNAME", "admin")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "kegroup2024")
DATABASE_URL   = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgres://", 1)

_login_attempts = {}
MAX_ATTEMPTS  = 5
BLOCK_SECONDS = 15 * 60

def check_rate(ip):
    now = time.time()
    e = _login_attempts.get(ip, {"count": 0, "blocked_until": 0})
    if e["blocked_until"] > now:
        return False, int((e["blocked_until"] - now) / 60) + 1
    return True, 0

def record_fail(ip):
    now = time.time()
    e = _login_attempts.get(ip, {"count": 0, "blocked_until": 0})
    e["count"] += 1
    if e["count"] >= MAX_ATTEMPTS:
        e["blocked_until"] = now + BLOCK_SECONDS
        e["count"] = 0
    _login_attempts[ip] = e

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=10)

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attrezzi (
                    id        SERIAL PRIMARY KEY,
                    codice    TEXT UNIQUE NOT NULL,
                    nome      TEXT NOT NULL,
                    categoria TEXT DEFAULT 'Manuale',
                    marca     TEXT,
                    qty_tot   INTEGER DEFAULT 1,
                    note      TEXT,
                    stato     TEXT DEFAULT 'disp',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS cantieri (
                    id        SERIAL PRIMARY KEY,
                    codice    TEXT UNIQUE NOT NULL,
                    nome      TEXT NOT NULL,
                    data_inizio DATE,
                    data_fine   DATE,
                    stato     TEXT DEFAULT 'attivo',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS operatori (
                    id        SERIAL PRIMARY KEY,
                    codice    TEXT UNIQUE NOT NULL,
                    nome      TEXT NOT NULL,
                    cognome   TEXT,
                    ruolo     TEXT DEFAULT 'Operaio Specializzato',
                    telefono  TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS movimenti (
                    id           SERIAL PRIMARY KEY,
                    codice       TEXT UNIQUE NOT NULL,
                    data_uscita  DATE NOT NULL,
                    attrezzo_id  INTEGER REFERENCES attrezzi(id) ON DELETE SET NULL,
                    attrezzo_nome TEXT,
                    cantiere_id  INTEGER REFERENCES cantieri(id) ON DELETE SET NULL,
                    cantiere_nome TEXT,
                    operatore_id  INTEGER REFERENCES operatori(id) ON DELETE SET NULL,
                    operatore_nome TEXT,
                    qty           INTEGER DEFAULT 1,
                    data_rientro_prev DATE,
                    data_rientro_eff  DATE,
                    stato         TEXT DEFAULT 'cantiere',
                    note          TEXT,
                    created_at    TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            conn.commit()
            _seed_data(cur, conn)

def _seed_data(cur, conn):
    cur.execute("SELECT COUNT(*) as n FROM attrezzi")
    if cur.fetchone()["n"] > 0:
        return
    attrezzi_data = [
        ('ATT-001','BOLLE','Manuale',None,19,'disp'),('ATT-002','MAZZETTE','Manuale',None,9,'disp'),
        ('ATT-003','TENAGLIE','Manuale',None,4,'disp'),('ATT-004','FORBICI LATTONERIA','Manuale',None,2,'disp'),
        ('ATT-005','SCALPELLI','Manuale',None,10,'disp'),('ATT-006','SEGHETTI CARTONGESSO','Manuale',None,5,'disp'),
        ('ATT-007','CUTTER','Manuale',None,6,'disp'),('ATT-008','LEVERINI','Manuale',None,4,'disp'),
        ('ATT-009','MARTELLI CARPENTIERE','Manuale',None,5,'disp'),('ATT-010','MARTELLO MURATORE','Manuale',None,1,'disp'),
        ('ATT-011','RIVELLATRICI','Misura',None,3,'disp'),('ATT-012','SEGA','Manuale',None,5,'disp'),
        ('ATT-013','SPAZZOLA FERRO','Manuale',None,5,'disp'),('ATT-014','FERRETTI','Manuale',None,4,'disp'),
        ('ATT-015','SEGHETTI FERRO','Manuale',None,5,'disp'),('ATT-016','SQUADRE','Misura',None,9,'disp'),
        ('ATT-017','CAZZUOLA','Manuale',None,17,'cant'),('ATT-018','CAZZUOLINI','Manuale',None,8,'disp'),
        ('ATT-019','FRATASSI IN SPUGNA','Manuale',None,16,'disp'),('ATT-020','SPATOLE AMERICANE GRANDI','Manuale',None,14,'cant'),
        ('ATT-021','SPATOLE AMERICANE PICCOLE','Manuale',None,11,'disp'),('ATT-022','SPATOLE AMERICANE IN PLASTICA','Manuale',None,7,'cant'),
        ('ATT-023','ASPIRAPOLVERE','Elettrico',None,6,'cant'),('ATT-024','LASER A CAVALLETTO','Misura',None,1,'cant'),
        ('ATT-025','SPARACHIODI A BATTERIA','Elettrico',None,1,'disp'),('ATT-026','SPARACHIODI A GAS','Pneumatico',None,1,'disp'),
        ('ATT-027','SALDATRICE','Saldatura',None,1,'disp'),('ATT-028','MISCELATORE','Elettrico',None,3,'cant'),
        ('ATT-029','CARTEGGIATRICE ELETTRICA','Elettrico',None,2,'disp'),('ATT-030','PHON','Elettrico',None,1,'disp'),
        ('ATT-031','SEGHETTO ALTERNATIVO','Elettrico',None,1,'disp'),('ATT-032','TAGLIA CAPPOTTO PICCOLO','Elettrico',None,1,'disp'),
        ('ATT-033','TAGLIA CAPPOTTO GRANDE','Elettrico',None,1,'disp'),('ATT-034','CARRELLINI','Trasporto',None,2,'disp'),
        ('ATT-035','LEVIGATRICE PAVIMENTO','Elettrico',None,1,'disp'),('ATT-036','FLESSIBILE GRANDE','Elettrico',None,4,'disp'),
        ('ATT-037','FLESSIBILE PICCOLO A BATTERIA','Elettrico',None,4,'cant'),('ATT-038','FLESSIBILE PICCOLO ELETTRICO','Elettrico',None,2,'disp'),
        ('ATT-039','SEGA ELETTRICA','Elettrico',None,1,'disp'),('ATT-040','AVVITATORE MAKITA','Elettrico','Makita',7,'disp'),
        ('ATT-041','SEGA CIRCOLARE A BATTERIA','Elettrico',None,1,'disp'),('ATT-042','RIVELLATRICE A BATTERIA','Misura',None,1,'disp'),
        ('ATT-043','MISURATORE LASER','Misura',None,1,'disp'),('ATT-044','TAGLIERINA DA BANCO DEWALT','Elettrico','DeWalt',1,'disp'),
        ('ATT-045','TRAPANO A BATTERIA MILWAUKEE','Elettrico','Milwaukee',3,'disp'),('ATT-046','TRAPANO ELETTRICO MAKITA','Elettrico','Makita',4,'disp'),
        ('ATT-047','TRAPANO BOSCH','Elettrico','Bosch',1,'disp'),('ATT-048','TRAPANO A BATTERIA MAKITA','Elettrico','Makita',4,'disp'),
        ('ATT-049','AUTO AVVOLGENTE LINEE VITA','Sicurezza',None,2,'disp'),('ATT-050','CINGHIE DI SICUREZZA','Sicurezza',None,10,'disp'),
        ('ATT-051','IMBRAGATURA TRACTEL','Sicurezza','Tractel',2,'disp'),('ATT-052','TENDI BULLONE A BATTERIA MILWAUKEE','Elettrico','Milwaukee',1,'disp'),
        ('ATT-053','TENDI BULLONE ELETTRICO BOSCH','Elettrico','Bosch',1,'disp'),('ATT-054','SCANALATRICE ELETTRICA MAKITA','Elettrico','Makita',1,'disp'),
        ('ATT-055','RASCHIETTO ELETTRICO MAKITA','Elettrico','Makita',1,'disp'),('ATT-056','SEGA CIRCOLARE ELETTRICA','Elettrico',None,1,'disp'),
        ('ATT-057','MARTELLO DEMOLITORE ELETTRICO MAKITA','Elettrico','Makita',4,'cant'),('ATT-058','MARTELLO DEMOLITORE ELETTRICO GRANDE','Elettrico',None,2,'disp'),
        ('ATT-059','CAROTATRICE ELETTRICA GEITEC','Elettrico','Geitec',1,'disp'),('ATT-060','CANNONE STUFA A GAS','Energia',None,1,'disp'),
        ('ATT-061','GIRAFFA LEVIGATRICE CARTONGESSO','Elettrico',None,1,'disp'),('ATT-062','FRATASSATRICE ELETTRICA','Elettrico',None,1,'disp'),
        ('ATT-063','MOTOSEGHE','Elettrico',None,2,'disp'),('ATT-064','PISTOLA SILICONE','Manuale',None,0,'fuori'),
        ('ATT-065','CARRUCOLA','Trasporto',None,1,'disp'),('ATT-066','AVVITATORE PICCOLO DEWALT','Elettrico','DeWalt',1,'disp'),
        ('ATT-067','CASSETTINA BETA TENDIBULLONI','Manuale','Beta',1,'disp'),('ATT-068','SCHIACCIA COPRICORDA ELETTRICO','Elettrico',None,1,'disp'),
        ('ATT-069','FRATASSI PLASTICA MURATORE','Manuale',None,12,'disp'),('ATT-070','RABOT','Elettrico',None,6,'cant'),
        ('ATT-071','RASCHIA INTONACO MANUALI','Manuale',None,6,'disp'),('ATT-072','PINZATRICE ELETTRICA RIGIDA','Elettrico',None,1,'disp'),
        ('ATT-073','TRANCINI','Manuale',None,4,'disp'),('ATT-074','VENTOSE PER VETRI','Manuale',None,2,'disp'),
        ('ATT-075','TRANSPALLET','Trasporto',None,2,'disp'),('ATT-076','SCALE CON APERTURA A LIBRO','Accesso',None,3,'disp'),
        ('ATT-077','SCALE','Accesso',None,11,'cant'),('ATT-078','SECCHI','Manuale',None,15,'disp'),
        ('ATT-079','GABASSI QUADRATI','Manuale',None,41,'cant'),('ATT-080','GABASSI PICCOLI','Manuale',None,4,'disp'),
        ('ATT-081','RASPE','Manuale',None,6,'disp'),('ATT-082','RASPINI GRANDI','Manuale',None,4,'disp'),
        ('ATT-083','BADILI','Manuale',None,9,'cant'),('ATT-084','SCOPE','Manuale',None,3,'cant'),
        ('ATT-085','BETTONIERA GRANDE','Elettrico',None,2,'cant'),('ATT-086','BETTONIERA PICCOLA','Elettrico',None,1,'disp'),
        ('ATT-087','SEGA CIRCOLARE GRANDE','Elettrico',None,1,'disp'),('ATT-088','CARIOLE','Trasporto',None,8,'disp'),
        ('ATT-089','TRIVELLA','Elettrico',None,1,'disp'),('ATT-090','CAZZUOLA QUADRATA','Manuale',None,1,'disp'),
        ('ATT-091','BOMBOLA 10 KG','Energia',None,3,'disp'),('ATT-092','CANNELLO GROSSO PER BOMBOLE','Energia',None,2,'disp'),
        ('ATT-093','PICCONI','Manuale',None,4,'disp'),('ATT-094','BATTERIE','Accessori',None,15,'disp'),
        ('ATT-095','CARICA BATTERIE','Accessori',None,10,'disp'),('ATT-096','CARICA BATTERIE DOPPIO','Accessori',None,1,'disp'),
        ('ATT-097','FLESSIBILI (PROLUNGHE)','Accessori',None,5,'disp'),('ATT-098','FLESSIBILE A CORRENTE','Accessori',None,3,'disp'),
        ('ATT-099','TASSELLATORE MILWAUKEE M18','Elettrico','Milwaukee',1,'disp'),('ATT-100','SMERIGLIATRICE ANGOLARE MILWAUKEE M18','Elettrico','Milwaukee',1,'disp'),
        ('ATT-101','UTENSILE MULTIFUNZIONE OSCILLANTE BOSCH','Elettrico','Bosch',1,'disp'),('ATT-102','LASER ROTATIVO STANLEY','Misura','Stanley',1,'disp'),
        ('ATT-103','TREPPIEDE PER LASER','Misura',None,1,'disp'),('ATT-104','FARO LED DA CANTIERE RICARICABILE','Energia',None,1,'disp'),
        ('ATT-105','TRACCIALINEE MANUALE','Misura',None,1,'disp'),('ATT-106','MOTOSEGA ELETTRICA MAKITA','Elettrico','Makita',1,'disp'),
        ('ATT-107','MOTOSEGA A BATTERIA MAKITA','Elettrico','Makita',1,'disp'),('ATT-108','MARTELLO DEMOLITORE HILTI A BATTERIA','Elettrico','Hilti',1,'disp'),
        ('ATT-109','SMERIGLIATRICE ANGOLARE HILTI 230MM','Elettrico','Hilti',1,'disp'),('ATT-110','LEVIGATRICE PER CEMENTO HILTI','Elettrico','Hilti',1,'disp'),
    ]
    for row in attrezzi_data:
        cur.execute("INSERT INTO attrezzi (codice,nome,categoria,marca,qty_tot,stato) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", row)

    cantieri_data = [
        ('C001','Cantiere Cagnola (CAGNOLA)','attivo'),
        ('C002','Cantiere Pioltello Milano (PIOLTELLO VIA MILANO)','attivo'),
        ('C003','Cantiere Zogno (ZOGNO)','attivo'),
    ]
    for row in cantieri_data:
        cur.execute("INSERT INTO cantieri (codice,nome,stato) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", row)

    operatori_data = [
        ('OP-001','GIANNI',None,'Operaio Specializzato'),
        ('OP-002','MASSIMO',None,'Capo Cantiere'),
        ('OP-003','ANGELO',None,'Elettricista'),
        ('OP-004','PATRIZIO',None,'Elettricista'),
        ('OP-005','CARMELO',None,'Elettricista'),
    ]
    for row in operatori_data:
        cur.execute("INSERT INTO operatori (codice,nome,cognome,ruolo) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", row)

    movimenti_data = [
        ('MOV-001','2025-10-16','CAZZUOLA','CAGNOLA','GIANNI',3,'cantiere','1 ROTTA'),
        ('MOV-002','2025-10-16','SPATOLE AMERICANE GRANDI','CAGNOLA','GIANNI',5,'cantiere',None),
        ('MOV-003','2025-10-16','SPATOLE AMERICANE IN PLASTICA','CAGNOLA','GIANNI',1,'cantiere','1 ROTTA'),
        ('MOV-004','2025-10-16','ASPIRAPOLVERE','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-005','2025-10-16','LASER A CAVALLETTO','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-006','2025-10-16','MISCELATORE','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-007','2025-10-16','FLESSIBILE PICCOLO A BATTERIA','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-008','2025-10-16','MARTELLO DEMOLITORE ELETTRICO MAKITA','CAGNOLA','GIANNI',2,'cantiere',None),
        ('MOV-009','2025-10-16','RABOT','CAGNOLA','GIANNI',2,'cantiere',None),
        ('MOV-010','2025-10-16','SCALE','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-011','2025-10-16','GABASSI QUADRATI','CAGNOLA','GIANNI',6,'cantiere',None),
        ('MOV-012','2025-10-16','BADILI','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-013','2025-10-16','SCOPE','CAGNOLA','GIANNI',1,'cantiere',None),
        ('MOV-014','2025-10-16','BETTONIERA GRANDE','CAGNOLA','GIANNI',1,'cantiere',None),
    ]
    for row in movimenti_data:
        cur.execute("""INSERT INTO movimenti (codice,data_uscita,attrezzo_nome,cantiere_nome,operatore_nome,qty,stato,note)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""", row)
    conn.commit()

_db_initialized = False

def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as ex:
            print("DB init warning:", ex)

@app.before_request
def before_request():
    ensure_db()

# ── Auth ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return dec

@app.route("/login", methods=["GET"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    ip = request.remote_addr
    ok, mins = check_rate(ip)
    if not ok:
        return jsonify({"ok": False, "error": f"Troppi tentativi. Riprova tra {mins} min."}), 429
    d = request.json or {}
    u = d.get("username", "").strip()
    p = d.get("password", "")
    if u == LOGIN_USERNAME and p == LOGIN_PASSWORD:
        _login_attempts.pop(ip, None)
        session.permanent = True
        session["logged_in"] = True
        return jsonify({"ok": True})
    else:
        record_fail(ip)
        return jsonify({"ok": False, "error": "Credenziali non valide."}), 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

# ── Helpers ───────────────────────────────────────────────────────────────────
def next_codice(cur, table, prefix):
    cur.execute(f"SELECT codice FROM {table} ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        return f"{prefix}-001"
    last = row["codice"]
    try:
        n = int(last.split("-")[-1]) + 1
    except:
        n = 1
    return f"{prefix}-{str(n).zfill(3)}"

# ── API Attrezzi ──────────────────────────────────────────────────────────────
@app.route("/api/attrezzi", methods=["GET"])
@login_required
def get_attrezzi():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM attrezzi ORDER BY codice")
            return jsonify([dict(r) for r in cur.fetchall()])

@app.route("/api/attrezzi", methods=["POST"])
@login_required
def add_attrezzo():
    d = request.json
    if not d.get("nome"):
        return jsonify({"error":"Nome obbligatorio"}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cod = next_codice(cur, "attrezzi", "ATT")
            cur.execute("""INSERT INTO attrezzi (codice,nome,categoria,marca,qty_tot,note,stato)
                VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (cod, d["nome"].upper(), d.get("categoria","Manuale"),
                 d.get("marca") or None, int(d.get("qty_tot",1)),
                 d.get("note") or None, d.get("stato","disp")))
            conn.commit()
            return jsonify(dict(cur.fetchone())), 201

@app.route("/api/attrezzi/<int:aid>", methods=["PUT"])
@login_required
def upd_attrezzo(aid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE attrezzi SET nome=%s,categoria=%s,marca=%s,qty_tot=%s,note=%s,stato=%s
                WHERE id=%s RETURNING *""",
                (d["nome"].upper(), d.get("categoria","Manuale"), d.get("marca") or None,
                 int(d.get("qty_tot",1)), d.get("note") or None, d.get("stato","disp"), aid))
            conn.commit()
            row = cur.fetchone()
            return jsonify(dict(row)) if row else ("", 404)

@app.route("/api/attrezzi/<int:aid>", methods=["DELETE"])
@login_required
def del_attrezzo(aid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM attrezzi WHERE id=%s", (aid,))
            conn.commit()
    return jsonify({"ok": True})

# ── API Cantieri ──────────────────────────────────────────────────────────────
@app.route("/api/cantieri", methods=["GET"])
@login_required
def get_cantieri():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM cantieri ORDER BY codice")
            return jsonify([dict(r) for r in cur.fetchall()])

@app.route("/api/cantieri", methods=["POST"])
@login_required
def add_cantiere():
    d = request.json
    if not d.get("nome"):
        return jsonify({"error":"Nome obbligatorio"}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cod = next_codice(cur, "cantieri", "C")
            cur.execute("""INSERT INTO cantieri (codice,nome,data_inizio,data_fine,stato)
                VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (cod, d["nome"].upper(), d.get("data_inizio") or None,
                 d.get("data_fine") or None, d.get("stato","attivo")))
            conn.commit()
            return jsonify(dict(cur.fetchone())), 201

@app.route("/api/cantieri/<int:cid>", methods=["PUT"])
@login_required
def upd_cantiere(cid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE cantieri SET nome=%s,data_inizio=%s,data_fine=%s,stato=%s
                WHERE id=%s RETURNING *""",
                (d["nome"].upper(), d.get("data_inizio") or None,
                 d.get("data_fine") or None, d.get("stato","attivo"), cid))
            conn.commit()
            row = cur.fetchone()
            return jsonify(dict(row)) if row else ("", 404)

@app.route("/api/cantieri/<int:cid>", methods=["DELETE"])
@login_required
def del_cantiere(cid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cantieri WHERE id=%s", (cid,))
            conn.commit()
    return jsonify({"ok": True})

# ── API Operatori ─────────────────────────────────────────────────────────────
@app.route("/api/operatori", methods=["GET"])
@login_required
def get_operatori():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM operatori ORDER BY codice")
            return jsonify([dict(r) for r in cur.fetchall()])

@app.route("/api/operatori", methods=["POST"])
@login_required
def add_operatore():
    d = request.json
    if not d.get("nome"):
        return jsonify({"error":"Nome obbligatorio"}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cod = next_codice(cur, "operatori", "OP")
            cur.execute("""INSERT INTO operatori (codice,nome,cognome,ruolo,telefono)
                VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (cod, d["nome"].upper(), (d.get("cognome") or "").upper() or None,
                 d.get("ruolo","Operaio Specializzato"), d.get("telefono") or None))
            conn.commit()
            return jsonify(dict(cur.fetchone())), 201

@app.route("/api/operatori/<int:oid>", methods=["PUT"])
@login_required
def upd_operatore(oid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE operatori SET nome=%s,cognome=%s,ruolo=%s,telefono=%s
                WHERE id=%s RETURNING *""",
                (d["nome"].upper(), (d.get("cognome") or "").upper() or None,
                 d.get("ruolo","Operaio Specializzato"), d.get("telefono") or None, oid))
            conn.commit()
            row = cur.fetchone()
            return jsonify(dict(row)) if row else ("", 404)

@app.route("/api/operatori/<int:oid>", methods=["DELETE"])
@login_required
def del_operatore(oid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM operatori WHERE id=%s", (oid,))
            conn.commit()
    return jsonify({"ok": True})

# ── API Movimenti ─────────────────────────────────────────────────────────────
@app.route("/api/movimenti", methods=["GET"])
@login_required
def get_movimenti():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT m.*,
                a.codice as att_cod, c.codice as cant_cod, o.codice as op_cod
                FROM movimenti m
                LEFT JOIN attrezzi a ON a.id=m.attrezzo_id
                LEFT JOIN cantieri c ON c.id=m.cantiere_id
                LEFT JOIN operatori o ON o.id=m.operatore_id
                ORDER BY m.id DESC""")
            rows = []
            for r in cur.fetchall():
                row = dict(r)
                for k,v in row.items():
                    if hasattr(v, 'isoformat'):
                        row[k] = v.isoformat()
                rows.append(row)
            return jsonify(rows)

@app.route("/api/movimenti", methods=["POST"])
@login_required
def add_movimento():
    d = request.json
    if not d.get("attrezzo_nome") or not d.get("cantiere_nome") or not d.get("operatore_nome"):
        return jsonify({"error":"Attrezzo, cantiere e operatore obbligatori"}), 400
    with get_db() as conn:
        with conn.cursor() as cur:
            cod = next_codice(cur, "movimenti", "MOV")
            # Risolvi ID
            cur.execute("SELECT id FROM attrezzi WHERE nome=%s LIMIT 1", (d["attrezzo_nome"],))
            a = cur.fetchone(); att_id = a["id"] if a else None
            cur.execute("SELECT id FROM cantieri WHERE nome ILIKE %s LIMIT 1", ('%'+d["cantiere_nome"]+'%',))
            c = cur.fetchone(); cant_id = c["id"] if c else None
            cur.execute("SELECT id FROM operatori WHERE nome=%s LIMIT 1", (d["operatore_nome"],))
            o = cur.fetchone(); op_id = o["id"] if o else None

            cur.execute("""INSERT INTO movimenti
                (codice,data_uscita,attrezzo_id,attrezzo_nome,cantiere_id,cantiere_nome,
                 operatore_id,operatore_nome,qty,data_rientro_prev,stato,note)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (cod, d["data_uscita"], att_id, d["attrezzo_nome"],
                 cant_id, d["cantiere_nome"], op_id, d["operatore_nome"],
                 int(d.get("qty",1)), d.get("data_rientro_prev") or None,
                 "cantiere", d.get("note") or None))
            # Aggiorna stato attrezzo
            if att_id:
                cur.execute("UPDATE attrezzi SET stato='cant' WHERE id=%s", (att_id,))
            conn.commit()
            row = dict(cur.fetchone())
            for k,v in row.items():
                if hasattr(v,'isoformat'): row[k]=v.isoformat()
            return jsonify(row), 201

@app.route("/api/movimenti/<int:mid>/rientro", methods=["POST"])
@login_required
def rientro_movimento(mid):
    d = request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM movimenti WHERE id=%s", (mid,))
            mov = cur.fetchone()
            if not mov:
                return jsonify({"error":"Non trovato"}), 404
            cur.execute("UPDATE movimenti SET data_rientro_eff=%s,stato='rientrato' WHERE id=%s",
                (d.get("data_rientro_eff"), mid))
            # Controlla se ci sono altri movimenti attivi per lo stesso attrezzo
            if mov["attrezzo_id"]:
                cur.execute("""SELECT COUNT(*) as n FROM movimenti
                    WHERE attrezzo_id=%s AND stato='cantiere' AND id!=%s""",
                    (mov["attrezzo_id"], mid))
                if cur.fetchone()["n"] == 0:
                    cur.execute("UPDATE attrezzi SET stato='disp' WHERE id=%s", (mov["attrezzo_id"],))
            conn.commit()
            cur.execute("SELECT * FROM movimenti WHERE id=%s", (mid,))
            row = dict(cur.fetchone())
            for k,v in row.items():
                if hasattr(v,'isoformat'): row[k]=v.isoformat()
            return jsonify(row)

@app.route("/api/movimenti/<int:mid>", methods=["DELETE"])
@login_required
def del_movimento(mid):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM movimenti WHERE id=%s", (mid,))
            conn.commit()
    return jsonify({"ok": True})

# ── API Stats ─────────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
@login_required
def get_stats():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as n FROM attrezzi")
            tot = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) as n FROM attrezzi WHERE stato='cant'")
            in_cant = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) as n FROM attrezzi WHERE stato='disp'")
            in_mag = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) as n FROM movimenti WHERE stato='cantiere'")
            mov_att = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) as n FROM cantieri WHERE stato='attivo'")
            cant_att = cur.fetchone()["n"]
            # Categorie
            cur.execute("SELECT categoria, COUNT(*) as n FROM attrezzi GROUP BY categoria ORDER BY n DESC")
            cats = [dict(r) for r in cur.fetchall()]
            # Movimenti per cantiere
            cur.execute("""SELECT cantiere_nome, SUM(qty) as tot FROM movimenti
                WHERE stato='cantiere' GROUP BY cantiere_nome ORDER BY tot DESC""")
            cant_mov = [dict(r) for r in cur.fetchall()]
            return jsonify({
                "tot":tot, "in_cant":in_cant, "in_mag":in_mag,
                "mov_att":mov_att, "cant_att":cant_att,
                "cats":cats, "cant_mov":cant_mov
            })

if __name__ == "__main__":
    app.run(debug=False)
