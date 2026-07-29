"""Modul Produk — murni & campuran, image, approval sales→owner."""
import os
from datetime import datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import (
    get_db, Product, ProductRecipe, Category, write_log, format_rp, parse_rp,
)
from ui_theme import is_dark

st.set_page_config(page_title="Produk", page_icon="🍓", layout="wide")
user = require_login(["owner", "admin", "sales"])
show_user_sidebar()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "products")
os.makedirs(UPLOAD_DIR, exist_ok=True)

is_owner = user["role"] in ("owner", "admin")

st.markdown("## 🍓 Produk")
st.caption("Katalog produk murni / campuran · Sales buat → Owner approve")
if not is_owner:
    st.info("Sales bisa mengajukan produk baru. Produk aktif setelah **disetujui owner**.")

# Price text helpers in session
def _price_key(pid: str) -> str:
    return f"price_txt_{pid}"


db = get_db()
try:
    cats = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()
    tabs = ["Daftar Produk", "Tambah Produk"]
    if is_owner:
        tabs.append("Approve Produk")
    tab_objs = st.tabs(tabs)
    tab_list, tab_add = tab_objs[0], tab_objs[1]
    tab_appr = tab_objs[2] if is_owner else None

    with tab_list:
        show_pending = st.checkbox("Tampilkan juga yang pending", value=is_owner)
        q = db.query(Product).order_by(Product.created_at.desc())
        if not show_pending:
            q = q.filter(Product.approval_status == "approved")
        products = q.all()

        if not products:
            st.info("Belum ada produk.")
        else:
            # Fashion-style grid: 2 cards per row
            for i in range(0, len(products), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j >= len(products):
                        break
                    p = products[i + j]
                    with col:
                        status_badge = {
                            "approved": "🟢",
                            "pending": "🟡",
                            "rejected": "🔴",
                        }.get(p.approval_status or "approved", "⚪")
                        active_txt = "Aktif" if p.is_active else "Nonaktif"
                        header = f"{status_badge} **{p.name}** · {format_rp(p.base_price)}"

                        with st.container(border=True):
                            c_img, c_info = st.columns([1, 2])
                            with c_img:
                                if p.image_path and os.path.isfile(p.image_path):
                                    st.image(p.image_path, use_container_width=True)
                                else:
                                    grad = (
                                        "linear-gradient(135deg,#3f1d2e,#7f1d1d)"
                                        if is_dark()
                                        else "linear-gradient(135deg,#ffe4e6,#fecdd3)"
                                    )
                                    st.markdown(
                                        f"""
                                        <div style="background:{grad};
                                        border-radius:12px;height:140px;display:flex;align-items:center;
                                        justify-content:center;font-size:3rem;">🍓</div>
                                        """,
                                        unsafe_allow_html=True,
                                    )
                            with c_info:
                                st.markdown(header)
                                st.caption(
                                    f"{(p.product_type or 'pure').upper()} · {active_txt} · "
                                    f"{p.approval_status or 'approved'}"
                                )
                                if p.created_by:
                                    st.caption(f"Oleh: {p.created_by}")

                            with st.expander("Lihat detail & resep", expanded=False):
                                if p.description:
                                    st.write(p.description)
                                else:
                                    st.caption("Tidak ada deskripsi.")
                                recipes = p.recipes or []
                                if recipes:
                                    st.markdown("**Resep bahan:**")
                                    for r in recipes:
                                        cname = r.category.name if r.category else r.category_id
                                        st.write(f"• {cname}: **{r.ratio * 100:g}%**")
                                else:
                                    st.caption("Belum ada resep.")
                                st.markdown(f"**Harga:** {format_rp(p.base_price)} / kg")

                                if is_owner and (p.approval_status or "approved") == "approved":
                                    st.divider()
                                    st.caption("Edit (Owner) · ketik angka, titik pemisah ribuan otomatis di display")
                                    pk = _price_key(str(p.id))
                                    if pk not in st.session_state:
                                        st.session_state[pk] = f"{int(p.base_price or 0):,}".replace(",", ".")
                                    price_txt = st.text_input(
                                        "Harga (Rp)",
                                        key=pk,
                                        help="Contoh ketik: 37000 → tampil Rp. 37.000",
                                    )
                                    # live display
                                    parsed = parse_rp(price_txt)
                                    st.caption(f"Preview: **{format_rp(parsed)}**")

                                    img_up = st.file_uploader(
                                        "Ganti gambar",
                                        type=["jpg", "jpeg", "png", "webp"],
                                        key=f"img_{p.id}",
                                    )
                                    active = st.checkbox("Aktif dijual", value=bool(p.is_active), key=f"act_{p.id}")
                                    if st.button("Simpan perubahan", key=f"upd_{p.id}", type="primary"):
                                        p.base_price = float(parsed)
                                        p.is_active = active
                                        if img_up is not None:
                                            ext = os.path.splitext(img_up.name)[1] or ".jpg"
                                            fname = f"prod_{p.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                                            path = os.path.join(UPLOAD_DIR, fname)
                                            with open(path, "wb") as f:
                                                f.write(img_up.getbuffer())
                                            p.image_path = path
                                        write_log(
                                            db, user, "product.update",
                                            f"Update produk {p.name} harga {format_rp(parsed)}",
                                            entity_type="product", entity_id=p.id,
                                        )
                                        db.commit()
                                        flash_success(f"Produk '{p.name}' diupdate.")
                                        st.rerun()

    with tab_add:
        if not cats:
            st.error("Belum ada kategori. Buat di Master Data dulu.")
        else:
            if is_owner:
                st.caption("Owner: produk langsung **approved & aktif**.")
            else:
                st.caption("Sales: produk masuk antrean **pending** sampai owner approve.")

            name = st.text_input("Nama produk *")
            ptype = st.selectbox("Tipe", ["pure", "mixed"])
            price_raw = st.text_input(
                "Harga dasar (Rp/kg) *",
                value="35000",
                help="Ketik angka saja, contoh 37000",
                key="new_price_txt",
            )
            st.caption(f"Preview harga: **{format_rp(parse_rp(price_raw))}**")
            desc = st.text_area("Deskripsi")
            img = st.file_uploader("Gambar produk", type=["jpg", "jpeg", "png", "webp"], key="new_img")

            st.markdown("**Resep (rasio 0–1, total sebaiknya 1.0)**")
            ratios = {}
            rcols = st.columns(len(cats))
            for i, c in enumerate(cats):
                with rcols[i]:
                    default = 1.0 if (ptype == "pure" and i == 0) else 0.0
                    ratios[c.id] = st.number_input(
                        c.name,
                        min_value=0.0,
                        max_value=1.0,
                        value=default,
                        step=0.05,
                        format="%.2f",
                        key=f"ratio_{c.id}",
                    )
            total_r = sum(ratios.values())
            st.caption(f"Total rasio: {total_r:.2f}")

            btn_label = "Simpan Produk (langsung aktif)" if is_owner else "Ajukan Produk (butuh approve)"
            if st.button(btn_label, type="primary", use_container_width=True):
                price = parse_rp(price_raw)
                if not name.strip():
                    st.error("Nama wajib diisi.")
                elif db.query(Product).filter(Product.name == name.strip()).first():
                    st.error("Nama produk sudah ada.")
                elif total_r <= 0:
                    st.error("Minimal satu rasio > 0.")
                elif price <= 0:
                    st.error("Harga harus > 0.")
                else:
                    approved = is_owner
                    p = Product(
                        name=name.strip(),
                        product_type=ptype,
                        base_price=float(price),
                        description=desc or None,
                        approval_status="approved" if approved else "pending",
                        is_active=True if approved else False,
                        created_by=user["name"],
                    )
                    db.add(p)
                    db.flush()
                    for cid, r in ratios.items():
                        if r > 0:
                            db.add(ProductRecipe(product_id=p.id, category_id=cid, ratio=float(r)))
                    if img is not None:
                        ext = os.path.splitext(img.name)[1] or ".jpg"
                        fname = f"prod_{p.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                        path = os.path.join(UPLOAD_DIR, fname)
                        with open(path, "wb") as f:
                            f.write(img.getbuffer())
                        p.image_path = path
                    write_log(
                        db, user,
                        "product.create" if approved else "product.request",
                        f"{'Buat' if approved else 'Ajukan'} produk {p.name} ({format_rp(price)})",
                        entity_type="product", entity_id=p.id,
                    )
                    db.commit()
                    if approved:
                        flash_success(f"✅ Produk '{name}' aktif · {format_rp(price)}")
                    else:
                        flash_success(f"📤 Produk '{name}' diajukan. Menunggu approve owner.")
                    st.rerun()

    if tab_appr is not None:
        with tab_appr:
            st.subheader("Approve / Tolak Produk (Sales)")
            pending = (
                db.query(Product)
                .filter(Product.approval_status == "pending")
                .order_by(Product.created_at.asc())
                .all()
            )
            if not pending:
                st.info("Tidak ada produk pending.")
            else:
                for p in pending:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 3])
                        with c1:
                            if p.image_path and os.path.isfile(p.image_path):
                                st.image(p.image_path, use_container_width=True)
                            else:
                                st.markdown("🍓")
                        with c2:
                            st.markdown(f"### {p.name}")
                            st.write(f"**Harga:** {format_rp(p.base_price)} · Tipe: {p.product_type}")
                            st.write(p.description or "-")
                            st.caption(f"Diajukan: {p.created_by or '-'} · {str(p.created_at)[:19]}")
                            recipes = p.recipes or []
                            if recipes:
                                st.write("Resep: " + ", ".join(
                                    f"{r.category.name if r.category else r.category_id} {r.ratio*100:g}%"
                                    for r in recipes
                                ))
                            a1, a2 = st.columns(2)
                            with a1:
                                if st.button("Approve & Aktifkan", key=f"ap_prod_{p.id}", type="primary"):
                                    p.approval_status = "approved"
                                    p.is_active = True
                                    write_log(
                                        db, user, "product.approve",
                                        f"Approve produk {p.name}",
                                        entity_type="product", entity_id=p.id,
                                    )
                                    db.commit()
                                    flash_success(f"Produk '{p.name}' disetujui & aktif.")
                                    st.rerun()
                            with a2:
                                if st.button("Tolak", key=f"rj_prod_{p.id}"):
                                    p.approval_status = "rejected"
                                    p.is_active = False
                                    write_log(
                                        db, user, "product.reject",
                                        f"Tolak produk {p.name}",
                                        entity_type="product", entity_id=p.id,
                                    )
                                    db.commit()
                                    flash_success(f"Produk '{p.name}' ditolak.", balloons=False)
                                    st.rerun()
finally:
    db.close()
