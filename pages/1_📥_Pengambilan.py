"""Modul Pengambilan (Driver) — form ringkas 2 kebun, auto 2 SJ."""
import json
import os
from datetime import date, datetime

import streamlit as st

from auth_utils import require_login, show_user_sidebar, flash_success, flash_error
from database import (
    get_db, Pickup, User, PickupStatus, ChangeRequest, write_log,
)

FARMS = ["RED HARVEST 1", "RED HARVEST 2"]
FARM_CODES = {"RED HARVEST 1": "RH1", "RED HARVEST 2": "RH2"}


def farm_code(farm_name: str) -> str:
    return FARM_CODES.get(farm_name, "XX")


def make_sj_number(pickup_date: date, farm_name: str, seq: int = 1) -> str:
    base = f"{pickup_date.day:02d}{pickup_date.month:02d}{pickup_date.year}{farm_code(farm_name)}"
    return base if seq <= 1 else f"{base}-{seq:02d}"


st.set_page_config(page_title="Pengambilan", page_icon="📥", layout="wide")
user = require_login(["owner", "admin", "driver"])
show_user_sidebar()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.markdown("## 📥 Pengambilan dari Kebun")
st.caption("Isi tray per kebun → 1 submit = auto 2 SJ (1 kebun / 1 hari)")
if user["role"] == "driver":
    st.info("Driver tidak bisa mengedit data tersimpan. Ajukan **permintaan koreksi** jika ada kesalahan.")

