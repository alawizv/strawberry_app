"""Shared UI: professional light/dark theme + responsive CSS. High-contrast dark mode."""
import streamlit as st
import streamlit.components.v1 as components

THEME_KEY = "ui_theme_mode"  # "light" | "dark"


def get_theme_mode() -> str:
    mode = st.session_state.get(THEME_KEY, "light")
    return mode if mode in ("light", "dark") else "light"


def is_dark() -> bool:
    return get_theme_mode() == "dark"


def set_theme_mode(mode: str):
    st.session_state[THEME_KEY] = "dark" if mode == "dark" else "light"


def theme_toggle(key: str = "theme_mode_radio"):
    mode = get_theme_mode()
    st.markdown("**Tampilan**")
    choice = st.radio(
        "Mode tema",
        ["☀️ Light", "🌙 Dark"],
        index=1 if mode == "dark" else 0,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    new_mode = "dark" if "Dark" in choice else "light"
    if new_mode != mode:
        set_theme_mode(new_mode)
        _persist_theme_js(new_mode)
    else:
        _persist_theme_js(mode)
    st.caption(f"Mode aktif: **{get_theme_mode().title()}**")
    return get_theme_mode()


def _persist_theme_js(mode: str):
    safe = "dark" if mode == "dark" else "light"
    bg = "#0b0f14" if safe == "dark" else "#f8fafc"
    bg2 = "#12181f" if safe == "dark" else "#ffffff"
    fg = "#f1f5f9" if safe == "dark" else "#0f172a"
    sidebar_bg = "#0d1218" if safe == "dark" else "#fff1f2"
    components.html(
        f"""
        <script>
        try {{
          localStorage.setItem('strawberry_theme', '{safe}');
          const root = window.parent.document;
          if (root) {{
            root.documentElement.setAttribute('data-strawberry-theme', '{safe}');
          }}
        }} catch (e) {{}}
        </script>
        """,
        height=0,
        width=0,
    )


def _early_paint_css() -> str:
    """Return CSS string for immediate theme injection via st.markdown (no iframe delay)."""
    dark = is_dark()
    if dark:
        bg = "#0b0f14"
        bg2 = "#12181f"
        fg = "#f1f5f9"
        fg2 = "#94a3b8"
        border = "#2a3441"
        sidebar_bg = "#0d1218"
        card = "#151c24"
    else:
        bg = "#f8fafc"
        bg2 = "#ffffff"
        fg = "#0f172a"
        fg2 = "#64748b"
        border = "#e2e8f0"
        sidebar_bg = "#fff1f2"
        card = "#ffffff"

    return f"""
<style>
/* === EARLY PAINT — apply instantly, no flash === */
html, body, .stApp, [data-testid="stAppViewContainer"],
section.main, .main .block-container {{
    background-color: {bg} !important;
    color: {fg} !important;
}}
[data-testid="stHeader"] {{ background: {bg2} !important; }}
section[data-testid="stSidebar"] {{ background: {sidebar_bg} !important; }}
section[data-testid="stSidebar"] * {{ color: {fg} !important; }}
/* Smooth transitions to eliminate perceived flash */
.stApp, section[data-testid="stSidebar"],
[data-testid="stHeader"], .main .block-container {{
    transition: none !important;
    animation: none !important;
}}
</style>
"""


def _early_paint_js():
    """Backup JS for localStorage-based theme restore (runs after CSS)."""
    components.html(
        """
        <script>
        (function () {
          try {
            const mode = localStorage.getItem('strawberry_theme') || 'light';
            const bg = mode === 'dark' ? '#0b0f14' : '#f8fafc';
            const bg2 = mode === 'dark' ? '#12181f' : '#ffffff';
            const fg = mode === 'dark' ? '#f1f5f9' : '#0f172a';
            const sidebarBg = mode === 'dark' ? '#0d1218' : '#fff1f2';
            const root = window.parent.document;
            if (!root) return;
            root.documentElement.setAttribute('data-strawberry-theme', mode);
            let el = root.getElementById('strawberry-early-theme');
            if (!el) {
              el = root.createElement('style');
              el.id = 'strawberry-early-theme';
              root.head.appendChild(el);
            }
            el.textContent = `
              html, body, .stApp, [data-testid="stAppViewContainer"],
              section.main, .main .block-container {
                background-color: ${bg} !important;
                color: ${fg} !important;
              }
              [data-testid="stHeader"] { background: ${bg2} !important; }
              section[data-testid="stSidebar"] { background: ${sidebarBg} !important; }
              section[data-testid="stSidebar"] * { color: ${fg} !important; }
            `;
            const app = root.querySelector('.stApp');
            if (app) { app.style.backgroundColor = bg; app.style.color = fg; }
            const sidebar = root.querySelector('[data-testid="stSidebar"]');
            if (sidebar) { sidebar.style.backgroundColor = sidebarBg; }
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _palette(dark: bool) -> dict:
    if dark:
        return {
            "bg": "#0b0f14",
            "bg2": "#12181f",
            "card": "#151c24",
            "border": "#2a3441",
            "text": "#f1f5f9",
            "text2": "#94a3b8",
            "muted": "#94a3b8",
            "primary": "#fb7185",
            "primary_hover": "#f43f5e",
            "primary_soft": "rgba(251,113,133,0.16)",
            "header": "#fda4af",
            "success_bg": "#052e16",
            "success_bd": "#22c55e",
            "success_tx": "#bbf7d0",
            "warn_bg": "#422006",
            "warn_bd": "#fbbf24",
            "warn_tx": "#fef3c7",
            "info_bg": "#0c4a6e",
            "info_bd": "#38bdf8",
            "info_tx": "#e0f2fe",
            "bad_bg": "#450a0a",
            "bad_bd": "#f87171",
            "bad_tx": "#fecaca",
            "input_bg": "#0f141b",
            "input_border": "#3d4a5c",
            "sidebar_bg": "#0d1218",
            "shadow": "0 8px 28px rgba(0,0,0,0.45)",
            "metric_bg": "linear-gradient(160deg,#171e27 0%,#12181f 100%)",
            "table_bg": "#12181f",
            "table_header": "#1a2330",
            "widget_label": "#e2e8f0",
            "secondary_btn_bg": "#1e293b",
            "secondary_btn_tx": "#f1f5f9",
            "checkbox": "#e2e8f0",
            "code_bg": "#0f141b",
        }
    return {
        "bg": "#f8fafc",
        "bg2": "#ffffff",
        "card": "#ffffff",
        "border": "#e2e8f0",
        "text": "#0f172a",
        "text2": "#64748b",
        "muted": "#64748b",
        "primary": "#e11d48",
        "primary_hover": "#be123c",
        "primary_soft": "#ffe4e6",
        "header": "#be123c",
        "success_bg": "#dcfce7",
        "success_bd": "#16a34a",
        "success_tx": "#14532d",
        "warn_bg": "#fef3c7",
        "warn_bd": "#f59e0b",
        "warn_tx": "#78350f",
        "info_bg": "#e0f2fe",
        "info_bd": "#0284c7",
        "info_tx": "#0c4a6e",
        "bad_bg": "#fee2e2",
        "bad_bd": "#dc2626",
        "bad_tx": "#7f1d1d",
        "input_bg": "#ffffff",
        "input_border": "#cbd5e1",
        "sidebar_bg": "#fff1f2",
        "shadow": "0 6px 20px rgba(15,23,42,0.07)",
        "metric_bg": "linear-gradient(160deg,#fff1f2 0%,#ffe4e6 100%)",
        "table_bg": "#ffffff",
        "table_header": "#f1f5f9",
        "widget_label": "#0f172a",
        "secondary_btn_bg": "#f1f5f9",
        "secondary_btn_tx": "#0f172a",
        "checkbox": "#0f172a",
        "code_bg": "#f1f5f9",
    }


def inject_theme_css():
    dark = is_dark()
    p = _palette(dark)
    css = f"""
<style>
/* ========== Base surfaces ========== */
html, body, [data-testid="stAppViewContainer"], .stApp,
section.main, section.main > div {{
    background-color: {p["bg"]} !important;
    color: {p["text"]} !important;
}}
[data-testid="stHeader"] {{
    background: {p["bg2"]} !important;
    border-bottom: 1px solid {p["border"]};
}}
[data-testid="stSkeleton"] {{ background: {p["bg2"]} !important; }}

/* ========== Global text — force readable contrast ========== */
.stApp, .stApp p, .stApp span, .stApp label, .stApp li,
.stApp .stMarkdown, .stApp .stMarkdown p, .stApp .stMarkdown li,
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] span,
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stWidgetLabel"] label,
.stApp [data-testid="stWidgetLabel"] span,
.stApp label[data-testid="stWidgetLabel"],
.stApp .stTextInput label, .stApp .stNumberInput label,
.stApp .stSelectbox label, .stApp .stTextArea label,
.stApp .stDateInput label, .stApp .stMultiSelect label,
.stApp .stRadio label, .stApp .stCheckbox label,
.stApp .stColorPicker label, .stApp .stFileUploader label,
.stApp [data-baseweb="form-control-label"],
.stApp [data-testid="stForm"] label,
.stApp [data-testid="stForm"] p {{
    color: {p["text"]} !important;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    color: {p["text"]} !important;
}}
.stApp [data-testid="stCaption"], .stApp .stCaption,
.stApp small, .stApp .stMarkdown small {{
    color: {p["text2"]} !important;
}}
.stApp strong, .stApp b {{ color: {p["text"]} !important; }}

/* ========== Sidebar ========== */
section[data-testid="stSidebar"] {{
    background: {p["sidebar_bg"]} !important;
    border-right: 1px solid {p["border"]};
}}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
    color: {p["text"]} !important;
}}
section[data-testid="stSidebar"] [data-testid="stCaption"] {{
    color: {p["text2"]} !important;
}}

