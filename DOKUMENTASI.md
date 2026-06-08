# EduTask – Dokumentasi Aplikasi

> Platform manajemen tugas dan catatan belajar berbasis web untuk pelajar dan mahasiswa.

---

## Daftar Isi

1. [Gambaran Umum](#gambaran-umum)
2. [Fitur Utama](#fitur-utama)
3. [Arsitektur & Teknologi](#arsitektur--teknologi)
4. [Struktur Proyek](#struktur-proyek)
5. [Instalasi & Menjalankan](#instalasi--menjalankan)
6. [Panduan Penggunaan](#panduan-penggunaan)
7. [Akun Default](#akun-default)
8. [Referensi API Endpoint](#referensi-api-endpoint)
9. [Skema Database](#skema-database)

---

## Gambaran Umum

EduTask adalah aplikasi web manajemen tugas belajar yang dibangun menggunakan framework Flask (Python). Aplikasi ini memungkinkan pengguna untuk:

- Mencatat dan melacak tugas berdasarkan mata pelajaran dan prioritas
- Membuat dan menyimpan catatan pelajaran
- Memantau progres belajar melalui dashboard ringkas
- Menyesuaikan preferensi tampilan aplikasi

---

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Autentikasi** | Registrasi dan login dengan username & password |
| **Dashboard** | Ringkasan statistik tugas dan catatan terbaru |
| **Manajemen Tugas** | CRUD tugas dengan field: judul, mata pelajaran, deskripsi, deadline, prioritas, status |
| **Catatan Digital** | CRUD catatan bebas dengan judul dan isi teks |
| **Pencarian** | Pencarian tugas berdasarkan judul |
| **Profil** | Edit bio profil pengguna |
| **Preferensi** | Pengaturan tema, bahasa, dan notifikasi |
| **Panel Admin** | Kelola seluruh pengguna dan tugas (khusus admin) |

---

## Arsitektur & Teknologi

```
┌─────────────────────────────────────────────────┐
│                  Browser (Client)                │
│          HTML + CSS (Inter font) + JS            │
└───────────────────┬─────────────────────────────┘
                    │ HTTP
┌───────────────────▼─────────────────────────────┐
│            Flask Application Server              │
│         app.py  ·  Jinja2 Templates              │
└───────────────────┬─────────────────────────────┘
                    │ sqlite3
┌───────────────────▼─────────────────────────────┐
│             SQLite Database                      │
│         instance/edutask.db                     │
└─────────────────────────────────────────────────┘
```

**Stack:**

- **Backend:** Python 3.10+, Flask 2.3+
- **Database:** SQLite (via modul `sqlite3` bawaan Python)
- **Templating:** Jinja2 (bawaan Flask)
- **Frontend:** HTML5, CSS3 (custom), JavaScript vanilla
- **Font:** Inter (Google Fonts)

---

## Struktur Proyek

```
edutask/
├── app.py                  # Aplikasi utama Flask
├── requirements.txt        # Dependensi Python
├── instance/
│   └── edutask.db          # File database SQLite (dibuat saat run pertama)
├── static/
│   ├── css/
│   │   └── style.css       # Stylesheet utama
│   └── js/
│       └── app.js          # Script JavaScript
└── templates/
    ├── base.html           # Template dasar (navbar, layout)
    ├── index.html          # Halaman landing
    ├── login.html          # Halaman login
    ├── register.html       # Halaman registrasi
    ├── dashboard.html      # Dashboard utama
    ├── tasks.html          # Daftar tugas
    ├── add_task.html       # Form tambah tugas
    ├── edit_task.html      # Form edit tugas
    ├── notes.html          # Daftar catatan
    ├── add_note.html       # Form tambah catatan
    ├── view_note.html      # Tampilan catatan
    ├── search.html         # Halaman pencarian
    ├── profile.html        # Halaman profil
    ├── preferences.html    # Halaman preferensi
    └── admin.html          # Panel admin
```

---

## Instalasi & Menjalankan

### Prasyarat

- Python 3.10 atau lebih baru
- pip (Python package manager)

### Langkah Instalasi

```bash
# 1. Ekstrak dan masuk ke folder proyek
cd edutask

# 2. (Opsional) Buat virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependensi
pip install -r requirements.txt

# 4. Jalankan aplikasi
python app.py
```

### Mengakses Aplikasi

Buka browser dan akses:

```
http://localhost:5000
```

Database SQLite akan dibuat otomatis di `instance/edutask.db` saat pertama kali dijalankan.

---

## Panduan Penggunaan

### 1. Registrasi & Login

- Kunjungi halaman utama, klik **Mulai Gratis** untuk mendaftar
- Isi username dan password, lalu klik **Daftar**
- Login dengan kredensial yang telah dibuat

### 2. Dashboard

Setelah login, dashboard menampilkan:
- Statistik total tugas, tugas selesai, dan belum selesai
- 5 tugas terbaru
- 3 catatan terbaru

### 3. Mengelola Tugas

- Klik **Tugas** di navbar untuk melihat semua tugas
- Klik **+ Tambah Tugas** untuk membuat tugas baru
- Isi form: judul (wajib), mata pelajaran, deskripsi, deadline, prioritas
- Gunakan filter di atas tabel untuk menyaring berdasarkan status
- Ubah status tugas langsung dari dropdown di tabel
- Klik ikon pensil untuk edit, ikon tempat sampah untuk hapus

### 4. Membuat Catatan

- Klik **Catatan** di navbar
- Klik **+ Catatan Baru**, isi judul dan konten
- Klik catatan untuk membaca isi lengkapnya

### 5. Pencarian

- Klik ikon kaca pembesar di navbar
- Ketik judul tugas yang ingin dicari, klik **Cari**

### 6. Profil & Preferensi

- Klik avatar di pojok kanan navbar untuk ke halaman profil
- Edit bio profil dan simpan
- Klik ikon gear untuk mengatur tema dan bahasa

---

## Akun Default

Aplikasi menyertakan dua akun bawaan yang dibuat saat inisialisasi database:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `student1` | `password1` | student |

> Disarankan untuk mengubah password default setelah instalasi di lingkungan produksi.

---

## Referensi API Endpoint

| Method | URL | Deskripsi | Auth |
|---|---|---|---|
| GET | `/` | Halaman landing | Tidak |
| GET/POST | `/login` | Login | Tidak |
| GET/POST | `/register` | Registrasi | Tidak |
| GET | `/logout` | Logout | Ya |
| GET | `/dashboard` | Dashboard utama | Ya |
| GET | `/tasks` | Daftar tugas | Ya |
| GET/POST | `/tasks/add` | Tambah tugas | Ya |
| GET/POST | `/tasks/edit/<id>` | Edit tugas | Ya |
| GET | `/tasks/delete/<id>` | Hapus tugas | Ya |
| POST | `/tasks/status/<id>` | Update status tugas | Ya |
| GET | `/notes` | Daftar catatan | Ya |
| GET/POST | `/notes/add` | Tambah catatan | Ya |
| GET | `/notes/view/<id>` | Lihat catatan | Ya |
| GET | `/notes/delete/<id>` | Hapus catatan | Ya |
| GET | `/search?q=` | Cari tugas | Ya |
| GET/POST | `/profile` | Halaman profil | Ya |
| GET/POST | `/preferences` | Preferensi | Ya |
| GET | `/admin` | Panel admin | Ya* |
| GET | `/admin/delete_user/<id>` | Hapus user | Ya* |
| GET | `/api/tasks` | API: daftar tugas JSON | Ya |
| GET | `/api/users` | API: daftar user JSON | Tidak |

*) Seharusnya hanya bisa diakses oleh role `admin`.

---

## Skema Database

### Tabel `users`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | ID unik pengguna |
| `username` | TEXT UNIQUE | Nama pengguna |
| `password` | TEXT | Password |
| `role` | TEXT | Role: `admin` atau `student` |
| `bio` | TEXT | Bio profil |

### Tabel `tasks`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | ID unik tugas |
| `user_id` | INTEGER FK | Pemilik tugas |
| `title` | TEXT | Judul tugas |
| `description` | TEXT | Deskripsi |
| `subject` | TEXT | Mata pelajaran |
| `due_date` | TEXT | Tanggal deadline |
| `priority` | TEXT | `low`, `medium`, `high` |
| `status` | TEXT | `pending`, `in_progress`, `done` |
| `created_at` | DATETIME | Waktu dibuat |

### Tabel `notes`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INTEGER PK | ID unik catatan |
| `user_id` | INTEGER FK | Pemilik catatan |
| `title` | TEXT | Judul catatan |
| `content` | TEXT | Isi catatan |
| `created_at` | DATETIME | Waktu dibuat |

---

*Dokumentasi ini dibuat untuk keperluan pengembangan dan pengujian aplikasi EduTask.*
