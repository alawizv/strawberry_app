"""Master Data — kategori, user, pelanggan, setting toleransi."""
import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import get_db, Category, User, Customer, Setting, Role, hash_password

st.set_page_config(page_title="Master Data", page_icon="⚙️", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## ⚙️ Master Data")
st.caption("Kategori sortir, user & role, pelanggan, toleransi balance")

db = get_db()
try:
    t_cat, t_user, t_cust, t_set = st.tabs(["Kategori", "User", "Pelanggan", "Pengaturan"])

    with t_cat:
        cats = db.query(Category).order_by(Category.sort_order).all()
        if cats:
            st.dataframe([{
                "ID": c.id,
                "Nama": c.name,
                "Warna": c.color,
                "Order": c.sort_order,
                "Aktif": c.is_active,
                "Deskripsi": c.description or "",
            } for c in cats], use_container_width=True, hide_index=True)

        with st.form("add_cat"):
            st.subheader("Tambah Kategori")
            name = st.text_input("Nama *")
            desc = st.text_input("Deskripsi")
            color = st.color_picker("Warna", "#e11d48")
            order = st.number_input("Urutan", min_value=0, value=len(cats) + 1)
            if st.form_submit_button("Simpan Kategori", type="primary"):
                if not name.strip():
                    st.error("Nama wajib.")
                elif db.query(Category).filter_by(name=name.strip()).first():
                    st.error("Nama sudah ada.")
                else:
                    db.add(Category(name=name.strip(), description=desc or None, color=color, sort_order=int(order)))
                    db.commit()
                    flash_success(f"Kategori '{name}' ditambah.")
                    st.rerun()

        if cats:
            st.subheader("Toggle Aktif")
            for c in cats:
                col1, col2 = st.columns([3, 1])
                col1.write(c.name)
                new_val = col2.checkbox("Aktif", value=bool(c.is_active), key=f"cat_act_{c.id}")
                if new_val != bool(c.is_active):
                    c.is_active = new_val
                    db.commit()
                    st.rerun()

    with t_user:
        users = db.query(User).order_by(User.id).all()
        st.dataframe([{
            "ID": u.id,
            "Nama": u.name,
            "Username": u.username,
            "Role": u.role,
            "Phone": u.phone or "",
            "Aktif": u.is_active,
        } for u in users], use_container_width=True, hide_index=True)

        with st.form("add_user"):
            st.subheader("Tambah User")
            name = st.text_input("Nama *")
            username = st.text_input("Username *")
            password = st.text_input("Password *", type="password")
            role = st.selectbox("Role", [r.value for r in Role])
            phone = st.text_input("Telepon")
            if st.form_submit_button("Simpan User", type="primary"):
                if not name.strip() or not username.strip() or not password:
                    st.error("Nama, username, password wajib.")
                elif db.query(User).filter_by(username=username.strip()).first():
                    st.error("Username sudah dipakai.")
                else:
                    db.add(User(
                        name=name.strip(),
                        username=username.strip(),
                        password_hash=hash_password(password),
                        role=role,
                        phone=phone or None,
                    ))
                    db.commit()
                    flash_success(f"User '{username}' ditambah.")
                    st.rerun()

    with t_cust:
        customers = db.query(Customer).order_by(Customer.name).all()
        if customers:
            st.dataframe([{
                "ID": c.id,
                "Nama": c.name,
                "Phone": c.phone or "",
                "Diskon default %": c.default_discount_pct,
                "Aktif": c.is_active,
                "Alamat": c.address or "",
            } for c in customers], use_container_width=True, hide_index=True)

        with st.form("add_cust"):
            st.subheader("Tambah Pelanggan")
            name = st.text_input("Nama *", key="cname")
            phone = st.text_input("Telepon", key="cphone")
            address = st.text_area("Alamat")
            disc = st.number_input("Diskon default %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            notes = st.text_input("Catatan")
            if st.form_submit_button("Simpan Pelanggan", type="primary"):
                if not name.strip():
                    st.error("Nama wajib.")
                else:
                    db.add(Customer(
                        name=name.strip(),
                        phone=phone or None,
                        address=address or None,
                        notes=notes or None,
                        default_discount_pct=float(disc),
                    ))
                    db.commit()
                    flash_success(f"Pelanggan '{name}' ditambah.")
                    st.rerun()

    with t_set:
        company = db.query(Setting).filter_by(key="company_name").first()
        tol = db.query(Setting).filter_by(key="tolerance_kg").first()
        st.info(
            "**Toleransi balance** = selisih maksimal (kg) antara total timbang vs total sortir "
            "yang masih dianggap OK untuk sorter. Melebihi angka ini → **merah**; "
            "hanya **owner** yang boleh override simpan."
        )
        with st.form("settings"):
            cname = st.text_input("Nama perusahaan", value=company.value if company else "Strawberry Fresh Supply")
            tolerance = st.number_input(
                "Toleransi balance (kg)",
                min_value=0.0,
                value=float(tol.value) if tol else 0.15,
                step=0.05,
                format="%.2f",
                help="Contoh 0.15 = ±150 gram. Naikkan jika sering selisih wajar.",
            )
            st.caption(f"Preview: sorter boleh selisih maksimal **±{float(tolerance):g} kg** tanpa owner.")
            if st.form_submit_button("Simpan Pengaturan", type="primary"):
                if company:
                    company.value = cname
                else:
                    db.add(Setting(key="company_name", value=cname))
                if tol:
                    tol.value = str(tolerance)
                else:
                    db.add(Setting(key="tolerance_kg", value=str(tolerance)))
                db.commit()
                flash_success(f"Pengaturan disimpan. Toleransi balance: ±{float(tolerance):g} kg")
                st.rerun()
finally:
    db.close()
