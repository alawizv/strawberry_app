"""Log aktivitas — semua proses, untuk multi-owner audit."""
import streamlit as st
import pandas as pd

from auth_utils import require_login, show_user_sidebar
from database import get_db, ActivityLog

st.set_page_config(page_title="Log Aktivitas", page_icon="📋", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## 📋 Log Aktivitas")
st.caption("Audit trail semua proses (cocok untuk 2 owner / partner)")

st.info(
    "**Kolom Detail** = data teknis tambahan di balik ringkasan, "
    "misalnya payload JSON (resep, qty adjustment, field yang diubah). "
    "Bukan aksi terpisah — pelengkap **Ringkasan** agar bisa audit / debug.\n\n"
    "🔒 **Log bersifat permanen** — tidak ada fitur hapus log (audit multi-owner)."
)

db = get_db()
try:
    q = db.query(ActivityLog).order_by(ActivityLog.created_at.desc())
    action_filter = st.text_input("Filter action (opsional)", placeholder="mis. receiving.create")
    if action_filter.strip():
        q = q.filter(ActivityLog.action.contains(action_filter.strip()))
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
            "Detail": (l.detail or "")[:200],
        } for l in logs])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Baca detail penuh")
        opts = {
            f"#{l.id} {str(l.created_at)[:19]} · {l.action} · {l.summary[:40]}": l.id
            for l in logs if l.detail
        }
        if opts:
            sel = st.selectbox("Pilih log", list(opts.keys()))
            log = db.get(ActivityLog, opts[sel])
            if log:
                st.code(log.detail or "(kosong)", language="json")
        else:
            st.caption("Belum ada log yang punya detail ekstra.")
finally:
    db.close()
