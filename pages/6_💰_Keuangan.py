"""Modul Keuangan — pemasukan penjualan & pengeluaran."""
from datetime import date

import pandas as pd
import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success
from database import get_db, Sale, Expense

st.set_page_config(page_title="Keuangan", page_icon="💰", layout="wide")
user = require_login(["owner", "admin"])
show_user_sidebar()

st.markdown("## 💰 Keuangan")
st.caption("Pemasukan dari penjualan & pengeluaran operasional")

EXPENSE_CATS = ["shipping", "labor", "packaging", "fuel", "farm", "other"]

db = get_db()
try:
    today = date.today()
    month_start = today.replace(day=1)

    sales = db.query(Sale).filter(Sale.sale_date >= month_start, Sale.status != "cancelled").all()
    expenses = db.query(Expense).filter(Expense.expense_date >= month_start).all()
    rev = sum(s.total_amount or 0 for s in sales)
    exp = sum(e.amount or 0 for e in expenses)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pendapatan bulan ini", f"Rp {rev:,.0f}")
    c2.metric("Pengeluaran bulan ini", f"Rp {exp:,.0f}")
    c3.metric("Laba kotor estimasi", f"Rp {rev - exp:,.0f}")

    tab_inc, tab_exp, tab_add = st.tabs(["Pemasukan", "Pengeluaran", "Input Pengeluaran"])

    with tab_inc:
        if sales:
            df = pd.DataFrame([{
                "ID": s.id,
                "Tanggal": str(s.sale_date),
                "Pelanggan": s.customer.name if s.customer else "-",
                "Status": s.status,
                "Subtotal": s.subtotal,
                "Diskon": s.discount_amount,
                "Ongkir": s.shipping_cost,
                "Total": s.total_amount,
            } for s in sales])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada penjualan bulan ini.")

    with tab_exp:
        all_exp = db.query(Expense).order_by(Expense.expense_date.desc()).limit(100).all()
        if all_exp:
            df = pd.DataFrame([{
                "Tanggal": str(e.expense_date),
                "Kategori": e.category,
                "Jumlah": e.amount,
                "Deskripsi": e.description or "",
                "Sale#": e.related_sale_id or "",
                "Oleh": e.created_by or "",
            } for e in all_exp])
            st.dataframe(df, use_container_width=True, hide_index=True)
            by_cat = df.groupby("Kategori")["Jumlah"].sum().reset_index()
            st.bar_chart(by_cat.set_index("Kategori"))
        else:
            st.info("Belum ada pengeluaran.")

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
                    db.add(Expense(
                        expense_date=edate,
                        category=cat,
                        amount=float(amount),
                        description=desc or None,
                        created_by=user["name"],
                    ))
                    db.commit()
                    flash_success("Pengeluaran tersimpan.")
                    st.rerun()
finally:
    db.close()
