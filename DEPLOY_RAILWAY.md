# 🚂 Panduan Deploy ke Railway (Gratis)

## Prasyarat
- Akun Railway: https://railway.app (daftar gratis via GitHub)
- Akun GitHub (untuk push kode)

---

## Langkah 1 — Push ke GitHub

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/edutask.git
git push -u origin main
```

> ⚠️ Pastikan `.env` sudah ada di `.gitignore` agar tidak ikut ter-push!

---

## Langkah 2 — Buat Project di Railway

1. Buka https://railway.app → **New Project**
2. Pilih **Deploy from GitHub repo**
3. Pilih repo `edutask` yang baru dibuat
4. Railway otomatis mendeteksi Flask dari `Procfile`

---

## Langkah 3 — Tambah Plugin MySQL

1. Di dashboard project Railway, klik **+ New**
2. Pilih **Database → MySQL**
3. Railway otomatis membuat MySQL dan menyuntikkan variabel:
   - `MYSQL_URL` ← yang dipakai app ini
   - `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`

---

## Langkah 4 — Set Environment Variables

Di Railway → project → **Variables**, tambahkan:

| Key | Value |
|-----|-------|
| `FLASK_SECRET_KEY` | buat random string panjang, contoh: `openssl rand -hex 32` |
| `FLASK_DEBUG` | `False` |

> Variabel MySQL (`MYSQL_URL`, dll.) sudah otomatis dari plugin — tidak perlu diisi manual.

---

## Langkah 5 — Deploy

Railway akan otomatis build & deploy setiap kali ada push ke `main`.

Pantau log di **Deployments → View Logs**.

Setelah sukses, Railway memberikan URL publik seperti:
```
https://edutask-production-xxxx.up.railway.app
```

---

## Troubleshooting

| Problem | Solusi |
|---------|--------|
| `Access denied for user` | Pastikan plugin MySQL sudah terhubung ke service Flask |
| `Application failed to respond` | Cek log, pastikan `Procfile` ada dan benar |
| Tabel belum terbuat | `init_db()` jalan otomatis saat startup; lihat log |

---

## Lokal Development

```bash
# Install dependencies
pip install -r requirements.txt

# Isi .env sesuai MySQL lokal kamu
cp .env.example .env
# edit .env ...

# Jalankan
python app.py
```
