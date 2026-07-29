"""Modul Retur — pengembalian barang dari pelanggan."""
import json
from datetime import date, datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success, flash_error
from database import (
    get_db, Sale, SaleItem, Product, Customer,
    InventoryMovement, MovementType, ReturnOrder, ReturnItem,
    Category, write_log, format_rp,
)

st.set_page_config(page_title="Retur", page_icon="🔄", layout="wide")
user = require_login(["owner", "admin", "sales"])
show_user_sidebar()

st.markdown("## 🔄 Retur / Pengembalian")
st.caption("Kelola pengembalian barang dari pelanggan")

db = get_db()
try:
    is_owner = user["role"] in ("owner", "admin")

    if is_owner:
        tab_new, tab_list, tab_approve = st.tabs(["Buat Retur", "Riwayat Retur", "Approve Retur"])
    else:
        tab_new, tab_list = st.tabs(["Buat Retur", "Riwayat Retur"])
        tab_approve = None

    with tab_new:
        st.subheader("Ajukan Retur")
        sales = db.query(Sale).filter(
            Sale.status.in_(["confirmed", "shipped", "delivered"])
        ).order_by(Sale.created_at.desc()).limit(50).all()

        if not sales:
            st.info("Tidak ada order yang bisa diretur.")
        else:
            sale_opts = {f"#{s.id} {s.customer.name if s.customer else ''} — {format_rp(s.total_amount)} ({s.status})": s.id for s in sales}
            sel = st.selectbox("Pilih Order", list(sale_opts.keys()))
            sale = db.get(Sale, sale_opts[sel])

            if sale:
                st.write(f"Pelanggan: **{sale.customer.name if sale.customer else '-'}** · Tanggal: {sale.sale_date} · Status: {sale.status}")
                if sale.items:
                    st.dataframe([{
                        "Produk": it.product.name if it.product else "-",
                        "Qty kg": it.qty_kg, "Harga": format_rp(it.unit_price),
                    } for it in sale.items], use_container_width=True, hide_index=True)

                st.divider()
                cats = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()
                reason = st.text_area("Alasan Retur *")

                return_items = {}
                if cats:
                    cols = st.columns(len(cats))
                    for i, cat in enumerate(cats):
                        with cols[i]:
                            return_items[cat.id] = st.number_input(
                                f"{cat.name} (kg)", min_value=0.0, value=0.0, step=0.5, format="%.1f",
                                key=f"ret_{cat.id}",
                            )

                total_return = sum(return_items.values())
                st.metric("Total kg diretur", f"{total_return:g} kg")

                if st.button("Kirim Retur", type="primary", use_container_width=True):
                    if not reason.strip():
                        st.error("Alasan wajib diisi.")
                    elif total_return <= 0:
                        st.error("Minimal 1 kategori harus > 0 kg.")
                    else:
                        ret = ReturnOrder(
                            sale_id=sale.id, return_date=date.today(), reason=reason.strip(),
                            status="approved" if is_owner else "pending",
                            created_by_id=user["id"], created_by_name=user["name"],
                        )
                        db.add(ret)
                        db.flush()
                        for cat_id, kg in return_items.items():
                            if kg > 0:
                                db.add(ReturnItem(return_id=ret.id, category_id=cat_id, qty_kg=float(kg)))
                                if is_owner:
                                    db.add(InventoryMovement(
                                        category_id=cat_id, movement_type="in_return",
                                        qty_kg=float(kg), ref_type="return", ref_id=ret.id,
                                        notes=f"Retur sale #{sale.id}", created_by=user["name"],
                                    ))
                        write_log(db, user, "return.create" if not is_owner else "return.approve",
                            f"Retur sale #{sale.id}: {total_return:g} kg — {reason.strip()}",
                            entity_type="return", entity_id=ret.id,
                            detail=json.dumps({cat.name: return_items.get(cat.id, 0) for cat in cats if return_items.get(cat.id, 0) > 0}))
                        db.commit()
                        flash_success(f"Retur #{ret.id} tersimpan. Stok dikembalikan." if is_owner else f"Retur #{ret.id} diajukan. Menunggu owner.")
                        st.rerun()

    with tab_list:
        rets = db.query(ReturnOrder).order_by(ReturnOrder.created_at.desc()).limit(50).all()
        if not rets:
            st.info("Belum ada retur.")
        else:
            rows = []
            for r in rets:
                sale = db.get(Sale, r.sale_id)
                items_desc = ", ".join(f"{it.category.name}: {it.qty_kg:g}kg" for it in r.items if it.category)
                rows.append({
                    "ID": r.id, "Sale#": r.sale_id,
                    "Pelanggan": sale.customer.name if sale and sale.customer else "-",
                    "Alasan": r.reason[:50], "Status": r.status,
                    "Detail": items_desc, "Oleh": r.created_by_name or "-", "Tanggal": str(r.return_date),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

    if tab_approve is not None:
        with tab_approve:
            pending = db.query(ReturnOrder).filter_by(status="pending").order_by(ReturnOrder.created_at.asc()).all()
            if not pending:
                st.info("Tidak ada retur pending.")
            else:
                for r in pending:
                    sale = db.get(Sale, r.sale_id)
                    with st.container(border=True):
                        st.markdown(f"**Retur #{r.id}** — Sale #{r.sale_id} — {sale.customer.name if sale and sale.customer else '-'}")
                        st.write(f"Alasan: {r.reason}")
                        for it in r.items:
                            st.write(f"- {it.category.name if it.category else '?'}: {it.qty_kg:g} kg")
                        a1, a2 = st.columns(2)
                        with a1:
                            if st.button("Approve & Kembalikan Stok", key=f"ap_ret_{r.id}", type="primary"):
                                r.status = "approved"
                                r.reviewed_by_id = user["id"]
                                r.reviewed_by_name = user["name"]
                                r.reviewed_at = datetime.utcnow()
                                for it in r.items:
                                    db.add(InventoryMovement(
                                        category_id=it.category_id, movement_type="in_return",
                                        qty_kg=float(it.qty_kg), ref_type="return", ref_id=r.id,
                                        notes=f"Retur sale #{r.sale_id}", created_by=user["name"],
                                    ))
                                write_log(db, user, "return.approve", f"Approve retur #{r.id}", entity_type="return", entity_id=r.id)
                                db.commit()
                                flash_success(f"Retur #{r.id} disetujui. Stok dikembalikan.")
                                st.rerun()
                        with a2:
                            if st.button("Tolak", key=f"rj_ret_{r.id}"):
                                r.status = "rejected"
                                r.reviewed_by_id = user["id"]
                                r.reviewed_by_name = user["name"]
                                r.reviewed_at = datetime.utcnow()
                                write_log(db, user, "return.reject", f"Tolak retur #{r.id}", entity_type="return", entity_id=r.id)
                                db.commit()
                                flash_success(f"Retur #{r.id} ditolak.", balloons=False)
                                st.rerun()
finally:
    db.close()
