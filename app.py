"""
Strawberry Fresh Supply - Supply Chain & Sales Management App
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from database import (
    init_db, get_db, User, verify_password, Setting,
    Category, Pickup, Receiving, SortingDetail, Sale, SaleItem,
    Expense, get_stock_by_name, Product, ChangeRequest, format_rp,
)
from ui_theme import apply_theme, theme_toggle, page_header, get_theme_mode, is_dark, text_primary, text_muted

st.set_page_config(
    page_title="Dashboard · Strawberry Fresh Supply",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="auto",
)


@st.cache_resource
def _init(schema_version: int = 4):
    init_db()
    return True


_init()
apply_theme()

if "user" not in st.session_state:
    st.session_state.user = None


def login_page():
    # theme on login too (partner light / you dark)
    with st.sidebar:
        theme_toggle(key="theme_mode_radio")
        st.caption("Pilih Light / Dark sebelum atau sesudah login.")

    st.markdown('<p class="main-header">🍓 Strawberry Fresh Supply</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Sistem Manajemen Rantai Pasok & Penjualan Strawberry</p>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([0.4, 1.4, 0.4])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="owner")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Masuk", use_container_width=True, type="primary")
            if submitted:
                db = get_db()
                try:
                    user = db.query(User).filter(User.username == username, User.is_active == True).first()
                    if user and verify_password(password, user.password_hash):
                        st.session_state.user = {
                            "id": user.id,
                            "name": user.name,
                            "username": user.username,
                            "role": user.role,
                        }
                        st.rerun()
                    else:
                        st.error("Username atau password salah")
                finally:
                    db.close()
        st.caption("Demo: owner/owner123 · driver1/driver123 · sorter1/sorter123 · sales1/sales123")
        st.markdown("</div>", unsafe_allow_html=True)


def logout():
    st.session_state.user = None
    st.rerun()


if st.session_state.user is None:
    login_page()
    st.stop()

user = st.session_state.user
is_owner = user["role"] in ("owner", "admin")

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
    if st.button("Logout", use_container_width=True):
        logout()
    st.divider()
    st.caption("Menu modul di sidebar.")
    db_side = get_db()
    try:
        company = db_side.query(Setting).filter_by(key="company_name").first()
        st.caption(company.value if company else "Strawberry App")
    finally:
        db_side.close()

page_header(
    "🍓 Dashboard",
    "Ringkasan operasional · "
    + ("Mode Owner (interaktif)" if is_owner else f"Mode {user['role'].title()}"),
)

db = get_db()
try:
    today = date.today()
    default_start = today - timedelta(days=13)

    if is_owner:
        f1, f2, f3 = st.columns([1, 1, 1])
        with f1:
            start = st.date_input("Dari", value=default_start, key="dash_start")
        with f2:
            end = st.date_input("Sampai", value=today, key="dash_end")
        with f3:
            farm_filter = st.selectbox(
                "Filter kebun",
                ["Semua", "RED HARVEST 1", "RED HARVEST 2"],
                key="dash_farm",
            )
        if start > end:
            st.error("Tanggal mulai tidak boleh setelah tanggal akhir.")
            st.stop()
    else:
        start, end = default_start, today
        farm_filter = "Semua"

    stocks = get_stock_by_name(db)
    total_stock = sum(stocks.values())
    month_start = today.replace(day=1)

    sales_all = db.query(Sale).filter(
        Sale.sale_date >= start,
        Sale.sale_date <= end,
        Sale.status != "cancelled",
    ).all()
    sales_today = [s for s in sales_all if s.sale_date == today]
    sales_month = db.query(Sale).filter(
        Sale.sale_date >= month_start,
        Sale.status != "cancelled",
    ).all()
    rev_range = sum(s.total_amount or 0 for s in sales_all)
    rev_today = sum(s.total_amount or 0 for s in sales_today)
    rev_month = sum(s.total_amount or 0 for s in sales_month)
    ship_range = sum(s.shipping_cost or 0 for s in sales_all)

    exp_range = db.query(Expense).filter(
        Expense.expense_date >= start,
        Expense.expense_date <= end,
    ).all()
    exp_month = db.query(Expense).filter(Expense.expense_date >= month_start).all()
    exp_total_range = sum(e.amount or 0 for e in exp_range)
    exp_total_month = sum(e.amount or 0 for e in exp_month)

    pickups_q = db.query(Pickup).filter(
        Pickup.pickup_date >= start,
        Pickup.pickup_date <= end,
    )
    if farm_filter != "Semua":
        pickups_q = pickups_q.filter(Pickup.farm_name == farm_filter)
    pickups = pickups_q.all()
    pending_pickups = db.query(Pickup).filter(Pickup.status == "pending").count()
    trays = sum(p.tray_count or 0 for p in pickups)
    recv_kg = sum((p.receiving.total_kg or 0) for p in pickups if p.receiving)

    pending_products = db.query(Product).filter(Product.approval_status == "pending").count()
    pending_adj = db.query(ChangeRequest).filter(
        ChangeRequest.status == "pending",
        ChangeRequest.entity_type == "stock_adjustment",
    ).count()
    pending_cr = db.query(ChangeRequest).filter(
        ChangeRequest.status == "pending",
        ChangeRequest.entity_type == "pickup",
    ).count()

    # ---- KPI ----
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📦 Stok total", f"{total_stock:g} kg")
    k2.metric("💰 Omzet hari ini", format_rp(rev_today))
    k3.metric("📈 Omzet periode", format_rp(rev_range))
    k4.metric("🚚 Pickup pending", pending_pickups)
    k5.metric("📥 Tray periode", trays)
    k6.metric("⚖️ Kg diterima", f"{recv_kg:g}")

    if is_owner:
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("🟡 Produk pending", pending_products)
        a2.metric("🟡 Adj. stok pending", pending_adj)
        a3.metric("🟡 Koreksi pickup", pending_cr)
        profit = rev_month - exp_total_month
        a4.metric("💵 Laba bulan (est.)", format_rp(profit))

        st.markdown("### 🔔 Perlu perhatian")
        alerts = []
        if pending_pickups:
            alerts.append(("warn", f"{pending_pickups} pickup masih **pending** (belum diterima/sortir)."))
        if pending_products:
            alerts.append(("warn", f"{pending_products} produk menunggu **approve**."))
        if pending_adj:
            alerts.append(("warn", f"{pending_adj} adjustment stok menunggu **approve**."))
        if pending_cr:
            alerts.append(("info", f"{pending_cr} permintaan koreksi pickup menunggu review."))
        if total_stock <= 0:
            alerts.append(("bad", "Stok kosong — belum ada penerimaan balance, atau stok habis terjual."))
        if not alerts:
            alerts.append(("ok", "Tidak ada antrean kritis. Operasional aman."))
        for kind, msg in alerts:
            cls = {
                "warn": "alert-warn",
                "ok": "alert-ok",
                "info": "alert-info",
                "bad": "alert-bad",
            }[kind]
            st.markdown(f'<div class="alert-box {cls}">{msg}</div>', unsafe_allow_html=True)

    st.divider()

    # ---- Charts ----
    left, right = st.columns(2)
    with left:
        st.subheader("Omzet harian (periode)")
        by_day = defaultdict(float)
        for s in sales_all:
            by_day[str(s.sale_date)] += s.total_amount or 0
        if by_day:
            df_omzet = pd.DataFrame({
                "Tanggal": sorted(by_day.keys()),
                "Omzet": [by_day[d] for d in sorted(by_day.keys())],
            }).set_index("Tanggal")
            st.line_chart(df_omzet)
            st.caption(f"Total periode: **{format_rp(rev_range)}** · Ongkir: {format_rp(ship_range)}")
        else:
            st.info("Belum ada penjualan di periode ini.")

        st.subheader("Status order")
        status_cnt = defaultdict(int)
        for s in db.query(Sale).filter(Sale.sale_date >= start, Sale.sale_date <= end).all():
            status_cnt[s.status or "unknown"] += 1
        if status_cnt:
            st.bar_chart(pd.DataFrame({"Jumlah": status_cnt}))
        else:
            st.caption("Tidak ada order.")

    with right:
        st.subheader("Stok per kategori")
        if stocks:
            cats = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()
            cat_map = {c.name: c for c in cats}
            ccols = st.columns(max(len(stocks), 1))
            for i, (name, kg) in enumerate(stocks.items()):
                with ccols[i]:
                    color = cat_map[name].color if name in cat_map else "#64748b"
                    st.markdown(
                        f"""
                        <div class="stock-card" style="background:{color}22;border-left:4px solid {color};">
                            <div class="lbl">{name}</div>
                            <div class="val">{kg:g} kg</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.bar_chart(pd.DataFrame({"kg": stocks}))
        else:
            st.info("Belum ada stok.")

        st.subheader("Yield rata-rata % (periode)")
        rec_ids = [p.receiving.id for p in pickups if p.receiving]
        if rec_ids:
            details = (
                db.query(SortingDetail, Category)
                .join(Category)
                .filter(SortingDetail.receiving_id.in_(rec_ids))
                .all()
            )
            tot = defaultdict(float)
            cnt = defaultdict(int)
            for sd, cat in details:
                if sd.percentage is not None:
                    tot[cat.name] += sd.percentage
                    cnt[cat.name] += 1
            avg = {k: round(tot[k] / cnt[k], 1) for k in tot if cnt[k]}
            if avg:
                st.bar_chart(pd.DataFrame({"%": avg}))
            else:
                st.info("Belum ada % yield.")
        else:
            st.info("Belum ada penerimaan di periode ini.")

    # ---- BREAKDOWN % SORTIR (penting) ----
    st.divider()
    st.subheader("📊 Breakdown Sortir % (dari kiriman tray → JUMBO / B / AB MIX)")
    st.caption(
        "Persentase hasil sortir vs total kg diterima. "
        "Rata-rata per SJ + total kg per kategori di periode filter."
    )

    rec_ids_all = [p.receiving.id for p in pickups if p.receiving]
    cats_all = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()

    if not rec_ids_all:
        st.info("Belum ada penerimaan di periode ini — breakdown % belum tersedia.")
    else:
        details = (
            db.query(SortingDetail, Category, Receiving)
            .join(Category, SortingDetail.category_id == Category.id)
            .join(Receiving, SortingDetail.receiving_id == Receiving.id)
            .filter(SortingDetail.receiving_id.in_(rec_ids_all))
            .all()
        )
        kg_by_cat = defaultdict(float)
        pct_sum = defaultdict(float)
        pct_cnt = defaultdict(int)
        for sd, cat, recv in details:
            kg_by_cat[cat.name] += float(sd.kg or 0)
            if sd.percentage is not None:
                pct_sum[cat.name] += float(sd.percentage)
                pct_cnt[cat.name] += 1
            elif recv.total_kg:
                pct = float(sd.kg or 0) / float(recv.total_kg) * 100.0
                pct_sum[cat.name] += pct
                pct_cnt[cat.name] += 1

        total_sorted_kg = sum(kg_by_cat.values()) or 0.0
        # weighted overall % from total kg (lebih akurat dari rata-rata aritmetika SJ)
        overall_pct = {
            name: (kg_by_cat[name] / total_sorted_kg * 100.0) if total_sorted_kg else 0.0
            for name in kg_by_cat
        }
        # pastikan semua kategori aktif tampil (0 jika kosong)
        for c in cats_all:
            overall_pct.setdefault(c.name, 0.0)
            kg_by_cat.setdefault(c.name, 0.0)

        # big % cards
        ordered_names = [c.name for c in cats_all] if cats_all else sorted(overall_pct.keys())
        if ordered_names:
            pcols = st.columns(len(ordered_names))
            color_map = {c.name: c.color for c in cats_all}
            label_c = text_muted()
            muted_c = text_muted()
            for i, name in enumerate(ordered_names):
                pct = overall_pct.get(name, 0.0)
                kg = kg_by_cat.get(name, 0.0)
                color = color_map.get(name, "#e11d48")
                with pcols[i]:
                    st.markdown(
                        f"""
                        <div class="pct-card" style="background:{color}22;border:2px solid {color};">
                            <div style="font-size:0.9rem;font-weight:600;color:{label_c};">{name}</div>
                            <div style="font-size:clamp(1.6rem,4vw,2.2rem);font-weight:800;color:{color};line-height:1.2;">
                                {pct:.1f}%
                            </div>
                            <div style="font-size:0.9rem;color:{muted_c};margin-top:4px;">{kg:g} kg</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            sum_pct = sum(overall_pct.get(n, 0) for n in ordered_names)
            st.caption(
                f"Total kg sortir periode: **{total_sorted_kg:g} kg** · "
                f"Jumlah % (harus ~100%): **{sum_pct:.1f}%** · "
                f"Dari **{len(rec_ids_all)}** penerimaan"
            )

            chart_df = pd.DataFrame({
                "Kategori": ordered_names,
                "%": [round(overall_pct.get(n, 0), 1) for n in ordered_names],
                "kg": [round(kg_by_cat.get(n, 0), 2) for n in ordered_names],
            })
            c_ch1, c_ch2 = st.columns(2)
            with c_ch1:
                st.markdown("**Distribusi %**")
                st.bar_chart(chart_df.set_index("Kategori")["%"])
            with c_ch2:
                st.markdown("**Volume kg**")
                st.bar_chart(chart_df.set_index("Kategori")["kg"])

            # detail per SJ
            with st.expander("Detail % per Surat Jalan", expanded=False):
                rows_sj = []
                for p in pickups:
                    if not p.receiving:
                        continue
                    r = p.receiving
                    row = {
                        "SJ": p.sj_number,
                        "Kebun": p.farm_name,
                        "Tanggal": str(p.pickup_date),
                        "Tray": p.tray_count,
                        "Total kg": r.total_kg,
                    }
                    for c in cats_all:
                        row[f"{c.name} kg"] = 0.0
                        row[f"{c.name} %"] = 0.0
                    for d in r.sorting_details:
                        cname = d.category.name if d.category else str(d.category_id)
                        row[f"{cname} kg"] = d.kg
                        pct = d.percentage
                        if pct is None and r.total_kg:
                            pct = (d.kg / r.total_kg) * 100.0
                        row[f"{cname} %"] = round(float(pct or 0), 1)
                    rows_sj.append(row)
                if rows_sj:
                    st.dataframe(pd.DataFrame(rows_sj), use_container_width=True, hide_index=True)
                else:
                    st.caption("Tidak ada detail SJ.")

    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        st.subheader("Pickup terbaru")
        recent = (
            db.query(Pickup)
            .order_by(Pickup.created_at.desc())
            .limit(10)
            .all()
        )
        if recent:
            st.dataframe([{
                "SJ": p.sj_number,
                "Kebun": p.farm_name,
                "Tray": p.tray_count,
                "Driver": p.driver.name if p.driver else "-",
                "Status": p.status,
                "Tanggal": str(p.pickup_date),
            } for p in recent], use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada pickup.")

    with b2:
        st.subheader("Penjualan terbaru")
        recent_sales = (
            db.query(Sale)
            .order_by(Sale.created_at.desc())
            .limit(10)
            .all()
        )
        if recent_sales:
            st.dataframe([{
                "ID": s.id,
                "Pelanggan": s.customer.name if s.customer else "-",
                "Total": format_rp(s.total_amount),
                "Status": s.status,
                "Tanggal": str(s.sale_date),
            } for s in recent_sales], use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada penjualan.")

    if is_owner:
        st.divider()
        st.subheader("Keuangan singkat (periode filter)")
        p1, p2, p3 = st.columns(3)
        p1.metric("Pendapatan", format_rp(rev_range))
        p2.metric("Pengeluaran", format_rp(exp_total_range))
        p3.metric("Selisih", format_rp(rev_range - exp_total_range))

        st.subheader("Top produk (qty kg, periode)")
        prod_qty = defaultdict(float)
        for s in sales_all:
            for it in s.items:
                name = it.product.name if it.product else str(it.product_id)
                prod_qty[name] += it.qty_kg or 0
        if prod_qty:
            df_top = (
                pd.DataFrame({"Produk": list(prod_qty.keys()), "kg": list(prod_qty.values())})
                .sort_values("kg", ascending=False)
                .head(8)
            )
            st.bar_chart(df_top.set_index("Produk"))
        else:
            st.caption("Belum ada item terjual di periode ini.")

    st.divider()
    st.info(
        "👉 Navigasi: sidebar → Pengambilan, Penerimaan & Sortir, Stok, Produk, "
        "Penjualan, Keuangan, Master Data, Laporan, Log, **Panduan & FAQ**."
    )
finally:
    db.close()
