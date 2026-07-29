"""Panduan operasional + FAQ — dokumentasi lengkap semua fitur."""
import streamlit as st
from auth_utils import require_login, show_user_sidebar

st.set_page_config(page_title="Panduan & FAQ", page_icon="📖", layout="wide")
user = require_login(["owner", "admin", "driver", "sorter", "sales"])
show_user_sidebar()

st.markdown("## 📖 Panduan & FAQ")
st.caption("Dokumentasi operasional lengkap — semua fitur terbaru")

tab_guide, tab_roles, tab_flow, tab_faq = st.tabs([
    "Panduan Modul", "Hak Akses Role", "Alur Kerja", "FAQ",
])

with tab_guide:
    st.subheader("1. Login & Dashboard")
    st.markdown("""
- Login di halaman **Dashboard**. Session user disimpan di browser session Streamlit.
- **Dashboard berbeda per role:**
  - **Owner/Admin**: KPI lengkap, filter tanggal & kebun, charts omzet/stok/yield, antrean approve, snapshot keuangan, breakdown sortir %, retur pending.
  - **Driver**: pickup hari ini, ringkasan pickup, quick link ke Pengambilan.
  - **Sorter**: antrean SJ pending, penerimaan hari ini, level stok, quick link ke Penerimaan.
  - **Sales**: omzet hari ini/bulan, top produk, stok tersedia, order terbaru, quick link ke Penjualan.
- **Tema Light / Dark** di sidebar. Preferensi per sesi browser.
- Setelah aksi sukses: **toast + banner hijau + balloons**.
    """)

    st.subheader("2. Pengambilan (Driver / Owner)")
    st.markdown("""
- Multi-kebun sekarang **dinamis** dari Master Data → Kebun (bukan hardcode 2).
- Form: **Tanggal** + tray per kebun + TOTAL tray.
- 1 submit bisa membuat **beberapa SJ** sekaligus (satu per kebun dengan tray > 0).
- Format No. SJ: `DDMMYYYY` + kode kebun (dari Master Data, misal `RH1` / `RH2`).
- **Aturan 1 kebun / 1 hari**: jika kebun sudah ada pickup aktif, field tray **dikunci**.
- **QR Code otomatis** setelah simpan:
  - Download QR (PNG) per SJ.
  - **Cetak SJ** (download HTML yang bisa diprint — ada QR, info kebun, tray, driver).
  - QR berisi: nomor SJ, kode kebun, tanggal.
- Driver **tidak bisa edit** → koreksi via **Permintaan Koreksi** → Owner approve.
    """)

    st.subheader("3. Penerimaan & Sortir (Sorter / Owner)")
    st.markdown("""
- **Scan QR** atau **ketik No. SJ** untuk cari Surat Jalan.
- Sistem menampilkan info SJ (kebun, tray, driver, foto pickup).
- Input total kg timbang + **upload foto timbangan** (opsional).
- Sortir per kategori → cek balance (selisih ≤ toleransi).
- **Owner** boleh override tidak balance.
- Simpan wajib **konfirmasi** → stok masuk otomatis (in_sorting).
- Owner dapat **hapus riwayat** → rollback stok + pickup kembali pending.
    """)

    st.subheader("4. Stok")
    st.markdown("""
- Stok real-time per kategori + riwayat mutasi (filter tipe / arah).
- **Export CSV/Excel** riwayat mutasi.
- **Tren yield %** — line chart per kategori dari waktu ke waktu.
- **Tipe mutasi:** `in_sorting` (+), `out_sale` (−), `adjustment` (±), `in_return` (+).
- **Adjustment**: Sorter ajukan → Owner approve. Owner bisa langsung terapkan.
- Stok dicek agar tidak negatif saat adjustment.
    """)

    st.subheader("5. Produk")
    st.markdown("""
- Tampilan kartu (2 kolom) + gambar opsional.
- **Sales** buat → status **pending** → Owner approve.
- **Owner** buat → langsung **approved & aktif**.
- Harga: tampil `Rp. 37.000`, input ketik `37000`.
- Edit produk (harga, gambar, status aktif) di kartu produk.
    """)

    st.subheader("6. Penjualan")
    st.markdown("""
- Cari pelanggan → ketik nama → pilih atau buat baru (**cek duplikat**).
- **Diskon otomatis** dari data pelanggan (`default_discount_pct`). Bisa diubah manual.
- **Multi-item**: tambah baris, beda produk/qty/harga per baris.
- Total **live** (update saat widget berubah).
- Status `confirmed` → potong **stok bahan per kategori** sesuai **resep produk**.
- **Edit order** (draft/confirmed): ubah tanggal, ongkir, diskon, catatan. Semua tercatat di log.
- **Invoice PDF**: download nota penjualan per order (format A5, ada detail item & total).
- Metode kirim: GO SEND, Paxel, Kurir Sendiri, Mobil Box Sewa.
    """)

    st.subheader("7. Retur / Pengembalian (BARU)")
    st.markdown("""
- Sales/Owner bisa **ajukan retur** untuk order yang sudah confirmed/shipped/delivered.
- Pilih order → isi qty per kategori → alasan retur.
- **Owner** approve → stok dikembalikan otomatis (`in_return`).
- **Sales** mengajukan → menunggu approve owner.
- Partial return: bisa per kategori, tidak harus full order.
    """)

    st.subheader("8. Keuangan")
    st.markdown("""
- Omzet penjualan vs pengeluaran operasional.
- **Filter tanggal** untuk semua data.
- **Export CSV/Excel** pemasukan dan pengeluaran.
- Semua pengeluaran tercatat di **Log Aktivitas**.
- Owner bisa **hapus pengeluaran** (tercatat di log).
- Kategori pengeluaran: shipping, labor, packaging, fuel, farm, other.
    """)

    st.subheader("9. Master Data")
    st.markdown("""
- **Full CRUD** sekarang (tambah, edit, nonaktifkan):
  - **Kategori** — edit nama, deskripsi, warna, urutan.
  - **Kebun (BARU)** — dinamis! Tambah/edit/nonaktifkan kebun. Kode kebun untuk SJ.
  - **User** — edit nama, role, telepon, status aktif, reset password.
  - **Pelanggan** — edit semua field termasuk diskon default %.
- **Hak Akses (BARU)** — atur permission per role per modul (view/create/edit/delete/approve).
- **Pengaturan** — nama perusahaan, toleransi balance.
- **Backup Database** — download file .db (SQLite).
    """)

    st.subheader("10. Barcode & QR (BARU)")
    st.markdown("""
- **Driver**: setelah simpan pickup, QR code otomatis di-generate.
  - Download QR (file PNG).
  - Cetak SJ (HTML) — ada QR + info lengkap.
- **Sorter**: scan QR di halaman Penerimaan (atau ketik manual).
  - Sistem otomatis menemukan SJ dan menampilkan info.
- QR berisi: `SJ:nomor|FARM:kode|DATE:tanggal`.
- Bisa discan dengan HP biasa (camera app) atau input manual.
    """)

    st.subheader("11. Profil (BARU)")
    st.markdown("""
- Semua user bisa **ganti password sendiri** di halaman Profil.
- Akses dari sidebar → tombol **Profil**.
- Password lama wajib diverifikasi sebelum ganti.
    """)

    st.subheader("12. Laporan")
    st.markdown("""
- Filter periode, stok, yield %, performa driver/sales, top produk.
- **Tren yield %** — line chart per kategori.
- **Top pelanggan** — ranking berdasarkan omzet.
- **Perbandingan kebun** — tray, kg, efisiensi kg/tray.
- **Export CSV/Excel** data penjualan.
    """)

    st.subheader("13. Log Aktivitas")
    st.markdown("""
- **Audit trail** permanen — semua proses tercatat.
- **Audit Diff (BARU)** — sekarang menampilkan perubahan **before/after** yang readable.
  - Field yang berubah ditandai 🔴 merah.
  - Diff format: `field: 'lama' → 'baru'`.
- Filter: action, user, tanggal.
- **Export CSV/Excel** log.
- Log **tidak bisa dihapus** (audit multi-owner).
    """)

