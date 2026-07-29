"""Shared auth helpers for multipage Streamlit app."""
import streamlit as st

from ui_theme import apply_theme, theme_toggle, get_theme_mode


ROLE_PAGES = {
    "owner": {
        "Pengambilan", "Penerimaan Sortir", "Stok", "Produk",
        "Penjualan", "Keuangan", "Master Data", "Laporan",
        "Log Aktivitas", "Panduan FAQ",
    },
    "admin": {
        "Pengambilan", "Penerimaan Sortir", "Stok", "Produk",
        "Penjualan", "Keuangan", "Master Data", "Laporan",
        "Log Aktivitas", "Panduan FAQ",
    },
    "driver": {"Pengambilan", "Stok", "Panduan FAQ"},
    "sorter": {"Penerimaan Sortir", "Stok", "Panduan FAQ"},
    "sales": {"Penjualan", "Stok", "Produk", "Laporan", "Panduan FAQ"},
}


def require_login(allowed_roles=None):
    # Theme first — reduces white flash when multipage script reloads
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
    for page in ("Dashboard.py", "app.py"):
        try:
            st.switch_page(page)
            return
        except Exception:
            continue
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
        if st.button("Logout", key="logout_page", use_container_width=True):
            go_home_logout()
