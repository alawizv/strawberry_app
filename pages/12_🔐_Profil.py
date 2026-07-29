"""Profil user — ganti password."""
import streamlit as st
from auth_utils import require_login, show_user_sidebar, flash_success, flash_error
from database import get_db, User, hash_password, verify_password

st.set_page_config(page_title="Profil", page_icon="🔐", layout="wide")
user = require_login()
show_user_sidebar()

st.markdown("## 🔐 Profil Saya")
st.caption(f"Login sebagai: **{user['name']}** ({user['role']})")

with st.form("change_password"):
    st.subheader("Ganti Password")
    old_pw = st.text_input("Password lama", type="password")
    new_pw = st.text_input("Password baru", type="password")
    confirm_pw = st.text_input("Konfirmasi password baru", type="password")

    if st.form_submit_button("Simpan", type="primary"):
        if not old_pw or not new_pw:
            st.error("Semua field wajib diisi.")
        elif new_pw != confirm_pw:
            st.error("Konfirmasi password tidak cocok.")
        elif len(new_pw) < 4:
            st.error("Password minimal 4 karakter.")
        else:
            db = get_db()
            try:
                u = db.get(User, user["id"])
                if u and verify_password(old_pw, u.password_hash):
                    u.password_hash = hash_password(new_pw)
                    db.commit()
                    flash_success("Password berhasil diubah!")
                    st.rerun()
                else:
                    st.error("Password lama salah.")
            finally:
                db.close()