with tab_roles:
    st.subheader("Matriks role default")
    st.dataframe([
        {"Modul": "Dashboard", "Owner": "Penuh + filter + approve", "Driver": "Ringkas", "Sorter": "Ringkas", "Sales": "Ringkas"},
        {"Modul": "Pengambilan", "Owner": "Ya + edit + approve koreksi", "Driver": "Buat + QR + cetak SJ", "Sorter": "—", "Sales": "—"},
        {"Modul": "Penerimaan", "Owner": "Ya + override + hapus", "Driver": "—", "Sorter": "Scan QR + timbang + foto", "Sales": "—"},
        {"Modul": "Stok", "Owner": "Ya + adjustment langsung", "Driver": "Lihat", "Sorter": "Lihat + ajukan adj", "Sales": "Lihat"},
        {"Modul": "Produk", "Owner": "CRUD + approve", "Driver": "—", "Sorter": "—", "Sales": "Ajukan"},
        {"Modul": "Penjualan", "Owner": "Ya + edit order", "Driver": "—", "Sorter": "—", "Sales": "Ya"},
        {"Modul": "Retur", "Owner": "Ya + approve", "Driver": "—", "Sorter": "—", "Sales": "Ajukan retur"},
        {"Modul": "Keuangan", "Owner": "Ya + export", "Driver": "—", "Sorter": "—", "Sales": "—"},
        {"Modul": "Master Data", "Owner": "Full CRUD + hak akses + backup", "Driver": "—", "Sorter": "—", "Sales": "—"},
        {"Modul": "Laporan", "Owner": "Ya + export", "Driver": "—", "Sorter": "—", "Sales": "Ya"},
        {"Modul": "Log", "Owner": "Ya + audit diff + export", "Driver": "—", "Sorter": "—", "Sales": "—"},
        {"Modul": "Profil", "Owner": "Ganti password", "Driver": "Ganti password", "Sorter": "Ganti password", "Sales": "Ganti password"},
    ], use_container_width=True, hide_index=True)

    st.markdown("""
**Hak akses bisa dikustomisasi** di Master Data → tab Hak Akses.
Owner/Admin selalu punya akses penuh ke semua modul.
    """)

