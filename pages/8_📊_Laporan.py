"""Laporan — stok, omzet, yield, performa, produk terlaris."""
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
import streamlit as st

from auth_utils import require_login, show_user_sidebar
from database import (
    get_db, Sale, SaleItem, Product, Pickup, Receiving, SortingDetail,
    Category, Expense, User, get_stock_by_name,
)

st.set_page_config(page_title="Laporan", page_icon="📊", layout="wide")
user = require_login(["owner", "admin", "sales"])
show_user_sidebar()

st.markdown("## 📊 Laporan")
st.caption("Stok, omzet, yield %, performa, produk terlaris")

db = get_db()
try:
    today = date.today()
    c1, c2 = st.columns(2)
    start = c1.date_input("Dari", value=today.replace(day=1))
    end = c2.date_input("Sampai", value=today)

    stocks = get_stock_by_name(db)
    sales = db.query(Sale).filter(
        Sale.sale_date >= start,
        Sale.sale_date <= end,
        Sale.status != "cancelled",
    ).all()
    pickups = db.query(Pickup).filter(Pickup.pickup_date >= start, Pickup.pickup_date <= end).all()
    expenses = db.query(Expense).filter(Expense.expense_date >= start, Expense.expense_date <= end).all()

    rev = sum(s.total_amount or 0 for s in sales)
    ship_total = sum(s.shipping_cost or 0 for s in sales)
    exp_total = sum(e.amount or 0 for e in expenses)
    trays = sum(p.tray_count or 0 for p in pickups)
    recv_kg = 0.0
    for p in pickups:
        if p.receiving:
            recv_kg += p.receiving.total_kg or 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Omzet", f"Rp {rev:,.0f}")
    m2.metric("Pengeluaran", f"Rp {exp_total:,.0f}")
    m3.metric("Total Stok", f"{sum(stocks.values()):,.1f} kg")
    m4.metric("Tray masuk", trays)
    m5.metric("Kg diterima", f"{recv_kg:,.1f}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Stok saat ini")
        if stocks:
            st.bar_chart(pd.DataFrame({"kg": stocks}))
        else:
            st.info("Tidak ada stok.")

        st.subheader("Produk Terlaris (kg)")
        prod_qty = defaultdict(float)
        for s in sales:
            for item in s.items:
                pname = item.product.name if item.product else str(item.product_id)
                prod_qty[pname] += item.qty_kg or 0
        if prod_qty:
            df = pd.DataFrame({"Produk": list(prod_qty.keys()), "kg": list(prod_qty.values())}).sort_values("kg", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index("Produk"))
        else:
            st.info("Belum ada penjualan di periode ini.")

    with right:
        st.subheader("Yield rata-rata %")
        rec_ids = [p.receiving.id for p in pickups if p.receiving]
        details = []
        if rec_ids:
            details = db.query(SortingDetail, Category).join(Category).filter(SortingDetail.receiving_id.in_(rec_ids)).all()
        if details:
            tot = defaultdict(float)
            cnt = defaultdict(int)
            for sd, cat in details:
                if sd.percentage is not None:
                    tot[cat.name] += sd.percentage
                    cnt[cat.name] += 1
            avg = {k: round(tot[k] / cnt[k], 1) for k in tot if cnt[k]}
            st.bar_chart(pd.DataFrame({"%": avg}))
        else:
            st.info("Belum ada data sorting di periode ini.")

        st.subheader("Efisiensi kg / tray")
        if trays > 0:
            st.metric("kg per tray", f"{recv_kg / trays:.2f}")
        else:
            st.info("Belum ada tray.")

        st.subheader("% Ongkir vs Omzet")
        pct_ship = (ship_total / rev * 100) if rev else 0
        st.metric("Ongkir", f"Rp {ship_total:,.0f}", delta=f"{pct_ship:.1f}% dari omzet")

    st.divider()
    st.subheader("Performa Driver (jumlah pickup & tray)")
    driver_stats = defaultdict(lambda: {"pickup": 0, "tray": 0})
    for p in pickups:
        name = p.driver.name if p.driver else "Unknown"
        driver_stats[name]["pickup"] += 1
        driver_stats[name]["tray"] += p.tray_count or 0
    if driver_stats:
        st.dataframe(pd.DataFrame([
            {"Driver": k, "Pickup": v["pickup"], "Tray": v["tray"]}
            for k, v in driver_stats.items()
        ]), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada pickup di periode ini.")

    st.subheader("Performa Sales (omzet)")
    sales_stats = defaultdict(float)
    for s in sales:
        name = s.created_by_user.name if s.created_by_user else "Unknown"
        sales_stats[name] += s.total_amount or 0
    if sales_stats:
        st.dataframe(pd.DataFrame([
            {"Sales": k, "Omzet": v} for k, v in sales_stats.items()
        ]), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada penjualan di periode ini.")
finally:
    db.close()
