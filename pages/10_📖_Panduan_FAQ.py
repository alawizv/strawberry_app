"""Panduan operasional + FAQ sesuai aturan aplikasi saat ini."""
import streamlit as st

from auth_utils import require_login, show_user_sidebar

st.set_page_config(page_title="Panduan & FAQ", page_icon="📖", layout="wide")
user = require_login(["owner", "admin", "driver", "sorter", "sales"])
show_user_sidebar()

st.markdown("## 📖 Panduan & FAQ")
st.caption("Dokumentasi operasional yang selaras dengan aturan aplikasi saat ini")

tab_guide, tab_roles, tab_flow, tab_faq = st.tabs([
    "Panduan Modul",
    "Hak Akses Role",
    "Alur Kerja",
    "FAQ",
])

with tab_guide:
    st.subheader("1. Login & Dashboard")
    st.markdown("""
- Login di halaman **Dashboard**. Session user disimpan di browser session Streamlit.
- **Tema Light / Dark** di sidebar (bisa diganti kapan saja; preferensi per sesi browser).
- UI **responsif**: mobile (tombol full-width, tab scroll, padding rapat), tablet, desktop.
- **Dashboard Owner** interaktif: filter tanggal, filter kebun, KPI, grafik omzet/stok/yield,
  breakdown % sortir, antrean approve, snapshot keuangan.
- Role non-owner melihat ringkasan operasional (tanpa panel approve).
- Setelah aksi sukses: **toast + banner hijau + balloons** (feedback wajib).
    """)

    st.subheader("2. Pengambilan (Driver / Owner)")
    st.markdown("""
- Form ringkas: **Tanggal** + tray **RED HARVEST 1** + tray **RED HARVEST 2** + TOTAL tray.
- 1 submit dapat membuat **hingga 2 SJ** otomatis (jika tray > 0 per kebun).
- Format No. SJ: `DDMMYYYY` + kode kebun (`RH1` / `RH2`), contoh `29072026RH1`.
- **Aturan 1 kebun / 1 hari**: jika kebun sudah punya pickup (bukan cancelled) di tanggal itu,
  field tray **dikunci** — tidak bisa input lagi.
- Driver **tidak bisa edit** data tersimpan. Koreksi lewat **Permintaan Koreksi** → Owner approve/tolak.
- Owner dapat batalkan pickup pending; semua tercatat di **Log Aktivitas**.
    """)

    st.subheader("3. Penerimaan & Sortir (Sorter / Owner)")
    st.markdown("""
- Daftar **hanya SJ pending yang belum diterima**. Yang sudah diterima hilang dari antrean, ada di **Riwayat**.
- **1 SJ = 1 kali penerimaan** (anti double-submit + lock session + cek DB).
- **Dicek oleh** otomatis dari akun login (tidak bisa diedit).
- Input kg: desimal pakai **titik** (contoh `12.5`).
- **Balance**: selisih |total timbang − total sortir| ≤ toleransi (default `0.15` kg).
  - Hijau = balance OK · Merah = tidak balance.
  - **Sorter** hanya boleh simpan jika balance.
  - **Owner** boleh **override** tidak balance (konfirmasi + log `receiving.override`).
- Toleransi diatur di **Master Data → Pengaturan**.
- Simpan wajib **konfirmasi popup** sebelum commit.
- Owner dapat **hapus riwayat** → rollback stok + pickup kembali pending + log.
    """)

    st.subheader("4. Stok")
    st.markdown("""
- Menampilkan stok real-time per kategori + **riwayat mutasi** (filter tipe / arah).
- **Tipe mutasi:**
  - `in_sorting` — masuk dari penerimaan/sortir (+)
  - `out_sale` — keluar karena penjualan confirmed (−)
  - `adjustment` — penyesuaian manual / rollback
  - `in_return` — pengembalian stok saat order dibatalkan (+)
- **Adjustment stok**:
  - **Sorter** mengajukan → Owner approve/tolak.
  - **Owner** boleh **langsung terapkan** (tanpa antrean) · tetap **wajib log**.
  - Role lain (driver, sales) **tidak bisa**.
    """)

    st.subheader("5. Produk")
    st.markdown("""
- Tampilan kartu (2 kolom) + gambar opsional; detail di expander collapsible.
- Harga display: `Rp. 37.000` · input ketik angka `37000`.
- **Sales** membuat produk → status **pending** (belum aktif dijual).
- **Owner** membuat produk → langsung **approved & aktif**.
- Owner approve/tolak di tab **Approve Produk**.
- Penjualan hanya memakai produk `is_active` + `approval_status=approved`.
    """)

    st.subheader("6. Penjualan")
    st.markdown("""
- Cari pelanggan ketik nama; jika tidak ketemu → **New Customer**.
- **Multi-item**: tambah baris, produk beda, qty beda, harga custom per baris.
- **Diskon % dihilangkan** (sementara). Hanya **diskon nominal (Rp)** di atas tombol simpan.
- Subtotal/total **live** (update saat qty/produk/harga/ongkir berubah).
- Total = (Σ qty×harga) − diskon nominal + ongkir (tidak negatif setelah diskon).
- Status `confirmed` memotong **stok bahan per kategori** sesuai **resep produk** (bukan stok “produk jadi”).
  Contoh: jual 10 kg Mix 50% Jumbo + 50% AB → stok JUMBO −5 kg, AB MIX −5 kg.
- Cek stok cukup per kategori sebelum konfirmasi.
- Metode kirim: GO SEND, Paxel, Kurir Sendiri, Mobil Box Sewa.
    """)

    st.subheader("7. Keuangan, Master Data, Laporan, Log")
    st.markdown("""
- **Keuangan**: omzet penjualan vs pengeluaran (owner).
- **Master Data**: kategori, user, pelanggan, nama perusahaan, **toleransi balance**.
- **Laporan**: filter periode, stok, yield, performa driver/sales, top produk.
- **Log Aktivitas** (owner): audit trail multi-owner.
  - **Ringkasan** = kalimat manusia.
  - **Detail** = payload teknis (JSON/qty/field) untuk audit, bukan aksi terpisah.
    """)