with tab_flow:
    st.subheader("Alur harian (happy path)")
    st.markdown("""
```
Driver  →  Form kebun dinamis (tray)  →  SJ + QR auto  →  Download/Cetak QR
                ↓
Sorter  →  Scan QR / ketik SJ  →  Timbang + foto + Sortir  →  Balance?
           ├─ Ya  → Konfirmasi → Stok masuk (in_sorting)
           └─ Tidak → Sorter stop / Owner override + log
                ↓
Sales   →  Cari/buat pelanggan (diskon auto)  →  Multi-item order  →  draft/confirmed
           confirmed → potong stok sesuai resep  →  Download Invoice PDF
           Bisa edit order  →  Bisa ajukan retur
                ↓
Owner   →  Dashboard (per role), approve antrean, laporan, keuangan,
           master data CRUD, hak akses, backup DB, audit diff log
```
    """)
    st.subheader("Kebun & SJ")
    st.markdown("""
| Kebun | Kode | Contoh SJ (29 Jul 2026) |
|-------|------|-------------------------|
| RED HARVEST 1 | RH1 | `29072026RH1` |
| RED HARVEST 2 | RH2 | `29072026RH2` |

- Kebun bisa ditambah di Master Data → Kebun.
- Maksimal **1 pickup aktif per kebun per tanggal**.
- Desimal kg selalu pakai **titik**, bukan koma.
    """)

