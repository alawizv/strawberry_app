# 🍓 Strawberry Fresh Supply

Aplikasi internal manajemen rantai pasok & penjualan strawberry:  
**Kebun → Pickup (SJ) → Penerimaan & Sortir → Stok → Produk → Order → Pengiriman → Keuangan**, plus dashboard owner, approval, dan audit log.

## Menjalankan

```bash
cd strawberry_app
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501`

### Akun demo

| Username | Password  | Role   |
|----------|-----------|--------|
| owner    | owner123  | Owner  |
| driver1  | driver123 | Driver |
| sorter1  | sorter123 | Sorter |
| sales1   | sales123  | Sales  |

## Fitur (aturan saat ini)

### Dashboard (Owner interaktif)
- Filter tanggal & kebun, KPI stok/omzet/tray/kg diterima
- Grafik omzet harian, status order, stok, yield %
- Antrean: produk pending, adjustment pending, koreksi pickup
- Snapshot keuangan & top produk

### Pengambilan
- Form 2 kebun (RH1 / RH2), tray per kebun, TOTAL tray, auto **1–2 SJ**
- SJ = `DDMMYYYY` + `RH1`/`RH2`
- **1 kebun / 1 hari** (field terkunci jika sudah ada)
- Driver tidak edit data; **permintaan koreksi → owner**

### Penerimaan & Sortir
- List **hanya SJ belum diterima**
- **1 SJ = 1 penerimaan** (anti double submit + konfirmasi)
- Dicek oleh = akun login (read-only)
- Balance ± toleransi (default 0.15 kg) — atur di Master Data
- Sorter wajib balance; **owner boleh override** (log)
- Owner hapus riwayat = rollback stok

### Stok
- Real-time + mutasi
- Adjustment: **hanya Sorter ajukan → Owner approve**

### Produk
- Kartu + gambar, harga `Rp. 37.000`
- Sales ajukan (pending); owner buat langsung aktif / approve

### Penjualan
- Cari pelanggan / New Customer
- Multi-item (produk & qty beda)
- Diskon **nominal saja** (tanpa %)
- Total live; confirmed potong stok sesuai resep

### Lainnya
- Keuangan, Master Data, Laporan
- **Log Aktivitas** (ringkasan + detail teknis)
- **Panduan & FAQ** di menu aplikasi (selaras aturan ini)

## Struktur

```
strawberry_app/
├── app.py                 # Login + Dashboard (entry: streamlit run app.py)
├── Dashboard.py           # Salinan entry yang sama (opsional: streamlit run Dashboard.py)
├── database.py            # Models, seed, helper harga/SJ/log
├── auth_utils.py          # Auth, flash sukses, role
├── pages/
│   ├── 1_…_Pengambilan.py
│   ├── 2_…_Penerimaan_Sortir.py
│   ├── 3_…_Stok.py
│   ├── 4_…_Produk.py
│   ├── 5_…_Penjualan.py
│   ├── 6_…_Keuangan.py
│   ├── 7_…_Master_Data.py
│   ├── 8_…_Laporan.py
│   ├── 9_…_Log_Aktivitas.py
│   └── 10_…_Panduan_FAQ.py
├── data/strawberry.db
├── uploads/
└── requirements.txt
```

## Tech
- Streamlit multipage · SQLAlchemy · SQLite (`data/strawberry.db`) · bcrypt · Pandas  
- Siap migrasi PostgreSQL / PostgREST nanti

## Catatan
- Desimal kg: pakai **titik** (`12.5`)
- Restart Streamlit setelah update kode
- Panduan lengkap & FAQ: menu **📖 Panduan & FAQ** di app
