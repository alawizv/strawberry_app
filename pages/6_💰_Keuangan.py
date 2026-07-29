"""Modul Keuangan — pemasukan penjualan & pengeluaran + log + export."""
import io
from datetime import date

import pandas as pd
import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import get_db, Sale, Expense, write_log
from ui_theme import safe_download_button

st.set_page_config(page_title="Keuangan", page_icon="💰", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## 💰 Keuangan")
st.caption("Pemasukan dari penjualan & pengeluaran operasional")

EXPENSE_CATS = ["shipping", "labor", "packaging", "fuel", "farm", "other"]

db = get_db()
try:
    today = date.today()
    f1, f2 = st.columns(2)
    with f1:
        start = st.date_input("Dari", value=today.replace(day=1), key="fin_start")
    with f2:
        end = st.date_input("Sampai", value=today, key="fin_end")

    sales = db.query(Sale).filter(Sale.sale_date >= start, Sale.sale_date <= end, Sale.status != "cancelled").all()
    expenses = db.query(Expense).filter(Expense.expense_date >= start, Expense.expense_date <= end).all()
    rev = sum(s.total_amount or 0 for s in sales)
    exp = sum(e.amount or 0 for e in expenses)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pendapatan", f"Rp {rev:,.0f}")
    c2.metric("Pengeluaran", f"Rp {exp:,.0f}")
    c3.metric("Laba kotor", f"Rp {rev - exp:,.0f}")

    tab_inc, tab_exp, tab_add = st.tabs(["Pemasukan", "Pengeluaran", "Input Pengeluaran"])

    with tab_inc:
        if sales:
            df = pd.DataFrame([{
                "ID": s.id, "Tanggal": str(s.sale_date),
                "Pelanggan": s.customer.name if s.customer else "-", "Status": s.status,
                "Subtotal": s.subtotal, "Diskon": s.discount_amount, "Ongkir": s.shipping_cost, "Total": s.total_amount,
            } for s in sales])
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8")
            xlsx_buf = io.BytesIO()
            df.to_excel(xlsx_buf, index=False, engine="openpyxl")
            xlsx_buf.seek(0)
            c_csv, c_xlsx = st.columns(2)
            with c_csv:
                safe_download_button("Export Pemasukan CSV", csv, "pemasukan.csv", "text/csv", key="inc_csv")
            with c_xlsx:
                safe_download_button("Export Pemasukan Excel", xlsx_buf, "pemasukan.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="inc_xlsx")
        else:
            st.info("Belum ada penjualan di periode ini.")

    with tab_exp:
        all_exp = db.query(Expense).filter(Expense.expense_date >= start, Expense.expense_date <= end).order_by(Expense.expense_date.desc()).all()
        if all_exp:
            df = pd.DataFrame([{
                "ID": e.id, "Tanggal": str(e.expense_date), "Kategori": e.category,
                "Jumlah": e.amount, "Deskripsi": e.description or "", "Sale#": e.related_sale_id or "", "Oleh": e.created_by or "",
            } for e in all_exp])
            st.dataframe(df, use_container_width=True, hide_index=True)
            by_cat = df.groupby("Kategori")["Jumlah"].sum().reset_index()
            st.bar_chart(by_cat.set_index("Kategori"))

            csv = df.to_csv(index=False).encode("utf-8")
            xlsx_buf = io.BytesIO()
            df.to_excel(xlsx_buf, index=False, engine="openpyxl")
            xlsx_buf.seek(0)
            c_csv, c_xlsx = st.columns(2)
            with c_csv:
                safe_download_button("Export Pengeluaran CSV", csv, "pengeluaran.csv", "text/csv", key="exp_csv")
            with c_xlsx:
                safe_download_button("Export Pengeluaran Excel", xlsx_buf, "pengeluaran.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="exp_xlsx")

            st.subheader("Hapus Pengeluaran (Owner)")
            del_opts = {f"#{e.id} {e.category} Rp {e.amount:,.0f} — {e.description or '-'}": e.id for e in all_exp}
            del_sel = st.selectbox("Pilih", list(del_opts.keys()), key="del_exp")
            if st.button("Hapus pengeluaran", type="secondary"):
                eid = del_opts[del_sel]
                e = db.get(Expense, eid)
                if e:
                    write_log(db, user, "expense.delete", f"Hapus pengeluaran #{eid}: {e.category} Rp {e.amount:,.0f}",
                              entity_type="expense", entity_id=eid)
                    db.delete(e)
                    db.commit()
                    flash_success("Pengeluaran dihapus.")
                    st.rerun()
        else:
            st.info("Belum ada pengeluaran di periode ini.")

    with tab_add:
        with st.form("exp_form"):
            edate = st.date_input("Tanggal", value=today)
            cat = st.selectbox("Kategori", EXPENSE_CATS)
            amount = st.number_input("Jumlah (Rp)", min_value=0.0, value=0.0, step=1000.0)
            desc = st.text_input("Deskripsi")
            if st.form_submit_button("Simpan", type="primary"):
                if amount <= 0:
                    st.error("Jumlah harus > 0.")
                else:
                    db.add(Expense(expense_date=edate, category=cat, amount=float(amount),
                        description=desc or None, created_by=user["name"]))
                    write_log(db, user, "expense.create", f"Pengeluaran {cat}: Rp {amount:,.0f} — {desc or '-'}",
                              entity_type="expense")
                    db.commit()
                    flash_success("Pengeluaran tersimpan.")
                    st.rerun()
finally:
    db.close()
