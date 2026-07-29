"""Modul Penerimaan & Sortir — cek SJ, timbang, sortir kategori, balance."""
from datetime import datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success, flash_error
from database import (
    get_db, Pickup, Receiving, SortingDetail, Category, Setting,
    InventoryMovement, PickupStatus, MovementType, write_log,
)

st.set_page_config(page_title="Penerimaan & Sortir", page_icon="⚖️", layout="wide")
user = require_login(["owner", "admin", "sorter"])
show_user_sidebar()

st.markdown("## ⚖️ Penerimaan & Sortir")
st.caption("Cek SJ → timbang total → sortir per kategori → balance → stok masuk")
st.caption("💡 Angka desimal pakai titik, contoh: `12.5` (bukan koma).")

if "recv_lock" not in st.session_state:
    st.session_state.recv_lock = None
if "recv_confirm" not in st.session_state:
    st.session_state.recv_confirm = None

db = get_db()
try:
    tol_row = db.query(Setting).filter_by(key="tolerance_kg").first()
    tolerance = float(tol_row.value) if tol_row else 0.15
    categories = db.query(Category).filter_by(is_active=True).order_by(Category.sort_order).all()

    tab_in, tab_hist = st.tabs(["Proses Penerimaan", "Riwayat"])

    with tab_in:
        # Hanya SJ belum diterima (pending + belum ada receiving)
        pending_q = (
            db.query(Pickup)
            .filter(Pickup.status == PickupStatus.PENDING.value)
            .order_by(Pickup.pickup_date.desc())
            .all()
        )
        pending = []
        for p in pending_q:
            if db.query(Receiving).filter(Receiving.pickup_id == p.id).first():
                continue
            pending.append(p)

        st.caption(f"Daftar murni **belum diterima**: {len(pending)} SJ")
        if not pending:
            st.info("Tidak ada SJ pending. Yang sudah diterima hanya ada di tab Riwayat.")
        elif not categories:
            st.error("Belum ada kategori aktif. Atur di Master Data.")
        else:
            opts = {
                f"{p.sj_number} | {p.farm_name} | {p.tray_count} tray | {p.pickup_date}": p.id
                for p in pending
            }
            label = st.selectbox("Pilih Surat Jalan (belum diterima)", list(opts.keys()))
            pickup_id = opts[label]
            pickup = db.get(Pickup, pickup_id)

            # Guard: already received / status berubah
            existing = db.query(Receiving).filter(Receiving.pickup_id == pickup_id).first()
            if existing or not pickup or pickup.status != PickupStatus.PENDING.value:
                st.error("Pickup ini sudah diproses / hilang dari antrean. Refresh halaman.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Kebun", pickup.farm_name)
                c2.metric("Tray", pickup.tray_count)
                c3.metric("Driver", pickup.driver.name if pickup.driver else "-")
                if pickup.photo_path:
                    try:
                        st.image(pickup.photo_path, caption="Foto SJ", width=280)
                    except Exception:
                        st.caption(f"Foto: {pickup.photo_path}")

                st.divider()
                total_kg = st.number_input(
                    "Total kg hasil timbang *",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.1f",
                )
                st.caption("Contoh desimal: ketik `12.5` (pakai titik).")

                st.markdown(f"**Dicek oleh:** {user['name']} *(otomatis dari akun login)*")
                notes = st.text_area("Catatan penerimaan")

                st.subheader("Sortir per Kategori")
                st.caption(
                    f"Toleransi balance: **±{tolerance:g} kg** "
                    f"(atur di Master Data → Pengaturan). Desimal pakai titik, contoh `3.5`"
                )
                sort_vals = {}
                cols = st.columns(len(categories))
                for i, cat in enumerate(categories):
                    with cols[i]:
                        sort_vals[cat.id] = st.number_input(
                            f"{cat.name} (kg)",
                            min_value=0.0,
                            value=0.0,
                            step=1.0,
                            format="%.1f",
                            key=f"sort_{cat.id}",
                        )

                sorted_total = sum(sort_vals.values())
                diff = abs(sorted_total - total_kg)
                has_qty = total_kg > 0 and sorted_total > 0
                balanced = has_qty and diff <= tolerance
                is_owner = user["role"] in ("owner", "admin")
                # Sorter: hanya jika balance. Owner: boleh override selisih di luar toleransi.
                can_save = has_qty and st.session_state.recv_lock != pickup_id and (
                    balanced or is_owner
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Timbang", f"{total_kg:g} kg")
                m2.metric("Total Sortir", f"{sorted_total:g} kg")
                m3.metric("Selisih", f"{diff:g} kg")

                if balanced:
                    st.markdown(
                        f'<div class="balance-ok">✅ BALANCE OK '
                        f'(selisih {diff:g} kg ≤ toleransi {tolerance:g} kg)</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="balance-bad">❌ TIDAK BALANCE '
                        f'(selisih {diff:g} kg &gt; toleransi {tolerance:g} kg)</div>',
                        unsafe_allow_html=True,
                    )
                    if is_owner:
                        st.warning(
                            "Owner boleh **override** simpan di luar toleransi "
                            "(wajib konfirmasi + tercatat di log)."
                        )
                    else:
                        st.error(
                            f"Sorter tidak bisa simpan jika selisih > ±{tolerance:g} kg. "
                            "Minta owner atur toleransi di Master Data, atau owner yang simpan/override."
                        )

                if st.session_state.recv_lock == pickup_id:
                    st.success("Penerimaan ini sudah disimpan di sesi ini. Pilih SJ lain jika perlu.")
                elif st.button(
                    "Simpan Penerimaan & Masukkan Stok",
                    type="primary",
                    disabled=not can_save,
                    use_container_width=True,
                ):
                    st.session_state.recv_confirm = {
                        "pickup_id": pickup_id,
                        "total_kg": float(total_kg),
                        "sort_vals": {str(k): float(v) for k, v in sort_vals.items()},
                        "notes": notes or "",
                        "sj": pickup.sj_number,
                        "balanced": balanced,
                        "diff": float(diff),
                        "tolerance": float(tolerance),
                    }
                    st.rerun()

                # Confirmation dialog
                conf = st.session_state.recv_confirm
                if conf and conf.get("pickup_id") == pickup_id:
                    extra = ""
                    if not conf.get("balanced"):
                        extra = (
                            f"\n\n⚠️ **OVERRIDE TIDAK BALANCE** — selisih {conf.get('diff', 0):g} kg "
                            f"> toleransi ±{conf.get('tolerance', 0):g} kg. Hanya owner."
                        )
                    st.warning(
                        f"**Konfirmasi simpan SJ {conf['sj']}?**\n\n"
                        f"Total: {conf['total_kg']:g} kg · "
                        f"Sortir: {sum(conf['sort_vals'].values()):g} kg"
                        f"{extra}\n\n"
                        "Pastikan data sudah benar. Setelah disimpan **tidak bisa submit ulang**."
                    )
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Ya, Simpan Sekarang", type="primary", use_container_width=True):
                            if not conf.get("balanced") and user["role"] not in ("owner", "admin"):
                                st.session_state.recv_confirm = None
                                flash_error("Hanya owner yang boleh override tidak balance.")
                                st.rerun()
                            p2 = db.get(Pickup, pickup_id)
                            exists = db.query(Receiving).filter(Receiving.pickup_id == pickup_id).first()
                            if not p2 or p2.status != PickupStatus.PENDING.value or exists:
                                st.session_state.recv_confirm = None
                                flash_error("Gagal: pickup sudah diproses / sudah tersimpan.")
                                st.rerun()
                            if st.session_state.recv_lock == pickup_id:
                                st.session_state.recv_confirm = None
                                flash_error("Sudah tersimpan, tidak disimpan lagi.")
                                st.rerun()

                            total = float(conf["total_kg"])
                            svals = {int(k): float(v) for k, v in conf["sort_vals"].items()}
                            is_bal = bool(conf.get("balanced"))
                            note_extra = conf["notes"] or ""
                            if not is_bal:
                                note_extra = (
                                    (note_extra + " | " if note_extra else "")
                                    + f"OVERRIDE selisih {conf.get('diff', 0):g}kg "
                                    f"(tol ±{conf.get('tolerance', 0):g}kg) oleh {user['name']}"
                                )
                            recv = Receiving(
                                pickup_id=pickup_id,
                                total_kg=total,
                                checked_by=user["name"],
                                check_date=datetime.utcnow(),
                                notes=note_extra or None,
                                is_balanced=is_bal,
                            )
                            db.add(recv)
                            db.flush()
                            for cat_id, kg in svals.items():
                                if kg <= 0:
                                    continue
                                pct = (kg / total * 100.0) if total else 0.0
                                db.add(SortingDetail(
                                    receiving_id=recv.id,
                                    category_id=cat_id,
                                    kg=float(kg),
                                    percentage=round(pct, 2),
                                ))
                                db.add(InventoryMovement(
                                    category_id=cat_id,
                                    movement_type=MovementType.IN_SORTING.value,
                                    qty_kg=float(kg),
                                    ref_type="receiving",
                                    ref_id=recv.id,
                                    notes=f"SJ {conf['sj']}",
                                    created_by=user["name"],
                                ))
                            p2.status = PickupStatus.RECEIVED.value
                            write_log(
                                db, user,
                                "receiving.create" if is_bal else "receiving.override",
                                f"Penerimaan SJ {conf['sj']} total {total:g} kg"
                                + ("" if is_bal else f" OVERRIDE selisih {conf.get('diff', 0):g}kg"),
                                entity_type="receiving", entity_id=recv.id,
                                detail=str(svals),
                            )
                            db.commit()
                            st.session_state.recv_lock = pickup_id
                            st.session_state.recv_confirm = None
                            flash_success(f"✅ Berhasil! SJ {conf['sj']} tersimpan. Stok diperbarui.")
                            st.rerun()
                    with b2:
                        if st.button("❌ Batal", use_container_width=True):
                            st.session_state.recv_confirm = None
                            st.rerun()

    with tab_hist:
        recvs = db.query(Receiving).order_by(Receiving.created_at.desc()).limit(50).all()
        if not recvs:
            st.info("Belum ada riwayat penerimaan.")
        else:
            rows = []
            for r in recvs:
                details = ", ".join(
                    f"{d.category.name}: {d.kg:g}kg ({d.percentage or 0:.0f}%)"
                    for d in r.sorting_details if d.category
                )
                rows.append({
                    "ID": r.id,
                    "SJ": r.pickup.sj_number if r.pickup else "-",
                    "Kebun": r.pickup.farm_name if r.pickup else "-",
                    "Total kg": r.total_kg,
                    "Dicek": r.checked_by or "-",
                    "Balance": "Ya" if r.is_balanced else "Tidak",
                    "Detail": details,
                    "Waktu": str(r.check_date or r.created_at)[:19],
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

            if user["role"] in ("owner", "admin") and recvs:
                st.subheader("Hapus Riwayat (Owner)")
                del_opts = {
                    f"#{r.id} SJ {r.pickup.sj_number if r.pickup else '-'} — {r.total_kg:g} kg": r.id
                    for r in recvs
                }
                del_label = st.selectbox("Pilih riwayat", list(del_opts.keys()), key="del_recv_sel")
                if st.button("Hapus riwayat + rollback stok", type="secondary"):
                    rid = del_opts[del_label]
                    r = db.get(Receiving, rid)
                    if r:
                        sj = r.pickup.sj_number if r.pickup else str(rid)
                        pickup_id_saved = r.pickup_id
                        # reverse stock movements
                        movs = db.query(InventoryMovement).filter_by(
                            ref_type="receiving", ref_id=r.id
                        ).all()
                        for m in movs:
                            db.add(InventoryMovement(
                                category_id=m.category_id,
                                movement_type=MovementType.ADJUSTMENT.value,
                                qty_kg=-float(m.qty_kg),
                                ref_type="receiving_delete",
                                ref_id=r.id,
                                notes=f"Rollback hapus penerimaan SJ {sj}",
                                created_by=user["name"],
                            ))
                            db.delete(m)
                        for d in list(r.sorting_details):
                            db.delete(d)
                        if r.pickup:
                            r.pickup.status = PickupStatus.PENDING.value
                        write_log(
                            db, user, "receiving.delete",
                            f"Hapus penerimaan SJ {sj}",
                            entity_type="receiving", entity_id=rid,
                        )
                        db.delete(r)
                        db.commit()
                        if st.session_state.recv_lock == pickup_id_saved:
                            st.session_state.recv_lock = None
                        flash_success("Riwayat dihapus, stok di-rollback, pickup kembali pending.", balloons=False)
                        st.rerun()
finally:
    db.close()
