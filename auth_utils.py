"""Shared auth helpers for multipage Streamlit app with granular permissions."""
import streamlit as st

from ui_theme import apply_theme, theme_toggle, get_theme_mode

MODULE_MAP = {
    "Pengambilan": "pengambilan",
    "Penerimaan Sortir": "penerimaan",
    "Penerimaan & Sortir": "penerimaan",
    "Stok": "stok",
    "Produk": "produk",
    "Penjualan": "penjualan",
    "Keuangan": "keuangan",
    "Master Data": "master_data",
    "Laporan": "laporan",
    "Log Aktivitas": "log",
    "Panduan FAQ": "panduan",
    "Retur": "retur",
    "Profil": "profil",
}

DEFAULT_ROLE_PAGES = {
    "owner": set(MODULE_MAP.values()),
    "admin": set(MODULE_MAP.values()),
    "driver": {"dashboard", "pengambilan", "stok", "panduan", "profil"},
    "sorter": {"dashboard", "penerimaan", "stok", "panduan", "profil"},
    "sales": {"dashboard", "produk", "penjualan", "stok", "laporan", "panduan", "retur", "profil"},
}


def require_login(allowed_roles=None, module=None):
    apply_theme()
    if "user" not in st.session_state or st.session_state.user is None:
        st.warning("Silakan login dulu di halaman utama (Dashboard).")
        st.stop()
    user = st.session_state.user
    if allowed_roles and user.get("role") not in allowed_roles:
        st.error("Anda tidak punya akses ke halaman ini.")
        st.stop()
    show_flash()
    return user


def check_permission(user, module_name, action="view"):
    role = user.get("role", "")
    if role in ("owner", "admin"):
        return True
    from database import get_db, Permission
    db = get_db()
    try:
        perm = db.query(Permission).filter_by(role=role, module=module_name).first()
        if not perm:
            return True
        if action == "view":
            return perm.can_view
        if action == "create":
            return perm.can_create
        if action == "edit":
            return perm.can_edit
        if action == "delete":
            return perm.can_delete
        if action == "approve":
            return perm.can_approve
        return False
    finally:
        db.close()


def flash_success(msg: str, balloons: bool = True):
    st.session_state["_flash"] = {"type": "success", "msg": msg, "balloons": balloons}


def flash_error(msg: str):
    st.session_state["_flash"] = {"type": "error", "msg": msg, "balloons": False}


def show_flash():
    f = st.session_state.pop("_flash", None)
    if not f:
        return
    msg = f.get("msg") or ""
    if f.get("type") == "error":
        st.error(msg)
        try:
            st.toast(msg, icon="❌")
        except Exception:
            pass
        return
    st.success(msg)
    try:
        st.toast(msg, icon="✅")
    except Exception:
        pass
    if f.get("balloons"):
        st.balloons()


def go_home_logout():
    st.session_state.user = None
    st.rerun()


def show_user_sidebar():
    user = st.session_state.get("user")
    if not user:
        return
    with st.sidebar:
        st.markdown(f"**👤 {user['name']}**")
        st.caption(f"Role: {user['role'].upper()}")
        st.markdown(
            f'<span class="theme-badge">{get_theme_mode().title()} mode</span>',
            unsafe_allow_html=True,
        )
        st.divider()
        theme_toggle(key="theme_mode_radio")
        st.divider()
        st.page_link("pages/12_🔐_Profil.py", label="🔐 Profil", use_container_width=True)
        if st.button("Logout", key="logout_page", use_container_width=True):
            go_home_logout()