with tab_faq:
    st.subheader("Barcode & QR")
    with st.expander("Bagaimana cara cetak Surat Jalan?"):
        st.markdown("Setelah simpan pickup di halaman **Pengambilan**, QR + tombol **Cetak SJ (HTML)** otomatis muncul. Download HTML → buka di browser → Print (Ctrl+P).")
    with st.expander("Bagaimana cara scan QR di penerimaan?"):
        st.markdown("Di halaman **Penerimaan & Sortir**, pilih **Scan QR** → arahkan kamera HP ke QR code. Atau ketik nomor SJ manual di kolom input.")
    with st.expander("QR tidak terbaca / error?"):
        st.markdown("Ketik nomor SJ manual di kolom input (mode **Ketik No. SJ**). Format: `DDMMYYYYRH1`.")

    st.subheader("Pengambilan")
    with st.expander("Kenapa field tray terkunci?"):
        st.markdown("Kebun itu **sudah ada pickup** di tanggal yang sama (bukan cancelled). Aturan: **1 kebun = 1 angkut / hari**.")
    with st.expander("Bisa tambah kebun baru?"):
        st.markdown("Ya! **Master Data → tab Kebun** → tambah kebun baru (nama + kode). Kebun langsung muncul di form Pengambilan.")

    st.subheader("Penerimaan & Sortir")
    with st.expander("Di mana mengatur toleransi balance?"):
        st.markdown("**Master Data → Pengaturan → Toleransi balance (kg)**. Default `0.15` kg (±150 gram).")
    with st.expander("Sorter bisa upload foto?"):
        st.markdown("Ya! Di halaman Penerimaan, ada **upload foto timbangan** setelah input total kg.")

    st.subheader("Penjualan")
    with st.expander("Diskon otomatis dari pelanggan?"):
        st.markdown("Ya! Saat pilih pelanggan, diskon default (%) dari data pelanggan **otomatis terisi**. Bisa diubah manual sebelum simpan.")
    with st.expander("Bagaimana cara edit order?"):
        st.markdown("Di tab **Daftar Penjualan** → bagian **Edit Order** → pilih order (draft/confirmed) → edit tanggal, ongkir, diskon, catatan → Simpan.")
    with st.expander("Bagaimana cetak invoice?"):
        st.markdown("Di tab **Daftar Penjualan** → pilih order → klik **Download Invoice PDF**. Format A5, ada detail item, diskon, ongkir, total.")
    with st.expander("Format harga?"):
        st.markdown("Tampil `Rp. 37.000`. Ketik `37000`.")

    st.subheader("Retur")
    with st.expander("Bagaimana cara retur?"):
        st.markdown("Halaman **Retur** → pilih order yang sudah confirmed/shipped/delivered → isi qty per kategori + alasan → Kirim. Owner approve → stok masuk kembali.")
    with st.expander("Retur parsial?"):
        st.markdown("Ya! Bisa per kategori. Tidak harus full order.")

    st.subheader("Profil & Password")
    with st.expander("Bagaimana ganti password?"):
        st.markdown("Sidebar → tombol **Profil** → isi password lama + baru + konfirmasi → Simpan.")

    st.subheader("Master Data")
    with st.expander("Bagaimana tambah kebun baru?"):
        st.markdown("**Master Data → tab Kebun** → isi nama + kode (misal `RH3`) + lokasi → Simpan. Kebun langsung aktif dan muncul di form Pengambilan.")
    with st.expander("Bagaimana atur hak akses?"):
        st.markdown("**Master Data → tab Hak Akses** → centang/uncentang permission per role per modul → Simpan. Owner/Admin selalu full access.")
    with st.expander("Bagaimana backup database?"):
        st.markdown("**Master Data → tab Pengaturan** → bagian **Backup Database** → klik **Download Backup (.db)**. Simpan file .db sebagai backup.")

    st.subheader("Laporan & Export")
    with st.expander("Export data ke Excel/CSV?"):
        st.markdown("Tombol **Export CSV / Export Excel** tersedia di: Stok (mutasi), Keuangan (pemasukan & pengeluaran), Laporan (penjualan), Log Aktivitas.")

    st.subheader("Database")
    with st.expander("SQLite atau PostgreSQL?"):
        st.markdown("Default **SQLite** (`data/strawberry.db`). Untuk PostgreSQL, set env var `DATABASE_URL=postgresql://user:pass@host/db` sebelum menjalankan app.")

st.divider()
st.caption(f"Login sebagai **{user['name']}** ({user['role']}). Panduan ini mengikuti revisi fitur terbaru.")