.main .block-container {{
    padding-top: 1.15rem !important;
    padding-bottom: 3rem !important;
    max-width: 1280px;
    background: transparent !important;
}}

/* ========== Inputs (high contrast) ========== */
.stApp .stTextInput input,
.stApp .stNumberInput input,
.stApp .stTextArea textarea,
.stApp div[data-baseweb="input"],
.stApp div[data-baseweb="input"] > div,
.stApp div[data-baseweb="input"] input,
.stApp div[data-baseweb="textarea"],
.stApp div[data-baseweb="textarea"] textarea,
.stApp .stSelectbox [data-baseweb="select"] > div,
.stApp .stMultiSelect [data-baseweb="select"] > div,
.stApp .stDateInput input {{
    background-color: {p["input_bg"]} !important;
    color: {p["text"]} !important;
    border-color: {p["input_border"]} !important;
    border-radius: 10px !important;
    caret-color: {p["text"]} !important;
}}
.stApp .stTextInput input::placeholder,
.stApp .stTextArea textarea::placeholder,
.stApp input::placeholder, .stApp textarea::placeholder {{
    color: {p["muted"]} !important;
    opacity: 0.85 !important;
}}
.stApp .stNumberInput button {{
    background: {p["secondary_btn_bg"]} !important;
    color: {p["text"]} !important;
    border-color: {p["border"]} !important;
}}
.stApp [data-baseweb="popover"],
.stApp [data-baseweb="menu"],
.stApp ul[role="listbox"],
.stApp li[role="option"] {{
    background-color: {p["card"]} !important;
    color: {p["text"]} !important;
}}
.stApp li[role="option"]:hover,
.stApp li[aria-selected="true"] {{
    background-color: {p["primary_soft"]} !important;
    color: {p["text"]} !important;
}}
.stApp .stCheckbox label span,
.stApp .stRadio label span,
.stApp [data-testid="stCheckbox"] label,
.stApp [data-testid="stRadio"] label {{
    color: {p["checkbox"]} !important;
}}

