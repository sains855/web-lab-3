import os
import re
import pickle
import base64
import pymysql
import pymysql.cursors
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, g, make_response, jsonify
)
from dotenv import load_dotenv

# ─── Load .env (lokal). Di Railway, env var sudah di-inject otomatis. ────────
load_dotenv()

app = Flask(__name__)

# [VULN-1] Secret key diambil dari .env / Railway env var
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret_key")


# ─── DB Config ───────────────────────────────────────────────────────────────
# Railway menyediakan MYSQL_URL (format: mysql://user:pass@host:port/db)
# Kalau tidak ada, fallback ke variabel individual dari .env

def _parse_db_config():
    # Coba MYSQL_URL dulu (Railway reference format)
    url = os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL", "")
    if url and (url.startswith("mysql://") or url.startswith("mysql+pymysql://")):
        m = re.match(
            r"mysql(?:\+pymysql)?://([^:]+):([^@]*)@([^:/]+):?(\d*)/(.+)", url
        )
        if m:
            cfg = {
                "host":     m.group(3),
                "port":     int(m.group(4)) if m.group(4) else 3306,
                "user":     m.group(1),
                "password": m.group(2),
                "db":       m.group(5).split("?")[0],
                "charset":  "utf8mb4",
                "cursorclass": pymysql.cursors.DictCursor,
                "autocommit": False,
            }
            print(f"[db] Konek via MYSQL_URL ke host: {cfg['host']}")
            return cfg

    # Fallback: baca variabel individual (Railway inject MYSQL_HOST dll, atau dari .env lokal)
    host = os.environ.get("MYSQL_HOST") or os.environ.get("MYSQLHOST", "localhost")
    port = int(os.environ.get("MYSQL_PORT") or os.environ.get("MYSQLPORT", 3306))
    user = os.environ.get("MYSQL_USER") or os.environ.get("MYSQLUSER", "root")
    password = os.environ.get("MYSQL_PASSWORD") or os.environ.get("MYSQLPASSWORD", "")
    db = os.environ.get("MYSQL_DB") or os.environ.get("MYSQLDATABASE", "edutask")

    print(f"[db] Konek via variabel individual ke host: {host}")
    return {
        "host":     host,
        "port":     port,
        "user":     user,
        "password": password,
        "db":       db,
        "charset":  "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }

DB_CONFIG = _parse_db_config()


# ─── DB Helpers ──────────────────────────────────────────────────────────────

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = pymysql.connect(**DB_CONFIG)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Buat tabel jika belum ada, lalu seed data awal.
    Di Railway, database sudah dibuat otomatis.
    Di lokal, coba buat database terlebih dahulu.
    """
    if not os.environ.get("RAILWAY_ENVIRONMENT"):
        try:
            cfg = {k: v for k, v in DB_CONFIG.items() if k not in ("db", "cursorclass", "autocommit")}
            cfg["cursorclass"] = pymysql.cursors.DictCursor
            conn_tmp = pymysql.connect(**cfg)
            with conn_tmp.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['db']}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn_tmp.commit()
            conn_tmp.close()
        except Exception as e:
            print(f"[init_db] Lewati CREATE DATABASE: {e}")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id        INT AUTO_INCREMENT PRIMARY KEY,
                    username  VARCHAR(100) UNIQUE NOT NULL,
                    password  VARCHAR(255) NOT NULL,
                    role      VARCHAR(20) DEFAULT 'student',
                    bio       TEXT DEFAULT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    title       VARCHAR(255) NOT NULL,
                    description TEXT,
                    subject     VARCHAR(100),
                    due_date    VARCHAR(20),
                    priority    VARCHAR(20) DEFAULT 'medium',
                    status      VARCHAR(20) DEFAULT 'pending',
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id         INT AUTO_INCREMENT PRIMARY KEY,
                    user_id    INT NOT NULL,
                    title      VARCHAR(255) NOT NULL,
                    content    TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Seed default users
            cur.execute("""
                INSERT IGNORE INTO users (username, password, role)
                VALUES ('admin', 'admin123', 'admin'),
                       ('student1', 'password1', 'student');
            """)
        conn.commit()
        print("[init_db] Database MySQL berhasil diinisialisasi.")
    finally:
        conn.close()


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # [VULN-2] SQL Injection – raw string interpolation (sengaja dibiarkan untuk CTF)
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        db = get_db()
        with db.cursor() as cur:
            cur.execute(query)
            user = cur.fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            error = "Username atau password salah."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Semua field wajib diisi."
        else:
            db = get_db()
            try:
                with db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, password),
                    )
                db.commit()
                return redirect(url_for("login"))
            except pymysql.err.IntegrityError:
                error = "Username sudah digunakan."

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─── Dashboard ───────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM tasks WHERE user_id=%s ORDER BY created_at DESC LIMIT 5",
            (session["user_id"],),
        )
        tasks = cur.fetchall()

        cur.execute(
            "SELECT * FROM notes WHERE user_id=%s ORDER BY created_at DESC LIMIT 3",
            (session["user_id"],),
        )
        notes = cur.fetchall()

        cur.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE user_id=%s", (session["user_id"],)
        )
        total_tasks = cur.fetchone()["c"]

        cur.execute(
            "SELECT COUNT(*) as c FROM tasks WHERE user_id=%s AND status='done'",
            (session["user_id"],),
        )
        done_tasks = cur.fetchone()["c"]

    return render_template(
        "dashboard.html",
        tasks=tasks,
        notes=notes,
        total_tasks=total_tasks,
        done_tasks=done_tasks,
    )


# ─── Tasks ───────────────────────────────────────────────────────────────────

@app.route("/tasks")
def tasks():
    if "user_id" not in session:
        return redirect(url_for("login"))

    status_filter = request.args.get("status", "all")
    db = get_db()
    with db.cursor() as cur:
        if status_filter == "all":
            cur.execute(
                "SELECT * FROM tasks WHERE user_id=%s ORDER BY due_date ASC",
                (session["user_id"],),
            )
        else:
            cur.execute(
                "SELECT * FROM tasks WHERE user_id=%s AND status=%s ORDER BY due_date ASC",
                (session["user_id"], status_filter),
            )
        rows = cur.fetchall()

    return render_template("tasks.html", tasks=rows, status_filter=status_filter)


@app.route("/tasks/add", methods=["GET", "POST"])
def add_task():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title       = request.form.get("title", "")
        description = request.form.get("description", "")
        subject     = request.form.get("subject", "")
        due_date    = request.form.get("due_date", "")
        priority    = request.form.get("priority", "medium")

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (user_id,title,description,subject,due_date,priority) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (session["user_id"], title, description, subject, due_date, priority),
            )
        db.commit()
        return redirect(url_for("tasks"))

    return render_template("add_task.html")


@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        # [VULN-3] IDOR – no ownership check (sengaja untuk CTF)
        cur.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
        task = cur.fetchone()

    if not task:
        return "Tugas tidak ditemukan.", 404

    if request.method == "POST":
        title       = request.form.get("title", "")
        description = request.form.get("description", "")
        subject     = request.form.get("subject", "")
        due_date    = request.form.get("due_date", "")
        priority    = request.form.get("priority", "medium")
        status      = request.form.get("status", "pending")

        with db.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET title=%s,description=%s,subject=%s,"
                "due_date=%s,priority=%s,status=%s WHERE id=%s",
                (title, description, subject, due_date, priority, status, task_id),
            )
        db.commit()
        return redirect(url_for("tasks"))

    return render_template("edit_task.html", task=task)


@app.route("/tasks/delete/<int:task_id>")
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        # [VULN-3 continued] IDOR
        cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    db.commit()
    return redirect(url_for("tasks"))


@app.route("/tasks/status/<int:task_id>", methods=["POST"])
def update_status(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    new_status = request.form.get("status", "pending")
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE tasks SET status=%s WHERE id=%s", (new_status, task_id))
    db.commit()
    return jsonify({"ok": True})


# ─── Notes ───────────────────────────────────────────────────────────────────

@app.route("/notes")
def notes():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM notes WHERE user_id=%s ORDER BY created_at DESC",
            (session["user_id"],),
        )
        rows = cur.fetchall()

    return render_template("notes.html", notes=rows)


@app.route("/notes/add", methods=["GET", "POST"])
def add_note():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title   = request.form.get("title", "")
        content = request.form.get("content", "")
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO notes (user_id, title, content) VALUES (%s,%s,%s)",
                (session["user_id"], title, content),
            )
        db.commit()
        return redirect(url_for("notes"))

    return render_template("add_note.html")


@app.route("/notes/view/<int:note_id>")
def view_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        # [VULN-3 continued] IDOR on notes
        cur.execute("SELECT * FROM notes WHERE id=%s", (note_id,))
        note = cur.fetchone()

    if not note:
        return "Catatan tidak ditemukan.", 404
    return render_template("view_note.html", note=note)


@app.route("/notes/delete/<int:note_id>")
def delete_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id=%s", (note_id,))
    db.commit()
    return redirect(url_for("notes"))


# ─── Profile ─────────────────────────────────────────────────────────────────

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
        user = cur.fetchone()

    success = None
    if request.method == "POST":
        # [VULN-4] Stored XSS – bio disimpan mentah (sengaja untuk CTF)
        bio = request.form.get("bio", "")
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET bio=%s WHERE id=%s", (bio, session["user_id"])
            )
        db.commit()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
            user = cur.fetchone()
        success = "Profil berhasil diperbarui."

    return render_template("profile.html", user=user, success=success)


# ─── Search ──────────────────────────────────────────────────────────────────

@app.route("/search")
def search():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # [VULN-4 continued] Reflected XSS – query di-echo via |safe di template
    query = request.args.get("q", "")
    db = get_db()

    # [VULN-2 continued] SQL Injection in search (sengaja untuk CTF)
    sql = f"SELECT * FROM tasks WHERE user_id={session['user_id']} AND title LIKE '%{query}%'"
    with db.cursor() as cur:
        cur.execute(sql)
        results = cur.fetchall()

    return render_template("search.html", query=query, results=results)


# ─── Admin ───────────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    # [VULN-5] Broken Access Control (sengaja untuk CTF)
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id,username,role,bio FROM users")
        users = cur.fetchall()

        cur.execute(
            "SELECT t.*,u.username FROM tasks t "
            "JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC"
        )
        all_tasks = cur.fetchall()

    return render_template("admin.html", users=users, all_tasks=all_tasks)


@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    # [VULN-5 continued] No role check
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    return redirect(url_for("admin"))


# ─── Preferences (Insecure Deserialization) ──────────────────────────────────

@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prefs = {"theme": "light", "lang": "id", "notif": True}
    error = None

    if request.method == "POST":
        # [VULN-6] Insecure Deserialization via pickle (sengaja untuk CTF)
        raw = request.cookies.get("prefs")
        if raw:
            try:
                prefs = pickle.loads(base64.b64decode(raw))
            except Exception:
                pass

        prefs["theme"] = request.form.get("theme", "light")
        prefs["lang"]  = request.form.get("lang", "id")
        prefs["notif"] = request.form.get("notif") == "on"

        encoded = base64.b64encode(pickle.dumps(prefs)).decode()
        resp = make_response(redirect(url_for("preferences")))
        resp.set_cookie("prefs", encoded)
        return resp

    raw = request.cookies.get("prefs")
    if raw:
        try:
            prefs = pickle.loads(base64.b64decode(raw))
        except Exception:
            pass

    return render_template("preferences.html", prefs=prefs, error=error)


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.route("/api/tasks")
def api_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tasks WHERE user_id=%s", (session["user_id"],))
        rows = cur.fetchall()
    return jsonify(rows)


@app.route("/api/users")
def api_users():
    # [VULN-5 continued] No auth check (sengaja untuk CTF)
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id,username,role FROM users")
        rows = cur.fetchall()
    return jsonify(rows)


# ─── Health Check (Railway ping) ─────────────────────────────────────────────

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


# ─── Init DB (dipanggil saat startup, kompatibel dengan gunicorn) ─────────────

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"[startup] init_db gagal: {e}")


# ─── Entry Point (lokal) ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "True") == "True",
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("FLASK_PORT", 5000)),
    )