db = get_db()
try:
    is_owner = user["role"] in ("owner", "admin")
    tabs = ["Form Pickup", "Riwayat Pickup", "Permintaan Koreksi"]
    if is_owner:
        tabs.append("Approve Owner")
    tab_objs = st.tabs(tabs)
    tab_form, tab_list, tab_req = tab_objs[0], tab_objs[1], tab_objs[2]
    tab_approve = tab_objs[3] if is_owner else None

    with tab_form:
        pickup_date = st.date_input("Tanggal Pickup", value=date.today())

        # status existing per kebun (sebelum input → disable field)
        blocked = {}
        for farm in FARMS:
            exists = (
                db.query(Pickup)
                .filter(
                    Pickup.pickup_date == pickup_date,
                    Pickup.farm_name == farm,
                    Pickup.status != PickupStatus.CANCELLED.value,
                )
                .first()
            )
            if exists:
                blocked[farm] = exists

        st.markdown("### Tray per kebun")
        c1, c2 = st.columns(2)
        trays = {}
        with c1:
            farm = FARMS[0]
            st.markdown(f"**{farm}**")
            if farm in blocked:
                p = blocked[farm]
                st.error(f"Sudah ada · SJ `{p.sj_number}` · {p.tray_count} tray · **tidak bisa input lagi**")
                trays[farm] = 0
            else:
                trays[farm] = st.number_input(
                    f"Jumlah Tray — {farm}",
                    min_value=0,
                    value=0,
                    step=1,
                    key="tray_rh1",
                )
                st.caption(f"SJ: `{make_sj_number(pickup_date, farm)}`")
        with c2:
            farm = FARMS[1]
            st.markdown(f"**{farm}**")
            if farm in blocked:
                p = blocked[farm]
                st.error(f"Sudah ada · SJ `{p.sj_number}` · {p.tray_count} tray · **tidak bisa input lagi**")
                trays[farm] = 0
            else:
                trays[farm] = st.number_input(
                    f"Jumlah Tray — {farm}",
                    min_value=0,
                    value=0,
                    step=1,
                    key="tray_rh2",
                )
                st.caption(f"SJ: `{make_sj_number(pickup_date, farm)}`")

        total_tray = int(trays[FARMS[0]]) + int(trays[FARMS[1]])
        st.metric("TOTAL Tray (yang akan disimpan)", total_tray)

        if len(blocked) == 2:
            st.error("Kedua kebun sudah ada pickup di tanggal ini. Tidak bisa input lagi.")
        elif blocked:
            st.warning("Kebun yang sudah terdaftar dikunci. Hanya kebun kosong yang bisa diisi.")

        notes = st.text_input("Catatan (opsional)", disabled=len(blocked) == 2)
        photo = st.file_uploader(
            "Foto (opsional, 1 foto untuk batch)",
            type=["jpg", "jpeg", "png", "webp"],
            disabled=len(blocked) == 2,
        )

        if is_owner:
            drivers = db.query(User).filter(User.role == "driver", User.is_active == True).all()
            driver_opts = {f"{d.name} ({d.username})": d.id for d in drivers}
            if not driver_opts:
                driver_opts = {f"{user['name']} (saya)": user["id"]}
            driver_label = st.selectbox("Driver", list(driver_opts.keys()), disabled=len(blocked) == 2)
            driver_id = driver_opts[driver_label]
        else:
            driver_id = user["id"]

        to_create = [f for f in FARMS if int(trays[f]) > 0 and f not in blocked]
        if not to_create and total_tray == 0 and len(blocked) < 2:
            st.caption("Isi tray minimal 1 kebun (yang belum terdaftar) untuk generate SJ.")

        if st.button(
            f"Simpan Pickup ({len(to_create)} SJ)",
            type="primary",
            use_container_width=True,
            disabled=len(to_create) == 0,
        ):
            created = []
            photo_path = None
            if photo is not None:
                ext = os.path.splitext(photo.name)[1] or ".jpg"
                fname = f"batch_{pickup_date}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
                photo_path = os.path.join(UPLOAD_DIR, fname)
                with open(photo_path, "wb") as f:
                    f.write(photo.getbuffer())

            for farm in to_create:
                exists = (
                    db.query(Pickup)
                    .filter(
                        Pickup.pickup_date == pickup_date,
                        Pickup.farm_name == farm,
                        Pickup.status != PickupStatus.CANCELLED.value,
                    )
                    .first()
                )
                if exists:
                    continue
                sj_number = make_sj_number(pickup_date, farm, seq=1)
                while db.query(Pickup).filter(Pickup.sj_number == sj_number).first():
                    sj_number = f"{sj_number}-X"
                pickup = Pickup(
                    driver_id=driver_id,
                    farm_name=farm,
                    farm_location=None,
                    pickup_date=pickup_date,
                    tray_count=int(trays[farm]),
                    photo_path=photo_path,
                    sj_number=sj_number,
                    notes=(notes or "").strip() or None,
                    status=PickupStatus.PENDING.value,
                )
                db.add(pickup)
                db.flush()
                write_log(
                    db, user, "pickup.create",
                    f"Buat pickup SJ {sj_number} ({farm}, {trays[farm]} tray)",
                    entity_type="pickup", entity_id=pickup.id,
                )
                created.append(sj_number)

            if created:
                db.commit()
                flash_success(f"✅ Pickup tersimpan: {', '.join(created)} · Total tray {sum(int(trays[f]) for f in to_create)}")
            else:
                flash_error("Tidak ada pickup baru (sudah ada / tray 0).")
            st.rerun()

    with tab_list:
        from database import Receiving, InventoryMovement, SortingDetail, MovementType

        q = db.query(Pickup).order_by(Pickup.created_at.desc())
        if user["role"] == "driver":
            q = q.filter(Pickup.driver_id == user["id"])
        rows = q.limit(100).all()
        if not rows:
            st.info("Belum ada data pickup.")
        else:
            st.dataframe([{
                "ID": p.id,
                "SJ": p.sj_number,
                "Kebun": p.farm_name,
                "Tray": p.tray_count,
                "Driver": p.driver.name if p.driver else "-",
                "Tanggal": str(p.pickup_date),
                "Status": p.status,
            } for p in rows], use_container_width=True, hide_index=True)

            if is_owner:
                st.subheader("Kelola Pickup (Owner — tanpa approve, wajib log)")
                st.caption("Edit / hapus langsung. Semua aksi tercatat di Log Aktivitas. Log **tidak bisa dihapus**.")

                pick_opts = {
                    f"#{p.id} {p.sj_number} | {p.farm_name} | {p.tray_count} tray | {p.status}": p.id
                    for p in rows
                }
                sel = st.selectbox("Pilih baris", list(pick_opts.keys()), key="owner_pick_row")
                p = db.get(Pickup, pick_opts[sel])
                if p:
                    has_recv = db.query(Receiving).filter(Receiving.pickup_id == p.id).first()
                    act = st.radio(
                        "Aksi",
                        ["Edit", "Batalkan (pending)", "Hapus permanen"],
                        horizontal=True,
                        key="owner_pick_act",
                    )

                    if act == "Edit":
                        with st.form("owner_edit_pickup"):
                            new_farm = st.selectbox(
                                "Kebun",
                                FARMS,
                                index=FARMS.index(p.farm_name) if p.farm_name in FARMS else 0,
                            )
                            new_date = st.date_input("Tanggal", value=p.pickup_date)
                            new_tray = st.number_input("Tray", min_value=1, value=int(p.tray_count), step=1)
                            new_notes = st.text_input("Catatan", value=p.notes or "")
                            new_status = st.selectbox(
                                "Status",
                                ["pending", "received", "cancelled"],
                                index=["pending", "received", "cancelled"].index(p.status)
                                if p.status in ("pending", "received", "cancelled") else 0,
                            )
                            if st.form_submit_button("Simpan perubahan", type="primary"):
                                # cek bentrok 1 kebun/1 hari jika ganti farm/date
                                conflict = (
                                    db.query(Pickup)
                                    .filter(
                                        Pickup.id != p.id,
                                        Pickup.pickup_date == new_date,
                                        Pickup.farm_name == new_farm,
                                        Pickup.status != PickupStatus.CANCELLED.value,
                                    )
                                    .first()
                                )
                                if conflict and new_status != PickupStatus.CANCELLED.value:
                                    flash_error(
                                        f"Bentrok: {new_farm} sudah ada SJ {conflict.sj_number} di {new_date}."
                                    )
                                    st.rerun()
                                before = {
                                    "farm": p.farm_name,
                                    "date": str(p.pickup_date),
                                    "tray": p.tray_count,
                                    "status": p.status,
                                    "notes": p.notes,
                                }
                                p.farm_name = new_farm
                                p.pickup_date = new_date
                                p.tray_count = int(new_tray)
                                p.notes = new_notes or None
                                p.status = new_status
                                # regenerasi SJ jika farm/date berubah & masih format lama
                                p.sj_number = make_sj_number(new_date, new_farm, seq=1)
                                # pastikan unique
                                seq = 1
                                while (
                                    db.query(Pickup)
                                    .filter(Pickup.sj_number == p.sj_number, Pickup.id != p.id)
                                    .first()
                                ):
                                    seq += 1
                                    p.sj_number = make_sj_number(new_date, new_farm, seq=seq)
                                write_log(
                                    db, user, "pickup.edit",
                                    f"Owner edit pickup #{p.id} → SJ {p.sj_number}",
                                    entity_type="pickup", entity_id=p.id,
                                    detail=json.dumps({"before": before, "after": {
                                        "farm": p.farm_name,
                                        "date": str(p.pickup_date),
                                        "tray": p.tray_count,
                                        "status": p.status,
                                        "sj": p.sj_number,
                                        "notes": p.notes,
                                    }}),
                                )
                                db.commit()
                                flash_success(f"Pickup #{p.id} diupdate · SJ {p.sj_number}")
                                st.rerun()

                    elif act == "Batalkan (pending)":
                        if p.status != PickupStatus.PENDING.value:
                            st.warning("Hanya status pending yang dibatalkan lewat aksi ini. Gunakan Edit untuk status lain.")
                        elif st.button("Konfirmasi batalkan", type="secondary", key="btn_cancel_p"):
                            p.status = PickupStatus.CANCELLED.value
                            write_log(
                                db, user, "pickup.cancel",
                                f"Batalkan pickup SJ {p.sj_number}",
                                entity_type="pickup", entity_id=p.id,
                            )
                            db.commit()
                            flash_success("Pickup dibatalkan.", balloons=False)
                            st.rerun()

                    else:  # Hapus permanen
                        st.error(
                            "Hapus permanen menghapus pickup. "
                            + ("Ada penerimaan terkait → stok di-rollback dulu. " if has_recv else "")
                            + "Log tetap ada (tidak dihapus)."
                        )
                        if st.button("Ya, hapus permanen", type="primary", key="btn_del_p"):
                            sj = p.sj_number
                            pid = p.id
                            if has_recv:
                                recv = has_recv
                                movs = db.query(InventoryMovement).filter_by(
                                    ref_type="receiving", ref_id=recv.id
                                ).all()
                                for m in movs:
                                    db.add(InventoryMovement(
                                        category_id=m.category_id,
                                        movement_type=MovementType.ADJUSTMENT.value,
                                        qty_kg=-float(m.qty_kg),
                                        ref_type="pickup_delete",
                                        ref_id=pid,
                                        notes=f"Rollback hapus pickup SJ {sj}",
                                        created_by=user["name"],
                                    ))
                                    db.delete(m)
                                for d in list(recv.sorting_details):
                                    db.delete(d)
                                db.delete(recv)
                            write_log(
                                db, user, "pickup.delete",
                                f"Owner hapus pickup SJ {sj}",
                                entity_type="pickup", entity_id=pid,
                                detail=json.dumps({
                                    "sj": sj,
                                    "farm": p.farm_name,
                                    "tray": p.tray_count,
                                    "status": p.status,
                                    "had_receiving": bool(has_recv),
                                }),
                            )
                            db.delete(p)
                            db.commit()
                            flash_success(f"Pickup SJ {sj} dihapus. Log tetap tersimpan.", balloons=False)
                            st.rerun()

    with tab_req:
        st.subheader("Ajukan Koreksi Data")
        q = db.query(Pickup).order_by(Pickup.created_at.desc())
        if user["role"] == "driver":
            q = q.filter(Pickup.driver_id == user["id"])
        pickups = q.limit(50).all()
        if not pickups:
            st.info("Belum ada pickup.")
        else:
            opts = {
                f"{p.sj_number} | {p.farm_name} | {p.tray_count} tray | {p.status}": p.id
                for p in pickups if p.status != PickupStatus.CANCELLED.value
            }
            if opts:
                label = st.selectbox("Pilih pickup", list(opts.keys()), key="req_pickup")
                p = db.get(Pickup, opts[label])
                req_type = st.selectbox("Jenis permintaan", ["edit", "cancel"])
                new_tray = None
                new_farm = None
                new_notes = None
                if req_type == "edit":
                    new_farm = st.selectbox(
                        "Kebun baru", FARMS,
                        index=FARMS.index(p.farm_name) if p.farm_name in FARMS else 0,
                    )
                    new_tray = st.number_input("Tray baru", min_value=1, value=int(p.tray_count), step=1)
                    new_notes = st.text_input("Catatan baru", value=p.notes or "")
                reason = st.text_area("Alasan koreksi *")
                if st.button("Kirim permintaan ke Owner", type="primary"):
                    if not reason.strip():
                        st.error("Alasan wajib diisi.")
                    else:
                        payload = {}
                        if req_type == "edit":
                            payload = {
                                "farm_name": new_farm,
                                "tray_count": int(new_tray),
                                "notes": new_notes,
                            }
                        cr = ChangeRequest(
                            entity_type="pickup",
                            entity_id=p.id,
                            request_type=req_type,
                            payload=json.dumps(payload) if payload else None,
                            reason=reason.strip(),
                            status="pending",
                            requested_by_id=user["id"],
                            requested_by_name=user["name"],
                        )
                        db.add(cr)
                        db.flush()
                        write_log(
                            db, user, "change_request.create",
                            f"Request {req_type} pickup SJ {p.sj_number}: {reason.strip()}",
                            entity_type="change_request", entity_id=cr.id,
                        )
                        db.commit()
                        flash_success("Permintaan terkirim. Menunggu approve owner.")
                        st.rerun()

        st.divider()
        st.subheader("Status permintaan saya")
        my_req = (
            db.query(ChangeRequest)
            .filter(ChangeRequest.requested_by_id == user["id"])
            .order_by(ChangeRequest.created_at.desc())
            .limit(30)
            .all()
        )
        if my_req:
            st.dataframe([{
                "ID": r.id,
                "Tipe": r.request_type,
                "Entity": f"{r.entity_type}#{r.entity_id}",
                "Status": r.status,
                "Alasan": r.reason,
                "Reviewer": r.reviewed_by_name or "-",
                "Waktu": str(r.created_at)[:19],
            } for r in my_req], use_container_width=True, hide_index=True)
        else:
            st.caption("Belum ada permintaan.")

    if tab_approve is not None:
        with tab_approve:
            st.subheader("Approve / Tolak Permintaan")
            pending_req = (
                db.query(ChangeRequest)
                .filter(ChangeRequest.status == "pending", ChangeRequest.entity_type == "pickup")
                .order_by(ChangeRequest.created_at.asc())
                .all()
            )
            if not pending_req:
                st.info("Tidak ada permintaan pickup pending.")
            else:
                for r in pending_req:
                    with st.expander(f"#{r.id} {r.request_type.upper()} pickup#{r.entity_id} — {r.requested_by_name}"):
                        st.write(f"**Alasan:** {r.reason}")
                        st.write(f"**Payload:** {r.payload or '-'}")
                        note = st.text_input("Catatan reviewer", key=f"note_{r.id}")
                        a1, a2 = st.columns(2)
                        with a1:
                            if st.button("Approve", key=f"ap_{r.id}", type="primary"):
                                entity = db.get(Pickup, r.entity_id)
                                if entity:
                                    if r.request_type == "cancel":
                                        entity.status = PickupStatus.CANCELLED.value
                                    elif r.request_type == "edit" and r.payload:
                                        data = json.loads(r.payload)
                                        if "farm_name" in data:
                                            entity.farm_name = data["farm_name"]
                                        if "tray_count" in data:
                                            entity.tray_count = int(data["tray_count"])
                                        if "notes" in data:
                                            entity.notes = data["notes"]
                                r.status = "approved"
                                r.reviewed_by_id = user["id"]
                                r.reviewed_by_name = user["name"]
                                r.review_note = note or None
                                r.reviewed_at = datetime.utcnow()
                                write_log(
                                    db, user, "change_request.approve",
                                    f"Approve request #{r.id}",
                                    entity_type="change_request", entity_id=r.id,
                                    detail=r.payload,
                                )
                                db.commit()
                                flash_success(f"Request #{r.id} disetujui.")
                                st.rerun()
                        with a2:
                            if st.button("Tolak", key=f"rj_{r.id}"):
                                r.status = "rejected"
                                r.reviewed_by_id = user["id"]
                                r.reviewed_by_name = user["name"]
                                r.review_note = note or None
                                r.reviewed_at = datetime.utcnow()
                                write_log(
                                    db, user, "change_request.reject",
                                    f"Tolak request #{r.id}",
                                    entity_type="change_request", entity_id=r.id,
                                )
                                db.commit()
                                flash_success(f"Request #{r.id} ditolak.", balloons=False)
                                st.rerun()
finally:
    db.close()