/* ========== Buttons ========== */
.stApp .stButton > button,
.stApp .stFormSubmitButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    min-height: 2.65rem;
    color: {p["secondary_btn_tx"]} !important;
    background: {p["secondary_btn_bg"]} !important;
    border: 1px solid {p["border"]} !important;
}}
.stApp .stButton > button[kind="primary"],
.stApp .stFormSubmitButton > button[kind="primary"],
.stApp button[data-testid="baseButton-primary"],
.stApp button[kind="primary"] {{
    background: {p["primary"]} !important;
    border-color: {p["primary"]} !important;
    color: #ffffff !important;
}}
.stApp .stButton > button[kind="secondary"],
.stApp button[data-testid="baseButton-secondary"] {{
    background: {p["secondary_btn_bg"]} !important;
    color: {p["text"]} !important;
    border: 1px solid {p["border"]} !important;
}}

/* ========== Metrics ========== */
.stApp [data-testid="stMetric"] {{
    background: {p["metric_bg"]};
    border: 1px solid {p["border"]};
    border-radius: 14px;
    padding: 0.85rem 1rem;
    box-shadow: {p["shadow"]};
}}
.stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stMetricLabel"] p {{
    color: {p["text2"]} !important;
}}
.stApp [data-testid="stMetricValue"],
.stApp [data-testid="stMetricValue"] * {{
    font-size: clamp(1.1rem, 2.4vw, 1.5rem) !important;
    color: {p["text"]} !important;
    font-weight: 700 !important;
}}
.stApp [data-testid="stMetricDelta"] {{
    color: {p["text2"]} !important;
}}

