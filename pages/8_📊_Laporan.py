"""Laporan — stok, omzet, yield, performa, export."""
import io
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
import streamlit as st

from auth_utils import require_login, show_user_sidebar
from database import (
    get_db, Sale, SaleItem, Product, Pickup, Receiving, SortingDetail,
    Category, Expense, User, get_stock_by_name, Farm, format_rp,
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
    sales = db.query(Sale).filter(Sale.sale_date >= start, Sale.sale_date <= end, Sale.status != "cancelled").all()
    pickups = db.query(Pickup).filter(Pickup.pickup_date >= start, Pickup.pickup_date <= end).all()
    expenses = db.query(Expense).filter(Expense.expense_date >= start, Expense.expense_date <= end).all()

    rev = sum(s.total_amount or 0 for s in sales)
    ship_total = sum(s.shipping_cost or 0 for s in sales)
    exp_total = sum(e.amount or 0 for e in expenses)
    trays = sum(p.tray_count or 0 for p in pickups)
    recv_kg = sum(p.receiving.total_kg or 0 for p in pickups if p.receiving)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Omzet", format_rp(rev))
    m2.metric("Pengeluaran", format_rp(exp_total))
    m3.metric("Total Stok", f"{sum(stocks.values()):,.1f} kg")
    m4.metric("Tray masuk", trays)
    m5.metric("Kg diterima", f"{recv_kg:,.1f}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Stok saat ini")
        if stocks:
            st.bar_chart(pd.DataFrame({"kg": stocks}))

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

        st.subheader("Efisiensi kg / tray")
        if trays > 0:
            st.metric("kg per tray", f"{recv_kg / trays:.2f}")

        st.subheader("% Ongkir vs Omzet")
        pct_ship = (ship_total / rev * 100) if rev else 0
        st.metric("Ongkir", format_rp(ship_total), delta=f"{pct_ship:.1f}% dari omzet")

    st.divider()

    st.subheader("📈 Tren Yield % per Kategori")
    if rec_ids:
        details_trend = db.query(SortingDetail, Category, Receiving).join(Category).join(Receiving).filter(SortingDetail.receiving_id.in_(rec_ids)).all()
        trend_data = defaultdict(lambda: defaultdict(float))
        trend_cnt = defaultdict(lambda: defaultdict(int))
        for sd, cat, recv in details_trend:
            if sd.percentage is not None and recv.pickup:
                day = str(recv.pickup.pickup_date)
                trend_data[day][cat.name] += sd.percentage
                trend_cnt[day][cat.name] += 1
        avg_trend = {}
        for day in sorted(trend_data.keys()):
            avg_trend[day] = {}
            for cat_name in trend_data[day]:
                avg_trend[day][cat_name] = round(trend_data[day][cat_name] / trend_cnt[day][cat_name], 1)
        if avg_trend:
            df_trend = pd.DataFrame(avg_trend).T.sort_index()
            st.line_chart(df_trend)

    st.divider()
    st.subheader("Performa Driver")
    driver_stats = defaultdict(lambda: {"pickup": 0, "tray": 0})
    for p in pickups:
        name = p.driver.name if p.driver else "Unknown"
        driver_stats[name]["pickup"] += 1
        driver_stats[name]["tray"] += p.tray_count or 0
    if driver_stats:
        st.dataframe(pd.DataFrame([{"Driver": k, "Pickup": v["pickup"], "Tray": v["tray"]} for k, v in driver_stats.items()]),
            use_container_width=True, hide_index=True)

    st.subheader("Performa Sales (omzet)")
    sales_stats = defaultdict(float)
    for s in sales:
        name = s.created_by_user.name if s.created_by_user else "Unknown"
        sales_stats[name] += s.total_amount or 0
    if sales_stats:
        st.dataframe(pd.DataFrame([{"Sales": k, "Omzet": format_rp(v)} for k, v in sales_stats.items()]),
            use_container_width=True, hide_index=True)

    st.subheader("Top Pelanggan")
    cust_stats = defaultdict(float)
    for s in sales:
        cname = s.customer.name if s.customer else "Unknown"
        cust_stats[cname] += s.total_amount or 0
    if cust_stats:
        df_cust = pd.DataFrame({"Pelanggan": list(cust_stats.keys()), "Omzet": list(cust_stats.values())}).sort_values("Omzet", ascending=False)
        st.dataframe(df_cust, use_container_width=True, hide_index=True)

    st.subheader("Perbandingan Kebun")
    farm_stats = defaultdict(lambda: {"tray": 0, "kg": 0})
    for p in pickups:
        farm_stats[p.farm_name]["tray"] += p.tray_count or 0
        farm_stats[p.farm_name]["kg"] += p.receiving.total_kg if p.receiving else 0
    if farm_stats:
        st.dataframe(pd.DataFrame([{"Kebun": k, "Tray": v["tray"], "Kg": v["kg"], "Kg/Tray": f"{v['kg']/v['tray']:.2f}" if v["tray"] else "0"} for k, v in farm_stats.items()]),
            use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📥 Export Semua Data")
    if sales:
        df_all = pd.DataFrame([{
            "ID": s.id, "Tanggal": str(s.sale_date), "Pelanggan": s.customer.name if s.customer else "-",
            "Total": s.total_amount, "Status": s.status,
        } for s in sales])
        csv = df_all.to_csv(index=False).encode("utf-8")
        xlsx_buf = io.BytesIO()
        df_all.to_excel(xlsx_buf, index=False, engine="openpyxl")
        xlsx_buf.seek(0)
        c_csv, c_xlsx = st.columns(2)
        with c_csv:
            st.download_button("📥 Export Penjualan CSV", csv, "laporan_penjualan.csv", "text/csv")
        with c_xlsx:
            st.download_button("📥 Export Penjualan Excel", xlsx_buf, "laporan_penjualan.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
finally:
    db.close()
