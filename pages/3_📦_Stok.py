"""Modul Stok Bahan — adjustment hanya Sorter (approve Owner)."""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import (
    get_db, Category, InventoryMovement, get_stock_by_name, write_log, ChangeRequest,
)
from ui_theme import is_dark, text_primary, text_muted

st.set_page_config(page_title="Stok", page_icon="📦", layout="wide")
user = require_login(["owner", "admin", "driver", "sorter", "sales"])
show_user_sidebar()

st.markdown("## 📦 Stok Bahan")
st.caption("Stok real-time per kategori sortir")

is_owner = user["role"] in ("owner", "admin")
is_sorter = user["role"] == "sorter"

db = get_db()
try:
    stocks = get_stock_by_name(db)
    cats = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()
    cat_map = {c.name: c for c in cats}

    if stocks:
        cols = st.columns(max(len(stocks), 1))
        muted = text_muted()
        val_c = text_primary()
        for i, (name, kg) in enumerate(stocks.items()):
            with cols[i]:
                color = cat_map[name].color if name in cat_map else "#64748b"
                st.markdown(
                    f"""
                    <div class="stock-card" style="background:{color}22;border-left:4px solid {color};">
                        <div class="lbl">{name}</div>
                        <div class="val" style="color:{val_c} !important;">{kg:g} kg</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.metric("Total Stok", f"{sum(stocks.values()):g} kg")
    else:
        st.info("Belum ada stok. Lakukan penerimaan & sortir terlebih dahulu.")

    st.divider()
    st.subheader("Riwayat Mutasi Stok")
    TYPE_LABEL = {
        "in_sorting": "Masuk · Sortir (in_sorting)",
        "out_sale": "Keluar · Penjualan (out_sale)",
        "adjustment": "Penyesuaian (adjustment)",
        "in_return": "Masuk · Retur jual (in_return)",
    }
    st.caption(
        "Qty **+** = stok naik · **−** = stok turun. "
        "`out_sale` hanya muncul setelah order **confirmed**. "
        "`adjustment` setelah owner terapkan/approve."
    )

    movements = (
        db.query(InventoryMovement)
        .order_by(InventoryMovement.created_at.desc())
        .limit(200)
        .all()
    )
    if movements:
        f1, f2 = st.columns(2)
        type_opts = ["Semua"] + sorted({m.movement_type for m in movements if m.movement_type})
        with f1:
            filt_type = st.selectbox("Filter tipe", type_opts, key="mut_type")
        with f2:
            filt_dir = st.selectbox("Filter arah", ["Semua", "Masuk (+)", "Keluar (−)"], key="mut_dir")

        filtered = movements
        if filt_type != "Semua":
            filtered = [m for m in filtered if m.movement_type == filt_type]
        if filt_dir == "Masuk (+)":
            filtered = [m for m in filtered if (m.qty_kg or 0) > 0]
        elif filt_dir == "Keluar (−)":
            filtered = [m for m in filtered if (m.qty_kg or 0) < 0]

        data = [{
            "Waktu": str(m.created_at)[:19] if m.created_at else "-",
            "Kategori": m.category.name if m.category else m.category_id,
            "Tipe": TYPE_LABEL.get(m.movement_type, m.movement_type),
            "Arah": "Masuk" if (m.qty_kg or 0) >= 0 else "Keluar",
            "Qty kg": m.qty_kg,
            "Ref": f"{m.ref_type or '-'}#{m.ref_id or '-'}",
            "Oleh": m.created_by or "-",
            "Catatan": m.notes or "",
        } for m in filtered]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        if not filtered:
            st.warning("Tidak ada baris untuk filter ini. Coba 'Semua' — mungkin belum ada penjualan confirmed / adjustment.")
        counts = {}
        for m in movements:
            counts[m.movement_type] = counts.get(m.movement_type, 0) + 1
        st.caption("Jumlah per tipe (semua data, max 200): " + ", ".join(
            f"**{TYPE_LABEL.get(k, k)}** = {v}" for k, v in sorted(counts.items())
        ))
    else:
        st.info("Belum ada mutasi stok.")

    st.divider()
    st.subheader("Penyesuaian Stok (Adjustment)")
    st.caption(
        "**Sorter** mengajukan → Owner approve. "
        "**Owner** boleh langsung terapkan (tanpa approve) · **wajib log**. Role lain tidak bisa."
    )

    if is_owner and cats:
        with st.form("adj_owner_direct"):
            st.markdown("**Owner — terapkan langsung**")
            cat = st.selectbox("Kategori", cats, format_func=lambda c: c.name, key="own_adj_cat")
            qty = st.number_input("Qty kg (+ tambah / - kurangi)", value=0.0, step=1.0, format="%.1f", key="own_adj_qty")
            notes = st.text_input("Alasan *", key="own_adj_notes")
            if st.form_submit_button("Terapkan Adjustment (langsung)", type="primary"):
                if qty == 0:
                    st.error("Qty tidak boleh 0.")
                elif not (notes or "").strip():
                    st.error("Alasan wajib diisi.")
                else:
                    db.add(InventoryMovement(
                        category_id=cat.id,
                        movement_type="adjustment",
                        qty_kg=float(qty),
                        ref_type="adjustment",
                        notes=notes.strip(),
                        created_by=user["name"],
                    ))
                    write_log(
                        db, user, "stock.adjust_direct",
                        f"Owner adjustment langsung {cat.name}: {qty:g} kg — {notes.strip()}",
                        entity_type="category", entity_id=cat.id,
                        detail=json.dumps({"category": cat.name, "qty_kg": float(qty), "notes": notes.strip()}),
                    )
                    db.commit()
                    flash_success(f"✅ Stok {cat.name} disesuaikan {qty:g} kg (owner langsung).")
                    st.rerun()

    if is_sorter and cats:
        with st.form("adj_form"):
            st.markdown("**Sorter — ajukan ke Owner**")
            cat = st.selectbox("Kategori", cats, format_func=lambda c: c.name)
            qty = st.number_input("Qty kg (+ tambah / - kurangi)", value=0.0, step=1.0, format="%.1f")
            notes = st.text_input("Alasan *")
            if st.form_submit_button("Ajukan Adjustment (butuh approve Owner)", type="primary"):
                if qty == 0:
                    st.error("Qty tidak boleh 0.")
                elif not (notes or "").strip():
                    st.error("Alasan wajib diisi.")
                else:
                    payload = {
                        "category_id": cat.id,
                        "category_name": cat.name,
                        "qty_kg": float(qty),
                        "notes": notes.strip(),
                    }
                    cr = ChangeRequest(
                        entity_type="stock_adjustment",
                        entity_id=cat.id,
                        request_type="adjust",
                        payload=json.dumps(payload),
                        reason=notes.strip(),
                        status="pending",
                        requested_by_id=user["id"],
                        requested_by_name=user["name"],
                    )
                    db.add(cr)
                    db.flush()
                    write_log(
                        db, user, "stock.adjust_request",
                        f"Ajukan adjustment {cat.name}: {qty:g} kg — {notes.strip()}",
                        entity_type="change_request", entity_id=cr.id,
                        detail=json.dumps(payload),
                    )
                    db.commit()
                    flash_success(f"📤 Adjustment {cat.name} {qty:g} kg diajukan. Menunggu owner.")
                    st.rerun()
    elif not is_owner and not is_sorter:
        st.info("Anda tidak bisa adjustment. Hanya **Sorter** (ajukan) atau **Owner** (langsung / approve).")

    if is_owner:
        st.subheader("Approve Adjustment (Owner)")
        pending = (
            db.query(ChangeRequest)
            .filter(
                ChangeRequest.status == "pending",
                ChangeRequest.entity_type == "stock_adjustment",
            )
            .order_by(ChangeRequest.created_at.asc())
            .all()
        )
        if not pending:
            st.info("Tidak ada adjustment pending dari sorter.")
        else:
            for r in pending:
                payload = json.loads(r.payload) if r.payload else {}
                with st.container(border=True):
                    st.markdown(
                        f"**#{r.id}** {payload.get('category_name', '?')} · "
                        f"**{payload.get('qty_kg', 0):g} kg** — oleh {r.requested_by_name}"
                    )
                    st.write(f"Alasan: {r.reason}")
                    st.caption(str(r.created_at)[:19])
                    a1, a2 = st.columns(2)
                    with a1:
                        if st.button("Approve & Terapkan", key=f"ap_adj_{r.id}", type="primary"):
                            cid = int(payload["category_id"])
                            qty = float(payload["qty_kg"])
                            db.add(InventoryMovement(
                                category_id=cid,
                                movement_type="adjustment",
                                qty_kg=qty,
                                ref_type="adjustment",
                                ref_id=r.id,
                                notes=payload.get("notes") or r.reason,
                                created_by=user["name"],
                            ))
                            r.status = "approved"
                            r.reviewed_by_id = user["id"]
                            r.reviewed_by_name = user["name"]
                            r.reviewed_at = datetime.utcnow()
                            write_log(
                                db, user, "stock.adjust_approve",
                                f"Approve adjustment {payload.get('category_name')}: {qty:g} kg",
                                entity_type="change_request", entity_id=r.id,
                                detail=r.payload,
                            )
                            db.commit()
                            flash_success(
                                f"✅ Adjustment diterapkan: {payload.get('category_name')} {qty:g} kg"
                            )
                            st.rerun()
                    with a2:
                        if st.button("Tolak", key=f"rj_adj_{r.id}"):
                            r.status = "rejected"
                            r.reviewed_by_id = user["id"]
                            r.reviewed_by_name = user["name"]
                            r.reviewed_at = datetime.utcnow()
                            write_log(
                                db, user, "stock.adjust_reject",
                                f"Tolak adjustment #{r.id}",
                                entity_type="change_request", entity_id=r.id,
                            )
                            db.commit()
                            flash_success(f"Adjustment #{r.id} ditolak.", balloons=False)
                            st.rerun()
finally:
    db.close()
