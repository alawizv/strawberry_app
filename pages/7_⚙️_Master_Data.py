"""Master Data — kategori, kebun, user, pelanggan, hak akses, backup."""
import os
import shutil
from datetime import datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import (
    get_db, Category, User, Customer, Setting, Role, hash_password,
    Farm, Permission, get_default_permissions, write_log, DB_PATH, is_sqlite,
)

st.set_page_config(page_title="Master Data", page_icon="⚙️", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## ⚙️ Master Data")
st.caption("Kategori, kebun, user, pelanggan, hak akses, pengaturan, backup")

db = get_db()
try:
    t_cat, t_farm, t_user, t_cust, t_perm, t_set = st.tabs([
        "Kategori", "Kebun", "User", "Pelanggan", "Hak Akses", "Pengaturan"
    ])

    with t_cat:
        cats = db.query(Category).order_by(Category.sort_order).all()
        if cats:
            st.dataframe([{
                "ID": c.id, "Nama": c.name, "Warna": c.color, "Order": c.sort_order,
                "Aktif": c.is_active, "Deskripsi": c.description or "",
            } for c in cats], use_container_width=True, hide_index=True)

        with st.form("add_cat"):
            st.subheader("Tambah / Edit Kategori")
            edit_cat = st.selectbox("Edit existing (kosongkan untuk baru)", [""] + [c.name for c in cats], key="edit_cat_sel")
            cat_obj = None
            if edit_cat:
                cat_obj = db.query(Category).filter_by(name=edit_cat).first()
            name = st.text_input("Nama *", value=cat_obj.name if cat_obj else "")
            desc = st.text_input("Deskripsi", value=cat_obj.description if cat_obj else "")
            color = st.color_picker("Warna", cat_obj.color if cat_obj else "#e11d48")
            order = st.number_input("Urutan", min_value=0, value=cat_obj.sort_order if cat_obj else len(cats) + 1)
            if st.form_submit_button("Simpan Kategori", type="primary"):
                if not name.strip():
                    st.error("Nama wajib.")
                elif cat_obj:
                    cat_obj.name = name.strip()
                    cat_obj.description = desc or None
                    cat_obj.color = color
                    cat_obj.sort_order = int(order)
                    write_log(db, user, "category.update", f"Edit kategori {name}", entity_type="category", entity_id=cat_obj.id)
                    db.commit()
                    flash_success(f"Kategori '{name}' diupdate.")
                    st.rerun()
                elif db.query(Category).filter_by(name=name.strip()).first():
                    st.error("Nama sudah ada.")
                else:
                    db.add(Category(name=name.strip(), description=desc or None, color=color, sort_order=int(order)))
                    write_log(db, user, "category.create", f"Tambah kategori {name}", entity_type="category")
                    db.commit()
                    flash_success(f"Kategori '{name}' ditambah.")
                    st.rerun()

        if cats:
            st.subheader("Toggle Aktif")
            for c in cats:
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"{c.name} ({c.color})")
                new_val = col2.checkbox("Aktif", value=bool(c.is_active), key=f"cat_act_{c.id}")
                if new_val != bool(c.is_active):
                    c.is_active = new_val
                    write_log(db, user, "category.toggle", f"{'Aktif' if new_val else 'Nonaktif'} kategori {c.name}", entity_type="category", entity_id=c.id)
                    db.commit()
                    st.rerun()

    with t_farm:
        farms = db.query(Farm).order_by(Farm.name).all()
        if farms:
            st.dataframe([{
                "ID": f.id, "Nama": f.name, "Kode": f.code, "Lokasi": f.location or "", "Aktif": f.is_active,
            } for f in farms], use_container_width=True, hide_index=True)

        with st.form("add_farm"):
            st.subheader("Tambah / Edit Kebun")
            edit_farm = st.selectbox("Edit existing", [""] + [f.name for f in farms], key="edit_farm_sel")
            farm_obj = None
            if edit_farm:
                farm_obj = db.query(Farm).filter_by(name=edit_farm).first()
            fname = st.text_input("Nama kebun *", value=farm_obj.name if farm_obj else "")
            fcode = st.text_input("Kode singkat *", value=farm_obj.code if farm_obj else "", max_chars=10)
            floc = st.text_input("Lokasi", value=farm_obj.location if farm_obj else "")
            if st.form_submit_button("Simpan Kebun", type="primary"):
                if not fname.strip() or not fcode.strip():
                    st.error("Nama dan kode wajib.")
                elif farm_obj:
                    farm_obj.name = fname.strip()
                    farm_obj.code = fcode.strip().upper()
                    farm_obj.location = floc or None
                    write_log(db, user, "farm.update", f"Edit kebun {fname}", entity_type="farm", entity_id=farm_obj.id)
                    db.commit()
                    flash_success(f"Kebun '{fname}' diupdate.")
                    st.rerun()
                elif db.query(Farm).filter_by(name=fname.strip()).first():
                    st.error("Nama kebun sudah ada.")
                elif db.query(Farm).filter_by(code=fcode.strip().upper()).first():
                    st.error("Kode kebun sudah ada.")
                else:
                    db.add(Farm(name=fname.strip(), code=fcode.strip().upper(), location=floc or None))
                    write_log(db, user, "farm.create", f"Tambah kebun {fname}", entity_type="farm")
                    db.commit()
                    flash_success(f"Kebun '{fname}' ditambah.")
                    st.rerun()

        if farms:
            st.subheader("Toggle Aktif Kebun")
            for f in farms:
                col1, col2 = st.columns([3, 1])
                col1.write(f"{f.name} ({f.code})")
                new_val = col2.checkbox("Aktif", value=bool(f.is_active), key=f"farm_act_{f.id}")
                if new_val != bool(f.is_active):
                    f.is_active = new_val
                    db.commit()
                    st.rerun()

    with t_user:
        users = db.query(User).order_by(User.id).all()
        st.dataframe([{
            "ID": u.id, "Nama": u.name, "Username": u.username, "Role": u.role,
            "Phone": u.phone or "", "Aktif": u.is_active,
        } for u in users], use_container_width=True, hide_index=True)

        with st.form("add_user"):
            st.subheader("Tambah / Edit User")
            edit_user = st.selectbox("Edit existing", [""] + [f"{u.username} ({u.name})" for u in users], key="edit_user_sel")
            user_obj = None
            if edit_user:
                uname = edit_user.split(" (")[0]
                user_obj = db.query(User).filter_by(username=uname).first()
            uname_field = st.text_input("Username *", value=user_obj.username if user_obj else "", disabled=bool(user_obj))
            name_field = st.text_input("Nama *", value=user_obj.name if user_obj else "")
            password = st.text_input("Password baru (kosongkan jika tidak diubah)", type="password")
            role = st.selectbox("Role", [r.value for r in Role], index=[r.value for r in Role].index(user_obj.role) if user_obj and user_obj.role in [r.value for r in Role] else 0)
            phone = st.text_input("Telepon", value=user_obj.phone if user_obj else "")
            active = st.checkbox("Aktif", value=user_obj.is_active if user_obj else True)
            if st.form_submit_button("Simpan User", type="primary"):
                if user_obj:
                    user_obj.name = name_field.strip()
                    user_obj.role = role
                    user_obj.phone = phone or None
                    user_obj.is_active = active
                    if password:
                        user_obj.password_hash = hash_password(password)
                    write_log(db, user, "user.update", f"Edit user {user_obj.username}", entity_type="user", entity_id=user_obj.id)
                    db.commit()
                    flash_success(f"User '{user_obj.username}' diupdate.")
                    st.rerun()
                else:
                    if not name_field.strip() or not uname_field.strip() or not password:
                        st.error("Nama, username, password wajib.")
                    elif db.query(User).filter_by(username=uname_field.strip()).first():
                        st.error("Username sudah dipakai.")
                    else:
                        db.add(User(name=name_field.strip(), username=uname_field.strip(),
                            password_hash=hash_password(password), role=role, phone=phone or None))
                        write_log(db, user, "user.create", f"Tambah user {uname_field.strip()}", entity_type="user")
                        db.commit()
                        flash_success(f"User '{uname_field.strip()}' ditambah.")
                        st.rerun()

    with t_cust:
        customers = db.query(Customer).order_by(Customer.name).all()
        if customers:
            st.dataframe([{
                "ID": c.id, "Nama": c.name, "Phone": c.phone or "", "Diskon %": c.default_discount_pct,
                "Aktif": c.is_active, "Alamat": c.address or "",
            } for c in customers], use_container_width=True, hide_index=True)

        with st.form("add_cust"):
            st.subheader("Tambah / Edit Pelanggan")
            edit_cust = st.selectbox("Edit existing", [""] + [c.name for c in customers], key="edit_cust_sel")
            cust_obj = None
            if edit_cust:
                cust_obj = db.query(Customer).filter_by(name=edit_cust).first()
            cname = st.text_input("Nama *", value=cust_obj.name if cust_obj else "", key="cname")
            cphone = st.text_input("Telepon", value=cust_obj.phone if cust_obj else "", key="cphone")
            caddr = st.text_area("Alamat", value=cust_obj.address if cust_obj else "")
            disc = st.number_input("Diskon default %", min_value=0.0, max_value=100.0,
                value=float(cust_obj.default_discount_pct or 0) if cust_obj else 0.0, step=0.5)
            cnotes = st.text_input("Catatan", value=cust_obj.notes if cust_obj else "")
            cactive = st.checkbox("Aktif", value=cust_obj.is_active if cust_obj else True, key="cactive")
            if st.form_submit_button("Simpan Pelanggan", type="primary"):
                if not cname.strip():
                    st.error("Nama wajib.")
                elif cust_obj:
                    cust_obj.name = cname.strip()
                    cust_obj.phone = cphone or None
                    cust_obj.address = caddr or None
                    cust_obj.default_discount_pct = float(disc)
                    cust_obj.notes = cnotes or None
                    cust_obj.is_active = cactive
                    write_log(db, user, "customer.update", f"Edit pelanggan {cname}", entity_type="customer", entity_id=cust_obj.id)
                    db.commit()
                    flash_success(f"Pelanggan '{cname}' diupdate.")
                    st.rerun()
                else:
                    db.add(Customer(name=cname.strip(), phone=cphone or None, address=caddr or None,
                        notes=cnotes or None, default_discount_pct=float(disc)))
                    write_log(db, user, "customer.create", f"Tambah pelanggan {cname}", entity_type="customer")
                    db.commit()
                    flash_success(f"Pelanggan '{cname}' ditambah.")
                    st.rerun()

    with t_perm:
        st.subheader("Hak Akses per Role × Modul")
        st.caption("Centang untuk memberikan akses. Owner/Admin selalu punya akses penuh.")
        modules = ["dashboard", "pengambilan", "penerimaan", "stok", "produk", "penjualan",
                   "keuangan", "master_data", "laporan", "log", "panduan", "retur", "profil"]
        roles_to_edit = ["driver", "sorter", "sales"]

        for role in roles_to_edit:
            st.markdown(f"### Role: **{role.upper()}**")
            perms = db.query(Permission).filter_by(role=role).all()
            perm_map = {p.module: p for p in perms}

            cols = st.columns(len(modules))
            changed = False
            for i, mod in enumerate(modules):
                with cols[i]:
                    p = perm_map.get(mod)
                    st.caption(mod)
                    v = st.checkbox("👁", value=p.can_view if p else False, key=f"v_{role}_{mod}")
                    c = st.checkbox("➕", value=p.can_create if p else False, key=f"c_{role}_{mod}")
                    e = st.checkbox("✏️", value=p.can_edit if p else False, key=f"e_{role}_{mod}")
                    d = st.checkbox("🗑", value=p.can_delete if p else False, key=f"d_{role}_{mod}")
                    a = st.checkbox("✅", value=p.can_approve if p else False, key=f"a_{role}_{mod}")
                    if p:
                        if p.can_view != v or p.can_create != c or p.can_edit != e or p.can_delete != d or p.can_approve != a:
                            p.can_view = v
                            p.can_create = c
                            p.can_edit = e
                            p.can_delete = d
                            p.can_approve = a
                            changed = True
                    elif v or c or e or d or a:
                        db.add(Permission(role=role, module=mod, can_view=v, can_create=c,
                            can_edit=e, can_delete=d, can_approve=a))
                        changed = True

        if st.button("Simpan Semua Hak Akses", type="primary"):
            write_log(db, user, "permission.update", "Update hak akses", entity_type="permission")
            db.commit()
            flash_success("Hak akses disimpan.")
            st.rerun()

    with t_set:
        company = db.query(Setting).filter_by(key="company_name").first()
        tol = db.query(Setting).filter_by(key="tolerance_kg").first()
        st.info("**Toleransi balance** = selisih maksimal (kg) antara total timbang vs total sortir.")
        with st.form("settings"):
            cname = st.text_input("Nama perusahaan", value=company.value if company else "Strawberry Fresh Supply")
            tolerance = st.number_input("Toleransi balance (kg)", min_value=0.0,
                value=float(tol.value) if tol else 0.15, step=0.05, format="%.2f")
            st.caption(f"Preview: sorter boleh selisih maksimal **±{float(tolerance):g} kg**")
            if st.form_submit_button("Simpan Pengaturan", type="primary"):
                if company:
                    company.value = cname
                else:
                    db.add(Setting(key="company_name", value=cname))
                if tol:
                    tol.value = str(tolerance)
                else:
                    db.add(Setting(key="tolerance_kg", value=str(tolerance)))
                write_log(db, user, "settings.update", f"Update pengaturan: toleransi ±{float(tolerance):g}kg", entity_type="setting")
                db.commit()
                flash_success(f"Pengaturan disimpan. Toleransi: ±{float(tolerance):g} kg")
                st.rerun()

        st.divider()
        st.subheader("Database Info")
        st.caption(f"Engine: {'SQLite' if is_sqlite else 'PostgreSQL'}")
        if is_sqlite:
            st.caption(f"Path: `{DB_PATH}`")
            st.subheader("Backup Database")
            if os.path.isfile(DB_PATH):
                with open(DB_PATH, "rb") as f:
                    db_bytes = f.read()
                st.download_button("📥 Download Backup (.db)", db_bytes, "strawberry_backup.db", "application/octet-stream")
            else:
                st.warning("File database tidak ditemukan.")
        else:
            st.caption("PostgreSQL — backup via pg_dump atau tool database.")
finally:
    db.close()