with tab_roles:
    st.subheader("Matriks role")
    st.dataframe([
        {"Modul": "Dashboard", "Owner": "Penuh + filter + antrean", "Driver": "Ringkas", "Sorter": "Ringkas", "Sales": "Ringkas"},
        {"Modul": "Pengambilan", "Owner": "Ya + batalkan + approve koreksi", "Driver": "Buat + minta koreksi", "Sorter": "—", "Sales": "—"},
        {"Modul": "Penerimaan", "Owner": "Ya + override + hapus riwayat", "Driver": "—", "Sorter": "Ya (wajib balance)", "Sales": "—"},
        {"Modul": "Stok lihat", "Owner": "Ya", "Driver": "Ya", "Sorter": "Ya", "Sales": "Ya"},
        {"Modul": "Adjustment stok", "Owner": "Langsung + approve", "Driver": "Tidak", "Sorter": "Ajukan saja", "Sales": "Tidak"},
        {"Modul": "Edit/hapus pickup", "Owner": "Langsung + log", "Driver": "Minta koreksi", "Sorter": "—", "Sales": "—"},
        {"Modul": "Produk", "Owner": "CRUD + approve", "Driver": "—", "Sorter": "—", "Sales": "Ajukan (pending)"},
        {"Modul": "Penjualan", "Owner": "Ya", "Driver": "—", "Sorter": "—", "Sales": "Ya"},
        {"Modul": "Keuangan", "Owner": "Ya", "Driver": "—", "Sorter": "—", "Sales": "—"},
        {"Modul": "Master Data", "Owner": "Ya", "Driver": "—", "Sorter": "—", "Sales": "—"},
        {"Modul": "Laporan", "Owner": "Ya", "Driver": "—", "Sorter": "—", "Sales": "Ya"},
        {"Modul": "Log / Panduan", "Owner": "Ya", "Driver": "Panduan", "Sorter": "Panduan", "Sales": "Panduan"},
    ], use_container_width=True, hide_index=True)

    st.markdown("""
**Prinsip persetujuan Owner (multi-owner / partner):**
- Perubahan sensitif yang sudah disepakati: koreksi pickup, produk dari sales, adjustment stok,
  override tidak balance, hapus riwayat penerimaan — **wajib lewat approve / aksi owner** dan **masuk log**.
- Dua owner bisa berbagi akun role `owner` (disarankan 2 user role owner di Master Data).
    """)