/* ========== Tabs ========== */
.stApp button[data-baseweb="tab"] {{
    font-weight: 600 !important;
    color: {p["text2"]} !important;
    background: transparent !important;
}}
.stApp button[data-baseweb="tab"][aria-selected="true"] {{
    color: {p["primary"]} !important;
}}
.stApp [data-baseweb="tab-highlight"] {{
    background-color: {p["primary"]} !important;
}}
.stApp [data-baseweb="tab-border"] {{
    background-color: {p["border"]} !important;
}}

/* ========== Expander / bordered containers / forms ========== */
.stApp [data-testid="stExpander"] {{
    background: {p["card"]} !important;
    border: 1px solid {p["border"]} !important;
    border-radius: 12px;
}}
.stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] summary span,
.stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stExpander"] p,
.stApp .streamlit-expanderHeader,
.stApp .streamlit-expanderHeader span,
.stApp .streamlit-expanderHeader p {{
    color: {p["text"]} !important;
}}
.stApp .streamlit-expanderContent,
.stApp .streamlit-expanderContent p,
.stApp .streamlit-expanderContent span,
.stApp .streamlit-expenderContent div {{
    color: {p["text"]} !important;
}}
.stApp .streamlit-expanderHeader:hover {{
    background: {p["bg2"]} !important;
}}
.stApp div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {p["card"]} !important;
    border-color: {p["border"]} !important;
    border-radius: 14px !important;
    box-shadow: {p["shadow"]};
}}
.stApp [data-testid="stForm"] {{
    background: {p["card"]} !important;
    border: 1px solid {p["border"]} !important;
    border-radius: 14px !important;
    padding: 0.5rem 0.25rem;
}}

/* ========== Dataframe / table ========== */
.stApp [data-testid="stDataFrame"],
.stApp [data-testid="stDataFrameResizable"] {{
    border-radius: 12px;
    border: 1px solid {p["border"]};
    background: {p["table_bg"]} !important;
}}
.stApp [data-testid="stDataFrame"] *,
.stApp [data-testid="stDataFrameResizable"] * {{
    color: {p["text"]} !important;
}}
/* glamor / glide data grid cells often use canvas — border only */
/* DataFrame show more/less and toolbar */
.stApp [data-testid="stDataFrame"] button,
.stApp [data-testid="stDataFrameResizable"] button,
.stApp [data-testid="stDataFrame"] [role="button"],
.stApp [data-testid="stDataFrameResizable"] [role="button"] {{
    color: {p["text"]} !important;
    background: {p["secondary_btn_bg"]} !important;
    border-color: {p["border"]} !important;
}}
/* Arrow / chevron icons in expanders and show-more */
.stApp svg[stroke],
.stApp [data-testid="stExpander"] svg,
.stApp .streamlit-expanderHeader svg {{
    fill: {p["text"]} !important;
    stroke: {p["text"]} !important;
}}

