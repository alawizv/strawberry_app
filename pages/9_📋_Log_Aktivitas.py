"""Log aktivitas — audit trail, diff before/after, export."""
import json
import io
from datetime import date

import streamlit as st
import pandas as pd

from auth_utils import require_login, show_user_sidebar
from database import get_db, ActivityLog, format_diff
from ui_theme import safe_download_button

st.set_page_config(page_title="Log Aktivitas", page_icon="📋", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## 📋 Log Aktivitas")
st.caption("Audit trail semua proses — dengan detail perubahan before/after")

st.info("🔒 **Log bersifat permanen** — tidak ada fitur hapus log (audit multi-owner).")

db = get_db()
try:
    f1, f2, f3 = st.columns(3)
    with f1:
        # Collect distinct actions from recent logs for dropdown
        recent_actions = db.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()
        action_options = ["Semua"] + [a[0] for a in recent_actions if a[0]]
        action_choice = st.selectbox("Filter action", action_options, key="log_action_filter")
    with f2:
        user_filter = st.text_input("Filter user", placeholder="mis. owner")
    with f3:
        date_filter = st.date_input("Dari tanggal", value=None, key="log_date")

    q = db.query(ActivityLog).order_by(ActivityLog.created_at.desc())
    if action_choice != "Semua":
        q = q.filter(ActivityLog.action == action_choice)
    if user_filter.strip():
        q = q.filter(ActivityLog.user_name.contains(user_filter.strip()))
    if date_filter:
        q = q.filter(ActivityLog.created_at >= date_filter)
    logs = q.limit(300).all()

    if not logs:
        st.info("Belum ada log.")
    else:
        df = pd.DataFrame([{
            "Waktu": str(l.created_at)[:19] if l.created_at else "-",
            "User": l.user_name or l.username or "-",
            "Role": l.role or "-",
            "Action": l.action,
            "Entity": f"{l.entity_type or '-'}#{l.entity_id or '-'}",
            "Ringkasan": l.summary,
            "Detail": "Ya" if l.detail else "-",
        } for l in logs])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("🔍 Detail Perubahan (Audit Diff)")
        opts = {f"#{l.id} {str(l.created_at)[:19]} · {l.action} · {l.summary[:40]}": l.id for l in logs}
        sel = st.selectbox("Pilih log", list(opts.keys()))
        log = db.get(ActivityLog, opts[sel])
        if log:
            st.markdown(f"**Ringkasan:** {log.summary}")
            st.caption(f"Waktu: {log.created_at} · User: {log.user_name} ({log.role}) · Entity: {log.entity_type}#{log.entity_id}")

            if log.detail:
                try:
                    detail = json.loads(log.detail)
                    if isinstance(detail, dict) and "before" in detail and "after" in detail:
                        before = detail["before"]
                        after = detail["after"]

                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Sebelum:**")
                            for k, v in before.items():
                                st.write(f"- {k}: `{v}`")
                        with c2:
                            st.markdown("**Sesudah:**")
                            for k, v in after.items():
                                changed = before.get(k) != v
                                icon = "🔴 " if changed else "  "
                                st.write(f"{icon}{k}: `{v}`")

                        diff_text = format_diff(before, after)
                        st.markdown("**Diff (yang berubah):**")
                        st.code(diff_text, language="diff")
                    else:
                        st.json(detail)
                except (json.JSONDecodeError, TypeError):
                    st.code(log.detail, language="text")
            else:
                st.caption("Tidak ada detail teknis.")

        st.divider()
        st.subheader("📥 Export Log")
        csv = df.to_csv(index=False).encode("utf-8")
        xlsx_buf = io.BytesIO()
        df.to_excel(xlsx_buf, index=False, engine="openpyxl")
        xlsx_buf.seek(0)
        c_csv, c_xlsx = st.columns(2)
        with c_csv:
            safe_download_button("Export Log CSV", csv, "log_aktivitas.csv", "text/csv", key="log_csv")
        with c_xlsx:
            safe_download_button("Export Log Excel", xlsx_buf, "log_aktivitas.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="log_xlsx")
finally:
    db.close()
