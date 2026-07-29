"""Modul Penjualan — multi-item, diskon auto, edit order, invoice PDF + WhatsApp."""
import json
import io
import urllib.parse
from datetime import date, datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success, flash_error
from database import (
    get_db, Sale, SaleItem, Product, Customer, Setting, format_rp,
    InventoryMovement, SaleStatus, ShippingMethod, MovementType,
    get_current_stock, Expense, write_log, generate_invoice_number,
)
from ui_theme import is_dark, safe_download_button

st.set_page_config(page_title="Penjualan", page_icon="🛒", layout="wide")
user = require_login(["owner", "admin", "sales"])
show_user_sidebar()

st.markdown("## 🛒 Penjualan")
st.caption("Multi-item · diskon otomatis pelanggan · edit order · invoice PDF")

SHIP_OPTIONS = [m.value for m in ShippingMethod]

if "sale_lines" not in st.session_state:
    st.session_state.sale_lines = [{"product_id": None, "qty": 1.0, "price": 0.0}]

db = get_db()
try:
    tab_new, tab_list = st.tabs(["Buat Order", "Daftar Penjualan"])

    with tab_new:
        customers = db.query(Customer).filter_by(is_active=True).order_by(Customer.name).all()
        products = db.query(Product).filter(Product.is_active.is_(True), Product.approval_status == "approved").order_by(Product.name).all()
        prod_by_id = {p.id: p for p in products}

        if not products:
            st.warning("Belum ada produk aktif.")

        st.markdown("### Pelanggan")
        search = st.text_input("Cari / ketik nama pelanggan *", placeholder="Contoh: RIZKY", key="cust_search")
        q = (search or "").strip().lower()
        matched = [c for c in customers if q and q in (c.name or "").lower()] if q else customers[:20]
        options = [f"{c.name}" + (f" · {c.phone}" if c.phone else "") for c in matched]
        id_map = {f"{c.name}" + (f" · {c.phone}" if c.phone else ""): c for c in matched}

        cust = None
        if matched:
            pick = st.selectbox(f"Hasil ({len(matched)})", options, key="cust_pick")
            cust = id_map.get(pick)
            if cust:
                st.caption(f"Dipilih: **{cust.name}** · Diskon default: {cust.default_discount_pct or 0}%")
        elif q:
            st.warning(f"Tidak ada pelanggan cocok dengan \"{search}\".")
            with st.expander("➕ New Customer", expanded=True):
                nc_name = st.text_input("Nama pelanggan baru *", value=search.strip(), key="nc_name")
                nc_phone = st.text_input("Telepon", key="nc_phone")
                nc_addr = st.text_input("Alamat", key="nc_addr")
                nc_disc = st.number_input("Diskon default %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="nc_disc")
                if st.button("Simpan pelanggan baru", type="primary", key="nc_save"):
                    if not nc_name.strip():
                        st.error("Nama wajib.")
                    else:
                        existing = db.query(Customer).filter(Customer.name.ilike(nc_name.strip())).first()
                        if existing:
                            st.error(f"Pelanggan '{nc_name.strip()}' sudah ada (ID #{existing.id}).")
                        else:
                            c = Customer(name=nc_name.strip(), phone=nc_phone.strip() or None,
                                address=nc_addr.strip() or None, default_discount_pct=float(nc_disc), is_active=True)
                            db.add(c)
                            db.flush()
                            write_log(db, user, "customer.create", f"Pelanggan baru {nc_name.strip()}", entity_type="customer", entity_id=c.id)
                            db.commit()
                            flash_success(f"Pelanggan '{nc_name.strip()}' ditambah.")
                            st.rerun()

        if cust and products:
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Pelanggan:** {cust.name}")
                sale_date = st.date_input("Tanggal", value=date.today())
            with c2:
                ship = st.selectbox("Metode pengiriman", SHIP_OPTIONS)
                ship_cost = st.number_input("Ongkir (Rp)", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
                notes = st.text_area("Catatan", height=80)

            st.subheader("Item")
            if not st.session_state.sale_lines:
                st.session_state.sale_lines = [{"product_id": products[0].id, "qty": 1.0, "price": float(products[0].base_price)}]

            for line in st.session_state.sale_lines:
                if line.get("product_id") not in prod_by_id:
                    line["product_id"] = products[0].id
                    line["price"] = float(products[0].base_price)

            b_add, b_clr = st.columns(2)
            with b_add:
                if st.button("➕ Tambah baris item"):
                    p0 = products[0]
                    st.session_state.sale_lines.append({"product_id": p0.id, "qty": 1.0, "price": float(p0.base_price)})
                    st.rerun()
            with b_clr:
                if st.button("🧹 Reset item") and len(st.session_state.sale_lines) > 0:
                    p0 = products[0]
                    st.session_state.sale_lines = [{"product_id": p0.id, "qty": 1.0, "price": float(p0.base_price)}]
                    st.rerun()

            items_calc = []
            for i, line in enumerate(list(st.session_state.sale_lines)):
                with st.container(border=True):
                    ic1, ic2, ic3, ic4 = st.columns([3, 2, 2, 1])
                    pids = [p.id for p in products]
                    cur_pid = line.get("product_id") if line.get("product_id") in pids else products[0].id
                    with ic1:
                        prod = st.selectbox(f"Produk #{i+1}", products, index=pids.index(cur_pid),
                            format_func=lambda p: f"{p.name} ({format_rp(p.base_price)})", key=f"prod_{i}")
                    with ic2:
                        qty = st.number_input(f"Qty kg #{i+1}", min_value=0.01, value=float(line.get("qty") or 1.0), step=0.1, format="%.2f", key=f"qty_{i}")
                    with ic3:
                        price_key = f"price_{i}_{prod.id}"
                        if price_key not in st.session_state:
                            st.session_state[price_key] = float(prod.base_price)
                        price = st.number_input(f"Harga/kg #{i+1}", min_value=0.0, step=500.0, format="%.0f", key=price_key)
                    line_sub = float(qty) * float(price)
                    with ic4:
                        st.caption("Sub")
                        st.write(format_rp(line_sub))
                        if len(st.session_state.sale_lines) > 1 and st.button("🗑", key=f"del_{i}"):
                            st.session_state.sale_lines.pop(i)
                            st.rerun()
                    st.session_state.sale_lines[i] = {"product_id": prod.id, "qty": float(qty), "price": float(price)}
                    items_calc.append((prod, float(qty), float(price), line_sub))

            subtotal = sum(x[3] for x in items_calc)
            st.divider()

            default_disc = 0.0
            if cust and cust.default_discount_pct:
                default_disc = subtotal * cust.default_discount_pct / 100.0

            disc_amt = st.number_input(
                "Diskon nominal (Rp)", min_value=0.0, value=float(default_disc),
                step=1000.0, format="%.0f",
                help=f"Diskon default pelanggan: {cust.default_discount_pct or 0}% = {format_rp(default_disc)}. Bisa diubah.",
                key="disc_amt",
            )
            after_disc = max(subtotal - float(disc_amt), 0.0)
            total = after_disc + float(ship_cost)

            st.markdown("**Rincian item**")
            for prod, qty, price, line_sub in items_calc:
                st.write(f"• {prod.name}: {qty:g} kg × {format_rp(price)} = **{format_rp(line_sub)}**")

            bg = "#1a1f2b" if is_dark() else "#fff1f2"
            bd = "#f43f5e" if is_dark() else "#e11d48"
            tx = "#e6edf3" if is_dark() else "#18181b"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bd};border-radius:12px;padding:14px;margin:8px 0;color:{tx};">
              <div>Subtotal item: <b>{format_rp(subtotal)}</b></div>
              <div>Diskon nominal: <b>- {format_rp(disc_amt)}</b></div>
              <div>Setelah diskon: <b>{format_rp(after_disc)}</b></div>
              <div>Ongkir: <b>{format_rp(ship_cost)}</b></div>
              <div style="font-size:1.25rem;margin-top:6px;">Total bayar: <b>{format_rp(total)}</b></div>
            </div>
            """, unsafe_allow_html=True)

            status_choice = st.selectbox("Status simpan", ["draft", "confirmed"])
            if st.button("Simpan Order", type="primary", use_container_width=True):
                if not items_calc:
                    flash_error("Minimal 1 item.")
                    st.rerun()
                need = {}
                ok = True
                if status_choice == "confirmed":
                    for prod, qty, _, _ in items_calc:
                        for r in prod.recipes:
                            need[r.category_id] = need.get(r.category_id, 0.0) + float(qty) * float(r.ratio)
                    for cid, kg_need in need.items():
                        stock = get_current_stock(db, cid)
                        if stock + 1e-9 < kg_need:
                            st.error(f"Stok kurang: category_id={cid} butuh {kg_need:g} kg, tersedia {stock:g} kg")
                            ok = False
                if ok:
                    sale = Sale(customer_id=cust.id, sale_date=sale_date, subtotal=float(subtotal),
                        discount_amount=float(disc_amt), discount_pct=0.0, shipping_method=ship,
                        shipping_cost=float(ship_cost), total_amount=float(total),
                        status=status_choice, notes=notes or None, created_by_id=user["id"])
                    db.add(sale)
                    db.flush()
                    sale.invoice_number = generate_invoice_number(sale.id, sale_date)
                    for prod, qty, price, line_sub in items_calc:
                        db.add(SaleItem(sale_id=sale.id, product_id=prod.id, qty_kg=float(qty),
                            unit_price=float(price), subtotal=float(line_sub)))
                    if status_choice == "confirmed":
                        for cid, kg_need in need.items():
                            db.add(InventoryMovement(category_id=cid, movement_type=MovementType.OUT_SALE.value,
                                qty_kg=-float(kg_need), ref_type="sale", ref_id=sale.id,
                                notes=f"Sale #{sale.id}", created_by=user["name"]))
                        if ship_cost > 0:
                            db.add(Expense(expense_date=sale_date, category="shipping",
                                amount=float(ship_cost), description=f"Ongkir sale #{sale.id} ({ship})",
                                related_sale_id=sale.id, created_by=user["name"]))
                    write_log(db, user, "sale.create", f"Order #{sale.id} {cust.name} {format_rp(total)} ({status_choice})",
                        entity_type="sale", entity_id=sale.id, detail=str([(p.name, q, pr) for p, q, pr, _ in items_calc]))
                    db.commit()

                    # Build items text for WA
                    items_text = "\n".join(
                        f"• {prod.name}: {qty:g} kg × {format_rp(price)} = {format_rp(line_sub)}"
                        for prod, qty, price, line_sub in items_calc
                    )
                    # Store in session for WA popup
                    st.session_state.wa_sale = {
                        "id": sale.id,
                        "invoice": sale.invoice_number or f"INV-{sale.id}",
                        "customer_name": cust.name,
                        "customer_phone": cust.phone or "",
                        "items_text": items_text,
                        "total": format_rp(total),
                        "ongkir": format_rp(ship_cost),
                        "diskon": format_rp(disc_amt),
                        "tanggal": str(sale_date),
                        "catatan": notes or "-",
                    }
                    st.session_state.sale_lines = [{"product_id": products[0].id, "qty": 1.0, "price": float(products[0].base_price)}]
                    st.rerun()

        # ── WhatsApp popup after order ──
        if st.session_state.get("wa_sale"):
            ws = st.session_state.wa_sale
            st.divider()
            bg = "#1a2332" if is_dark() else "#f0fdf4"
            bd = "#22c55e" if is_dark() else "#16a34a"
            tx = "#e6edf3" if is_dark() else "#14532d"
            st.markdown(f"""
            <div style="background:{bg};border:2px solid {bd};border-radius:16px;padding:20px;margin:12px 0;color:{tx};">
              <div style="font-size:1.3rem;font-weight:700;">✅ Order #{ws['id']} Tersimpan!</div>
              <div style="margin-top:8px;">
                <b>Pelanggan:</b> {ws['customer_name']}<br>
                <b>Invoice:</b> {ws['invoice']}<br>
                <b>Total:</b> {ws['total']}<br>
                <b>Telepon:</b> {ws['customer_phone'] or '❌ Tidak ada nomor'}
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_wa, col_done = st.columns(2)
            with col_wa:
                # Load WA template
                wa_tpl_setting = db.query(Setting).filter_by(key="wa_template").first()
                default_tpl = "Halo {nama_pelanggan},\n\nBerikut pesanan Anda:\n\n{items}\n\nTotal: {total}\nOngkir: {ongkir}\nDiskon: {diskon}\n\nInvoice: {invoice}\nTanggal: {tanggal}\n\nTerima kasih 🍓"
                tpl = wa_tpl_setting.value if wa_tpl_setting else default_tpl

                # Build message
                wa_msg = tpl.format(
                    nama_pelanggan=ws["customer_name"],
                    invoice=ws["invoice"],
                    tanggal=ws["tanggal"],
                    items=ws["items_text"],
                    total=ws["total"],
                    ongkir=ws["ongkir"],
                    diskon=ws["diskon"],
                    catatan=ws["catatan"],
                )

                phone = ws["customer_phone"].strip().replace("+", "").replace("-", "").replace(" ", "")
                if not phone.startswith("62") and phone.startswith("0"):
                    phone = "62" + phone[1:]
                encoded_msg = urllib.parse.quote(wa_msg)
                wa_url = f"https://wa.me/{phone}?text={encoded_msg}" if phone else None

                if wa_url:
                    st.link_button("📱 KIRIM WHATSAPP", wa_url, use_container_width=True, type="primary")
                    with st.expander("👀 Preview Pesan"):
                        st.code(wa_msg, language=None)
                else:
                    st.warning("Nomor telepon pelanggan kosong. Tidak bisa kirim WhatsApp.")
                    st.caption("Edit pelanggan dulu untuk tambahkan nomor telepon.")

            with col_done:
                if st.button("✅ Selesai", use_container_width=True, type="secondary"):
                    del st.session_state.wa_sale
                    flash_success(f"Order #{ws['id']} selesai.")
                    st.rerun()

    with tab_list:
        sales = db.query(Sale).order_by(Sale.created_at.desc()).limit(100).all()
        if not sales:
            st.info("Belum ada penjualan.")
        else:
            rows = [{
                "ID": s.id, "Invoice": s.invoice_number or "-", "Tanggal": str(s.sale_date),
                "Pelanggan": s.customer.name if s.customer else "-", "Total": format_rp(s.total_amount),
                "Status": s.status, "Oleh": s.created_by_user.name if s.created_by_user else "-",
            } for s in sales]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.subheader("Detail & Invoice")
            sale_opts = {f"#{s.id} {s.customer.name if s.customer else ''} — {format_rp(s.total_amount)}": s.id for s in sales}
            sid_label = st.selectbox("Pilih order", list(sale_opts.keys()), key="sale_detail")
            sale = db.get(Sale, sale_opts[sid_label])
            if sale and sale.items:
                st.dataframe([{
                    "Produk": it.product.name if it.product else it.product_id,
                    "Qty kg": it.qty_kg, "Harga/kg": format_rp(it.unit_price), "Subtotal": format_rp(it.subtotal),
                } for it in sale.items], use_container_width=True, hide_index=True)

                from reportlab.lib.pagesizes import A5
                from reportlab.pdfgen import canvas as pdf_canvas
                from reportlab.lib.units import mm

                def gen_invoice(sale_obj, items, customer, company_name="Strawberry Fresh Supply"):
                    buf = io.BytesIO()
                    c_pdf = pdf_canvas.Canvas(buf, pagesize=A5)
                    w, h = A5
                    y = h - 15*mm
                    c_pdf.setFont("Helvetica-Bold", 14)
                    c_pdf.drawString(15*mm, y, company_name)
                    y -= 7*mm
                    c_pdf.setFont("Helvetica", 9)
                    c_pdf.drawString(15*mm, y, f"Invoice: {sale_obj.invoice_number or f'INV-{sale_obj.id}'}")
                    y -= 5*mm
                    c_pdf.drawString(15*mm, y, f"Tanggal: {sale_obj.sale_date}")
                    y -= 5*mm
                    c_pdf.drawString(15*mm, y, f"Pelanggan: {customer.name}")
                    y -= 8*mm
                    c_pdf.setFont("Helvetica-Bold", 9)
                    c_pdf.drawString(15*mm, y, "Produk")
                    c_pdf.drawString(80*mm, y, "Qty")
                    c_pdf.drawString(100*mm, y, "Harga")
                    c_pdf.drawString(130*mm, y, "Subtotal")
                    y -= 5*mm
                    c_pdf.line(15*mm, y, w-15*mm, y)
                    y -= 5*mm
                    c_pdf.setFont("Helvetica", 9)
                    for item in items:
                        pname = item.product.name if item.product else str(item.product_id)
                        c_pdf.drawString(15*mm, y, pname[:30])
                        c_pdf.drawString(80*mm, y, f"{item.qty_kg:g} kg")
                        c_pdf.drawString(100*mm, y, format_rp(item.unit_price))
                        c_pdf.drawString(130*mm, y, format_rp(item.subtotal))
                        y -= 5*mm
                    y -= 3*mm
                    c_pdf.line(15*mm, y, w-15*mm, y)
                    y -= 7*mm
                    c_pdf.setFont("Helvetica-Bold", 10)
                    c_pdf.drawString(15*mm, y, f"Subtotal: {format_rp(sale_obj.subtotal)}")
                    y -= 5*mm
                    c_pdf.drawString(15*mm, y, f"Diskon: - {format_rp(sale_obj.discount_amount)}")
                    y -= 5*mm
                    c_pdf.drawString(15*mm, y, f"Ongkir: {format_rp(sale_obj.shipping_cost)}")
                    y -= 7*mm
                    c_pdf.setFont("Helvetica-Bold", 12)
                    c_pdf.drawString(15*mm, y, f"TOTAL: {format_rp(sale_obj.total_amount)}")
                    c_pdf.save()
                    buf.seek(0)
                    return buf

                pdf_buf = gen_invoice(sale, sale.items, sale.customer)
                safe_download_button("Download Invoice PDF", pdf_buf, f"Invoice_{sale.invoice_number or sale.id}.pdf", "application/pdf", key="inv_pdf")

            st.subheader("Ubah Status")
            active = [s for s in sales if s.status not in (SaleStatus.CANCELLED.value, SaleStatus.DELIVERED.value)]
            if active:
                opts = {f"#{s.id} {s.customer.name if s.customer else ''} — {s.status}": s.id for s in active}
                sel = st.selectbox("Pilih order", list(opts.keys()), key="sale_status_sel")
                new_status = st.selectbox("Status baru", ["draft", "confirmed", "shipped", "delivered", "cancelled"])
                if st.button("Update Status", type="primary"):
                    sale = db.get(Sale, opts[sel])
                    old = sale.status
                    if old == new_status:
                        st.info("Status sama.")
                    else:
                        if old == "draft" and new_status == "confirmed":
                            need = {}
                            for item in sale.items:
                                for r in item.product.recipes:
                                    need[r.category_id] = need.get(r.category_id, 0.0) + float(item.qty_kg) * float(r.ratio)
                            short = False
                            for cid, kg_need in need.items():
                                stock = get_current_stock(db, cid)
                                if stock + 1e-9 < kg_need:
                                    st.error(f"Stok kurang category_id={cid}: butuh {kg_need:g}, ada {stock:g}")
                                    short = True
                            if short:
                                st.stop()
                            for cid, kg_need in need.items():
                                db.add(InventoryMovement(category_id=cid, movement_type=MovementType.OUT_SALE.value,
                                    qty_kg=-float(kg_need), ref_type="sale", ref_id=sale.id,
                                    notes=f"Sale #{sale.id} confirmed", created_by=user["name"]))
                            if sale.shipping_cost and sale.shipping_cost > 0:
                                exists = db.query(Expense).filter_by(related_sale_id=sale.id, category="shipping").first()
                                if not exists:
                                    db.add(Expense(expense_date=sale.sale_date, category="shipping",
                                        amount=float(sale.shipping_cost), description=f"Ongkir sale #{sale.id}",
                                        related_sale_id=sale.id, created_by=user["name"]))
                        if new_status == "shipped":
                            sale.shipped_at = datetime.utcnow()
                        if old in ("confirmed", "shipped", "delivered") and new_status == "cancelled":
                            movs = db.query(InventoryMovement).filter_by(ref_type="sale", ref_id=sale.id, movement_type=MovementType.OUT_SALE.value).all()
                            for m in movs:
                                db.add(InventoryMovement(category_id=m.category_id, movement_type=MovementType.IN_RETURN.value,
                                    qty_kg=abs(m.qty_kg), ref_type="sale", ref_id=sale.id,
                                    notes=f"Cancel sale #{sale.id}", created_by=user["name"]))
                            exp = db.query(Expense).filter_by(related_sale_id=sale.id, category="shipping").first()
                            if exp:
                                db.delete(exp)
                        sale.status = new_status
                        write_log(db, user, "sale.status", f"Sale #{sale.id}: {old} → {new_status}",
                            entity_type="sale", entity_id=sale.id)
                        db.commit()
                        flash_success(f"✅ Sale #{sale.id}: {old} → {new_status}")
                        st.rerun()

            st.subheader("Edit Order")
            editable = [s for s in sales if s.status in ("draft", "confirmed")]
            if editable:
                edit_opts = {f"#{s.id} {s.customer.name if s.customer else ''} — {format_rp(s.total_amount)} ({s.status})": s.id for s in editable}
                edit_sel = st.selectbox("Pilih order untuk edit", list(edit_opts.keys()), key="edit_order_sel")
                edit_sale = db.get(Sale, edit_opts[edit_sel])
                if edit_sale:
                    with st.form("edit_order_form"):
                        new_date = st.date_input("Tanggal", value=edit_sale.sale_date)
                        ship_idx = SHIP_OPTIONS.index(edit_sale.shipping_method) if edit_sale.shipping_method in SHIP_OPTIONS else 0
                        new_ship = st.selectbox("Metode kirim", SHIP_OPTIONS, index=ship_idx)
                        new_ship_cost = st.number_input("Ongkir", value=float(edit_sale.shipping_cost or 0))
                        new_disc = st.number_input("Diskon nominal", value=float(edit_sale.discount_amount or 0))
                        new_notes = st.text_area("Catatan", value=edit_sale.notes or "")
                        if st.form_submit_button("Simpan Perubahan", type="primary"):
                            before = {"date": str(edit_sale.sale_date), "shipping": edit_sale.shipping_method,
                                "ongkir": edit_sale.shipping_cost, "discount": edit_sale.discount_amount, "notes": edit_sale.notes}
                            edit_sale.sale_date = new_date
                            edit_sale.shipping_method = new_ship
                            edit_sale.shipping_cost = float(new_ship_cost)
                            edit_sale.discount_amount = float(new_disc)
                            edit_sale.notes = new_notes or None
                            edit_sale.total_amount = (edit_sale.subtotal or 0) - float(new_disc) + float(new_ship_cost)
                            after = {"date": str(edit_sale.sale_date), "shipping": edit_sale.shipping_method,
                                "ongkir": edit_sale.shipping_cost, "discount": edit_sale.discount_amount, "notes": edit_sale.notes}
                            write_log(db, user, "sale.edit", f"Edit order #{edit_sale.id}",
                                entity_type="sale", entity_id=edit_sale.id, detail=json.dumps({"before": before, "after": after}))
                            db.commit()
                            flash_success(f"Order #{edit_sale.id} diupdate.")
                            st.rerun()
finally:
    db.close()