/* ========== Alerts ========== */
.stApp div[data-testid="stAlert"] {{
    border-radius: 12px !important;
}}
.stApp div[data-testid="stAlert"] p,
.stApp div[data-testid="stAlert"] span {{
    color: inherit !important;
}}

/* ========== Dividers ========== */
.stApp hr {{ border-color: {p["border"]} !important; opacity: 1; }}

/* ========== Code / JSON ========== */
.stApp code, .stApp pre, .stApp [data-testid="stCode"] {{
    background: {p["code_bg"]} !important;
    color: {p["text"]} !important;
    border-radius: 8px;
}}

/* ========== File uploader ========== */
.stApp [data-testid="stFileUploader"] section,
.stApp [data-testid="stFileUploaderDropzone"] {{
    background: {p["input_bg"]} !important;
    border-color: {p["input_border"]} !important;
    color: {p["text"]} !important;
}}
.stApp [data-testid="stFileUploader"] * {{
    color: {p["text"]} !important;
}}

/* ========== Color picker label ========== */
.stApp .stColorPicker label, .stApp .stColorPicker p {{
    color: {p["widget_label"]} !important;
}}

/* ========== Links ========== */
.stApp a {{ color: {p["primary"]} !important; }}
.stApp a.streamlit-expanderHeader,
.stApp .streamlit-expanderHeader a,
.stApp [data-testid="stMarkdownContainer"] a,
.stApp [data-testid="stMarkdownContainer"] a span,
.stApp .stMarkdown a,
.stApp .stMarkdown a span {{
    color: {p["primary"]} !important;
    text-decoration-color: {p["primary"]} !important;
}}
.stApp span[style*="cursor: pointer"],
.stApp div[role="button"] span {{
    color: {p["text"]} !important;
}}

/* ========== Custom classes ========== */
.main-header {{
    font-size: clamp(1.3rem, 4vw, 1.85rem);
    font-weight: 800;
    color: {p["header"]} !important;
    margin-bottom: 0.3rem;
    letter-spacing: -0.02em;
}}
.sub-header {{
    color: {p["text2"]} !important;
    font-size: 0.95rem;
    margin-bottom: 0.9rem;
}}
.alert-box {{
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 8px;
    font-size: 0.95rem;
    line-height: 1.45;
}}
.alert-warn {{ background:{p["warn_bg"]}; border-left:4px solid {p["warn_bd"]}; color:{p["warn_tx"]} !important; }}
.alert-ok {{ background:{p["success_bg"]}; border-left:4px solid {p["success_bd"]}; color:{p["success_tx"]} !important; }}
.alert-info {{ background:{p["info_bg"]}; border-left:4px solid {p["info_bd"]}; color:{p["info_tx"]} !important; }}
.alert-bad {{ background:{p["bad_bg"]}; border-left:4px solid {p["bad_bd"]}; color:{p["bad_tx"]} !important; }}
.login-card {{
    background: {p["card"]};
    border: 1px solid {p["border"]};
    border-radius: 18px;
    padding: 1.4rem 1.2rem 1.2rem;
    box-shadow: {p["shadow"]};
    color: {p["text"]};
}}
.login-card * {{ color: {p["text"]} !important; }}
.theme-badge {{
    display: inline-block;
    font-size: 0.72rem;
    padding: 3px 10px;
    border-radius: 999px;
    background: {p["primary_soft"]};
    color: {p["primary"]} !important;
    font-weight: 700;
}}
.pct-card {{
    border-radius: 14px;
    padding: 16px 12px;
    text-align: center;
    min-height: 110px;
    box-shadow: {p["shadow"]};
}}
.balance-ok {{
    background: {p["success_bg"]};
    border: 1px solid {p["success_bd"]};
    color: {p["success_tx"]} !important;
    padding: 12px;
    border-radius: 10px;
    font-weight: 600;
}}
.balance-bad {{
    background: {p["bad_bg"]};
    border: 1px solid {p["bad_bd"]};
    color: {p["bad_tx"]} !important;
    padding: 12px;
    border-radius: 10px;
    font-weight: 600;
}}
.stock-card, .cat-card {{
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 0.4rem;
}}
.stock-card .lbl, .cat-card .lbl {{ color: {p["muted"]} !important; font-size: 0.9rem; }}
.stock-card .val, .cat-card .val {{
    color: {p["text"]} !important;
    font-size: clamp(1.3rem, 3vw, 1.8rem);
    font-weight: 700;
}}