with tab_flow:
    st.subheader("Alur harian (happy path)")
    st.markdown("""
```
Driver  →  Form 2 kebun (tray)  →  SJ auto  →  status pending
                ↓
Sorter  →  Pilih SJ pending  →  Timbang + Sortir  →  Balance?
           ├─ Ya  → Konfirmasi → Stok masuk (in_sorting)
           └─ Tidak → Sorter stop / Owner override + log
                ↓
Sales   →  Cari/buat pelanggan  →  Multi-item order  →  draft/confirmed
           confirmed → potong stok sesuai resep produk
                ↓
Owner   →  Dashboard, approve antrean, laporan, keuangan, log
```
    """)
    st.subheader("Kebun & SJ")
    st.markdown("""
| Kebun | Kode | Contoh SJ (29 Jul 2026) |
|-------|------|-------------------------|
| RED HARVEST 1 | RH1 | `29072026RH1` |
| RED HARVEST 2 | RH2 | `29072026RH2` |

- Maksimal **1 pickup aktif per kebun per tanggal**.
- Desimal kg selalu pakai **titik**, bukan koma.
    """)

with tab_faq:
    st.subheader("Tampilan & perangkat")
    with st.expander("Bagaimana ganti Light / Dark mode?"):
        st.markdown(
            "Di **sidebar** pilih **☀️ Light** atau **🌙 Dark**. "
            "Bisa diganti kapan saja (login & setelah login). Preferensi per sesi browser."
        )
    with st.expander("Apakah app responsif di HP?"):
        st.markdown(
            "Ya. Mobile: tombol full-width, tab bisa digeser horizontal, padding rapat, "
            "kartu/metric menyesuaikan. Tablet & desktop: layout multi-kolom penuh."
        )

    st.subheader("Pengambilan")
    with st.expander("Kenapa field tray terkunci / tidak bisa input?"):
        st.markdown(
            "Kebun itu **sudah punya pickup** di tanggal yang sama (bukan cancelled). "
            "Aturan sementara: **1 kebun = 1 angkut / hari**. Ganti tanggal, atau batalkan "
            "(owner) / ajukan koreksi jika data salah."
        )
    with st.expander("Apakah 1 submit selalu buat 2 SJ?"):
        st.markdown(
            "Hanya untuk kebun dengan **tray > 0** dan **belum terdaftar** hari itu. "
            "Tray 0 = tidak dibuat. Kebun terkunci = skip."
        )
    with st.expander("Driver salah input tray, bagaimana?"):
        st.markdown(
            "Driver **tidak edit langsung**. Buka **Permintaan Koreksi** → isi alasan → "
            "Owner approve di tab Approve / halaman terkait."
        )

    st.subheader("Penerimaan & Sortir")
    with st.expander("Di mana mengatur toleransi balance (0.15 kg)?"):
        st.markdown(
            "**Master Data → tab Pengaturan → Toleransi balance (kg)**. "
            "Contoh `0.15` = ±150 gram. Naikkan jika selisih operasional wajar lebih besar."
        )
    with st.expander("Tidak balance — siapa boleh simpan?"):
        st.markdown(
            "**Sorter**: tidak boleh. **Owner**: boleh override dengan konfirmasi; tercatat log."
        )
    with st.expander("Kenapa SJ hilang dari list penerimaan?"):
        st.markdown(
            "Sudah diterima → status `received` → hanya di **Riwayat**. List proses murni pending."
        )
    with st.expander("Saya klik simpan berkali-kali, stok jadi berlipat?"):
        st.markdown(
            "Sudah dicegah: konfirmasi, session lock, cek receiving unik per pickup. "
            "Jika data lama sempat dobel, owner **hapus riwayat** (rollback) atau adjustment lewat sorter+owner."
        )

    st.subheader("Stok & Mutasi")
    with st.expander("Tipe mutasi stok (kolom Type) ada apa saja?"):
        st.markdown("""
| Tipe (kode) | Arah | Kapan muncul |
|-------------|------|----------------|
| **`in_sorting`** | Masuk (+) | Penerimaan & sortir disimpan (balance/override) |
| **`out_sale`** | Keluar (−) | Order penjualan status **`confirmed`** (potong stok per resep) |
| **`adjustment`** | Masuk/keluar | Owner adjustment langsung, approve adjustment sorter, atau rollback hapus data |
| **`in_return`** | Masuk (+) | Order confirmed dibatalkan → stok dikembalikan |

**Qty kg:** angka positif = stok naik · negatif = stok turun.

**Kenapa cuma kelihatan `in_sorting`?**  
Mutasi lain baru muncul setelah ada aksi terkait. Contoh: penjualan masih **draft** → belum `out_sale`.  
Adjustment belum pernah di-approve/diterapkan → belum ada baris `adjustment`.
        """)
    with st.expander("Siapa boleh adjustment stok?"):
        st.markdown(
            "**Sorter** mengajukan → Owner approve. "
            "**Owner** boleh langsung terapkan tanpa approve (tetap masuk log). "
            "Driver/Sales tidak bisa."
        )
    with st.expander("Sales/Driver bisa adjustment?"):
        st.markdown("**Tidak.** Hanya lihat stok (jika punya akses halaman).")
    with st.expander("Saat produk terjual, stok berkurang bagaimana?"):
        st.markdown("""
**Ya, stok bahan berkurang** — yang dipotong adalah **kategori bahan** (JUMBO / B / AB MIX)
sesuai **resep** produk, **bukan** “stok produk jadi” terpisah.

| Contoh jual | Resep | Efek stok | Mutasi |
|-------------|-------|-----------|--------|
| 10 kg Strawberry JUMBO (pure) | 100% JUMBO | JUMBO −10 kg | `out_sale` |
| 10 kg Mix 50% Jumbo + 50% AB | 0.5 + 0.5 | JUMBO −5, AB −5 | `out_sale` ×2 kategori |
| 9 kg Mix ⅓+⅓+⅓ | ⅓ tiap | masing-masing −3 kg | `out_sale` ×3 |

Hanya order **`confirmed`** yang memotong stok. **`draft` tidak potong.**  
Batal confirmed → muncul `in_return` (stok kembali).  
Cek di **Stok → Riwayat Mutasi** (filter tipe `out_sale` / Keluar).
        """)

    st.subheader("Produk & Penjualan")
    with st.expander("Produk sales tidak muncul di order?"):
        st.markdown("Belum di-**approve owner** atau `is_active=false`. Cek tab Approve Produk.")
    with st.expander("Format harga?"):
        st.markdown("Tampil `Rp. 37.000`. Ketik `37000` (titik pemisah ribuan di display).")
    with st.expander("Diskon persen hilang?"):
        st.markdown(
            "Sengaja disederhanakan: hanya **diskon nominal (Rp)** di atas tombol simpan order."
        )
    with st.expander("Subtotal tidak berubah saat ganti qty?"):
        st.markdown(
            "Bug lama (total di dalam form Streamlit). Sudah diganti perhitungan **live di luar form** "
            "dengan multi-baris item. Restart app jika masih cache lama."
        )
    with st.expander("Satu pelanggan beli banyak jenis?"):
        st.markdown(
            "Ya. Tombol **Tambah baris item** — tiap baris produk/qty/harga sendiri. "
            "Subtotal = jumlah (qty × harga) semua baris."
        )

    st.subheader("Log, Owner, Data")
    with st.expander("Kolom Detail di Log untuk apa?"):
        st.markdown(
            "Pelengkap **Ringkasan**: data teknis (JSON payload, qty, field diubah). "
            "Bukan menu aksi. Untuk audit 2 owner/partner & debug."
        )
    with st.expander("Apakah log bisa dihapus?"):
        st.markdown(
            "**Tidak.** Log permanen (tidak ada tombol hapus). "
            "Edit/hapus data bisnis tetap meninggalkan jejak di log."
        )
    with st.expander("Owner edit/hapus pickup di riwayat?"):
        st.markdown(
            "Ya, di **Riwayat Pickup**: Edit / Batalkan / Hapus permanen — **tanpa approve**, "
            "wajib log. Hapus yang sudah received akan rollback stok penerimaan dulu."
        )
    with st.expander("Apakah semua perubahan harus approve owner?"):
        st.markdown("""
Yang **wajib owner** (saat ini):
- Approve/tolak koreksi pickup
- Approve/tolak produk sales
- Approve/tolak adjustment stok
- Override penerimaan tidak balance
- Hapus riwayat penerimaan
- Master data kritis (user, toleransi) — akses halaman hanya owner

Yang **langsung** tanpa antrean approve (tetap ter-log bila relevan):
- Driver buat pickup baru
- Sorter simpan penerimaan **yang balance**
- Sales buat order (draft/confirmed)
- Owner buat produk langsung aktif
        """)
    with st.expander("Database di mana? PostgreSQL?"):
        st.markdown(
            "Sekarang **SQLite** di `data/strawberry.db` (localhost). "
            "Siap migrasi PostgreSQL / PostgREST nanti tanpa mengubah alur bisnis."
        )
    with st.expander("Upload foto di mana?"):
        st.markdown("`uploads/` (pickup) dan `uploads/products/` (gambar produk).")

st.divider()
st.caption(
    f"Login sebagai **{user['name']}** ({user['role']}). "
    "Panduan ini mengikuti revisi fitur terbaru aplikasi."
)