iframe[height="0"] {{
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    border: 0 !important;
    visibility: hidden !important;
    pointer-events: none !important;
}}

@media (max-width: 768px) {{
    .main .block-container {{
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        padding-top: 0.7rem !important;
    }}
    .stApp [data-testid="stMetric"] {{
        padding: 0.6rem 0.7rem;
        margin-bottom: 0.3rem;
    }}
    .stApp [data-testid="stMetricValue"] {{ font-size: 1.1rem !important; }}
    .stApp [data-baseweb="tab-list"] {{
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }}
    .stApp button[data-baseweb="tab"] {{
        white-space: nowrap;
        font-size: 0.82rem !important;
    }}
    .stApp .stButton > button, .stApp .stFormSubmitButton > button {{
        width: 100%;
        min-height: 2.85rem;
    }}
    .login-card {{ padding: 1.1rem 0.95rem; }}
    .main-header {{ font-size: 1.3rem !important; }}
}}
@media (min-width: 769px) and (max-width: 1100px) {{
    .main .block-container {{
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }}
}}
footer {{ visibility: hidden; height: 0; }}
#MainMenu {{ visibility: hidden; }}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def _sync_theme_from_widgets():
    for k, val in list(st.session_state.items()):
        if not isinstance(k, str) or "theme_mode" not in k:
            continue
        if not isinstance(val, str):
            continue
        if "Dark" in val:
            st.session_state[THEME_KEY] = "dark"
            return
        if "Light" in val:
            st.session_state[THEME_KEY] = "light"
            return


def apply_theme():
    if THEME_KEY not in st.session_state:
        st.session_state[THEME_KEY] = "light"
    _sync_theme_from_widgets()
    # CSS first (synchronous, no iframe delay — eliminates flash)
    st.markdown(_early_paint_css(), unsafe_allow_html=True)
    inject_theme_css()
    # JS backup for localStorage persistence (runs in iframe, after CSS)
    _early_paint_js()
    _persist_theme_js(get_theme_mode())


def safe_download_button(label, data, file_name, mime="application/octet-stream", key=None, **kwargs):
    """Wrapper for st.download_button that prevents IDM auto-detect.

    Shows a trigger button first; the actual download button only appears after click.
    """
    trigger_key = f"_dl_trigger_{key}" if key else f"_dl_trigger_{id(data)}"
    if trigger_key not in st.session_state:
        st.session_state[trigger_key] = False

    if not st.session_state[trigger_key]:
        if st.button(f"📥 {label}", key=f"_dl_btn_{key}" if key else None, **kwargs):
            st.session_state[trigger_key] = True
            st.rerun()
    else:
        st.download_button(label, data, file_name, mime, key=key, **kwargs)
        if st.button("✖ Tutup", key=f"_dl_close_{key}" if key else None):
            st.session_state[trigger_key] = False
            st.rerun()


def page_header(title: str, caption: str = ""):
    st.markdown(f'<p class="main-header">{title}</p>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<p class="sub-header">{caption}</p>', unsafe_allow_html=True)


def text_primary() -> str:
    return "#f1f5f9" if is_dark() else "#0f172a"


def text_muted() -> str:
    return "#94a3b8" if is_dark() else "#64748b"
