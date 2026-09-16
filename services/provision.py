# services/provision.py v16
# - Overlap model for server switch (old client kept until old_stop_time)
# - Enqueues old client into ServerClientDeletion
# - Always regenerates settings + QR
# - Uses notifier (enqueue_notification + create_pg_event)

import logging
import os
from datetime import datetime, timezone

import qrcode
from sqlalchemy import select, and_

from db.async_db import SessionLocal
from db.models import (
    SubscriptionTransaction,
    AllInvoices,
    InvoiceItems,
    AllUsers,
    UserSubscription,
    AllServers,
    ServerClientDeletion,
)
from services.server_api import (
    AsyncApi,
    add_client_to_3xui_server,
    update_existing_3xui_client,
)
from services.helpers import get_servers_list
from services.exceptions import ProvisioningError, NoServerAvailableError
from services.helpers import enqueue_notification
from services.events import create_pg_event
from config import SUBS_PERIOD_DAYS  # can be None or int

logger = logging.getLogger(__name__)

QRS_BASE_DIR = "qrs/subs_qrs"


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _add_one_month(dt: datetime) -> datetime:
    year = dt.year
    month = dt.month + 1
    if month > 12:
        month = 1
        year += 1
    day = dt.day
    while True:
        try:
            return dt.replace(year=year, month=month, day=day)
        except ValueError:
            day -= 1
            if day < 1:
                return dt.replace(year=year, month=month, day=1)


def _compute_new_end_ms(base_start_ms: int) -> int:
    if SUBS_PERIOD_DAYS and SUBS_PERIOD_DAYS > 0:
        period_ms = SUBS_PERIOD_DAYS * 24 * 60 * 60 * 1000
        return base_start_ms + period_ms

    base_dt = datetime.fromtimestamp(base_start_ms / 1000, tz=timezone.utc)
    new_dt = _add_one_month(base_dt)
    return int(new_dt.timestamp() * 1000)


async def _find_client_on_server(async_api: AsyncApi, new_client_email: str):
    inbounds = await async_api.inbound.get_list()
    for inbound in inbounds:
        clients = getattr(inbound.settings, "clients", []) if hasattr(inbound, "settings") else []
        for client in clients:
            if getattr(client, "email", None) == new_client_email:
                server_end = (
                    getattr(client, "expiry", None)
                    or getattr(client, "stop", None)
                    or getattr(client, "expire_at", None)
                )
                try:
                    server_end_ms = int(server_end) if server_end is not None else None
                except Exception:
                    server_end_ms = None
                return getattr(client, "id", None), server_end_ms
    return None, None


def _build_settings_string(inbounds, user_email: str, vpn_ip: str) -> str:
    for inbound in inbounds:
        clients = getattr(inbound.settings, "clients", [])
        for client in clients:
            if getattr(client, "email", None) == user_email:
                pbk = inbound.stream_settings.reality_settings["settings"]["publicKey"]
                fp = inbound.stream_settings.reality_settings["settings"]["fingerprint"]
                sni = inbound.stream_settings.reality_settings["serverNames"][0]
                sid = inbound.stream_settings.reality_settings["shortIds"][0]

                return (
                    f"{inbound.protocol}://{client.id}@{vpn_ip}:{inbound.port}"
                    f"?type={inbound.stream_settings.network}"
                    f"&security={inbound.stream_settings.security}"
                    f"&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F"
                    f"&flow={client.flow}#{client.email}"
                )

    raise ProvisioningError(f"user {user_email} not found in inbound clients")


def _get_or_create_settings_qr(
    settings_string: str,
    country_id: int,
    server_id: int,
    user_email: str,
    old_settings: str | None,
    old_qr_path: str | None,
) -> str:
    folder = os.path.join(QRS_BASE_DIR, str(country_id), str(server_id))
    os.makedirs(folder, exist_ok=True)

    img_name = f"{user_email}.png"
    img_path = os.path.join(folder, img_name)

    if old_qr_path and (old_qr_path != img_path) and old_settings and (old_settings != settings_string):
        try:
            if os.path.exists(old_qr_path):
                os.remove(old_qr_path)
        except Exception:
            logger.exception("Failed to delete old QR %s", old_qr_path)

    if os.path.exists(img_path) and old_settings == settings_string:
        return img_path

    img = qrcode.make(settings_string)
    img.save(img_path)

    return img_path


async def _get_or_create_subscription(
    session,
    user_id: int,
    slot_number: int,
) -> UserSubscription:
    r_sub = await session.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.slot_number == slot_number,
        )
    )
    sub = r_sub.scalar_one_or_none()
    if sub:
        return sub

    sub = UserSubscription(
        user_id=user_id,
        slot_number=slot_number,
        server_country_id=None,
        server_id=None,
        autopay_id=0,
        stop_time=None,
        next_server_id=0,
        pending=False,
        settings_string=None,
        qr_path=None,
    )
    session.add(sub)
    await session.flush()
    return sub


async def _choose_server_for_country(
    session,
    country_id: int,
) -> AllServers:
    q = (
        select(AllServers)
        .where(
            and_(
                AllServers.country_id == country_id,
                AllServers.all_subscriptions < AllServers.max_subscriptions,
            )
        )
        .order_by(AllServers.all_subscriptions.asc())
        .with_for_update(skip_locked=True)
    )
    r = await session.execute(q)
    server = r.scalars().first()
    if not server:
        raise NoServerAvailableError(
            f"No server available for country_id={country_id}",
            server_country=country_id,
        )
    return server


async def provision_subscription_for_user(tx_id: int) -> dict:
    """
    v16:
    - Overlap model for server switch:
      * new client on new server immediately
      * old client kept until old_stop_time
      * old client enqueued into ServerClientDeletion
    - Always regenerates settings + QR
    - Uses notifier for subscription_provisioned / subscription_server_changed
    """
    logger.info("provision_subscription_for_user start tx=%s", tx_id)

    async with SessionLocal() as session:
        async with session.begin():
            r_tx = await session.execute(
                select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
            )
            tx = r_tx.scalar_one_or_none()
            if not tx:
                raise ProvisioningError("tx not found")

            if not tx.provider_invoice_id:
                raise ProvisioningError("tx has no provider_invoice_id")

            r_inv = await session.execute(
                select(AllInvoices).where(AllInvoices.invoice_id == tx.provider_invoice_id)
            )
            invoice = r_inv.scalar_one_or_none()
            if not invoice:
                raise ProvisioningError("invoice not found for tx")

            r_items = await session.execute(
                select(InvoiceItems).where(InvoiceItems.invoice_id == tx.provider_invoice_id)
            )
            items = r_items.scalars().all()
            if not items:
                raise ProvisioningError("no invoice_items for subscription invoice")

            r_user = await session.execute(
                select(AllUsers)
                .where(AllUsers.user_id == invoice.user_id)
                .with_for_update()
            )
            user = r_user.scalar_one_or_none()
            if not user:
                raise ProvisioningError("user not found for invoice")

            user_id = user.user_id

            servers_cfg = get_servers_list()
            api_cache: dict[int, AsyncApi] = {}

            now = _now_dt()
            now_ms = int(now.timestamp() * 1000)

            slots_result: dict[str, dict] = {}

            for it in items:
                slot = it.acc_number
                server_country_id = getattr(it, "server_country_id", None)

                if slot < 1 or slot > 5:
                    raise ProvisioningError(f"invalid acc_number in invoice_items: {slot}")

                if not server_country_id:
                    raise ProvisioningError(f"no server_country_id for acc_number={slot}")

                # 1. Choose server in DB with row lock
                server_row = await _choose_server_for_country(session, server_country_id)
                server_id = server_row.server_id

                if server_id not in servers_cfg:
                    raise ProvisioningError(f"server_id {server_id} not in config")

                # 2. Persist chosen server_id into invoice item
                it.server_id = server_id
                session.add(it)

                # 3. Load or create subscription row
                sub = await _get_or_create_subscription(session, user_id, slot)

                old_server_id = sub.server_id
                old_stop_time = sub.stop_time

                # 4. Compute new stop_time
                current_stop = sub.stop_time
                if current_stop and current_stop > now_ms:
                    base_start_ms = current_stop
                else:
                    base_start_ms = now_ms

                new_end_ms = _compute_new_end_ms(base_start_ms)

                # 5. Overlap model: handle server switch vs same server
                if old_server_id and old_server_id != server_id and old_stop_time:
                    # enqueue old client for deletion after old_stop_time
                    deletion = ServerClientDeletion(
                        user_id=user_id,
                        slot_number=slot,
                        server_id=old_server_id,
                        client_email=f"{user_id}-slot{slot}",
                        delete_not_before_ts=old_stop_time,
                    )
                    session.add(deletion)

                # set new primary server
                sub.server_id = server_id
                sub.server_country_id = server_country_id
                sub.stop_time = new_end_ms
                sub.next_server_id = 0
                sub.pending = False

                # 6. Prepare API client
                if server_id not in api_cache:
                    cfg = servers_cfg[server_id]
                    api = AsyncApi(
                        host=cfg["http"],
                        username=cfg["username"],
                        password=cfg["pass"],
                        token=cfg.get("token"),
                        use_tls_verify=True,
                        custom_certificate_path=cfg.get("sert"),
                    )
                    await api.login()
                    api_cache[server_id] = api
                else:
                    api = api_cache[server_id]

                client_email = f"{user_id}-slot{slot}"

                external_id, server_end_ts = await _find_client_on_server(api, client_email)
                inbounds = await api.inbound.get_list()
                vpn_ip = servers_cfg[server_id].get("ip")

                # 7. Always ensure client has at least new_end_ms, regenerate settings
                if external_id and server_end_ts and server_end_ts >= new_end_ms:
                    settings_string = _build_settings_string(inbounds, client_email, vpn_ip)
                    final_end_ts = server_end_ts
                else:
                    if external_id:
                        now_ms_local = int(_now_dt().timestamp() * 1000)
                        ms_diff = max(new_end_ms - now_ms_local, 0)
                        days_to_extend = max(ms_diff // (24 * 60 * 60 * 1000), 1)
                        await update_existing_3xui_client(api, inbounds, client_email, days_to_extend)
                    else:
                        await add_client_to_3xui_server(api, client_email, new_end_ms, user_id)

                    inbounds_after = await api.inbound.get_list()
                    settings_string = _build_settings_string(inbounds_after, client_email, vpn_ip)

                    external_id_after, server_end_after = await _find_client_on_server(api, client_email)
                    final_end_ts = int(server_end_after) if server_end_after else new_end_ms

                old_settings = sub.settings_string
                old_qr = sub.qr_path

                img_path = _get_or_create_settings_qr(
                    settings_string=settings_string,
                    country_id=server_country_id,
                    server_id=server_id,
                    user_email=client_email,
                    old_settings=old_settings,
                    old_qr_path=old_qr,
                )

                sub.settings_string = settings_string
                sub.qr_path = img_path
                session.add(sub)

                # 8. Increment server load under lock
                server_row.all_subscriptions = (server_row.all_subscriptions or 0) + 1
                session.add(server_row)

                slots_result[str(slot)] = {
                    "server_id": server_id,
                    "end_ts": final_end_ts,
                    "settings_string": settings_string,
                    "img_path": img_path,
                }

                # 9. Notifications
                if old_server_id and old_server_id != server_id and old_stop_time:
                    await enqueue_notification(
                        session=session,
                        user_id=user_id,
                        reason="subscription_server_changed",
                        payload={
                            "slot": slot,
                            "old_server_id": old_server_id,
                            "old_valid_until": old_stop_time,
                            "new_server_id": server_id,
                            "new_settings_string": settings_string,
                            "new_qr_path": img_path,
                        },
                    )
                else:
                    await enqueue_notification(
                        session=session,
                        user_id=user_id,
                        reason="subscription_provisioned",
                        payload={
                            "slot": slot,
                            "server_id": server_id,
                            "settings_string": settings_string,
                            "qr_path": img_path,
                        },
                    )
                await create_pg_event("notify", session=session)

            # Attach slots to tx payload_meta
            r_tx2 = await session.execute(
                select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
            )
            tx2 = r_tx2.scalar_one_or_none()
            if not tx2:
                raise ProvisioningError("tx disappeared during provision")

            meta = tx2.payload_meta or {}
            meta["slots"] = slots_result
            tx2.payload_meta = meta

            await session.flush()

    if not slots_result:
        raise ProvisioningError("no slots processed in provision")

    logger.info(
        "provision_subscription_for_user completed tx=%s slots=%s",
        tx_id,
        list(slots_result.keys()),
    )
    return {"slots": slots_result}


# # services/provision.py v15
# # - Uses AllServers for capacity-aware selection
# # - Uses UserSubscription model
# # - Uses server_country_id to choose server_id
# # - Increments all_subscriptions under row lock
# # - Clean QR handling: per country/server, delete old if settings changed
# # - No money logic here

# import logging
# import os
# from datetime import datetime, timezone

# import qrcode
# from sqlalchemy import select, and_

# from db.async_db import SessionLocal
# from db.models import (
#     SubscriptionTransaction,
#     AllInvoices,
#     InvoiceItems,
#     AllUsers,
#     UserSubscription,
#     AllServers,
# )
# from services.server_api import (
#     AsyncApi,
#     add_client_to_3xui_server,
#     update_existing_3xui_client,
#     get_client_settings_string_and_qr,  # legacy, no longer used
# )
# from services.helpers import get_servers_list
# from services.exceptions import ProvisioningError, NoServerAvailableError
# from config import SUBS_PERIOD_DAYS  # can be None or int

# logger = logging.getLogger(__name__)

# QRS_BASE_DIR = "qrs/subs_qrs"


# def _now_dt() -> datetime:
#     return datetime.now(timezone.utc)


# def _add_one_month(dt: datetime) -> datetime:
#     year = dt.year
#     month = dt.month + 1
#     if month > 12:
#         month = 1
#         year += 1
#     day = dt.day
#     while True:
#         try:
#             return dt.replace(year=year, month=month, day=day)
#         except ValueError:
#             day -= 1
#             if day < 1:
#                 return dt.replace(year=year, month=month, day=1)


# def _compute_new_end_ms(base_start_ms: int) -> int:
#     if SUBS_PERIOD_DAYS and SUBS_PERIOD_DAYS > 0:
#         period_ms = SUBS_PERIOD_DAYS * 24 * 60 * 60 * 1000
#         return base_start_ms + period_ms

#     base_dt = datetime.fromtimestamp(base_start_ms / 1000, tz=timezone.utc)
#     new_dt = _add_one_month(base_dt)
#     return int(new_dt.timestamp() * 1000)


# async def _find_client_on_server(async_api: AsyncApi, new_client_email: str):
#     inbounds = await async_api.inbound.get_list()
#     for inbound in inbounds:
#         clients = getattr(inbound.settings, "clients", []) if hasattr(inbound, "settings") else []
#         for client in clients:
#             if getattr(client, "email", None) == new_client_email:
#                 server_end = (
#                     getattr(client, "expiry", None)
#                     or getattr(client, "stop", None)
#                     or getattr(client, "expire_at", None)
#                 )
#                 try:
#                     server_end_ms = int(server_end) if server_end is not None else None
#                 except Exception:
#                     server_end_ms = None
#                 return getattr(client, "id", None), server_end_ms
#     return None, None


# def _build_settings_string(inbounds, user_email: str, vpn_ip: str) -> str:
#     """
#     Extracts settings string for a given user_email from inbound list.
#     No QR logic here.
#     """
#     for inbound in inbounds:
#         clients = getattr(inbound.settings, "clients", [])
#         for client in clients:
#             if getattr(client, "email", None) == user_email:
#                 pbk = inbound.stream_settings.reality_settings["settings"]["publicKey"]
#                 fp = inbound.stream_settings.reality_settings["settings"]["fingerprint"]
#                 sni = inbound.stream_settings.reality_settings["serverNames"][0]
#                 sid = inbound.stream_settings.reality_settings["shortIds"][0]

#                 return (
#                     f"{inbound.protocol}://{client.id}@{vpn_ip}:{inbound.port}"
#                     f"?type={inbound.stream_settings.network}"
#                     f"&security={inbound.stream_settings.security}"
#                     f"&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F"
#                     f"&flow={client.flow}#{client.email}"
#                 )

#     raise ProvisioningError(f"user {user_email} not found in inbound clients")


# def _get_or_create_settings_qr(
#     settings_string: str,
#     country_id: int,
#     server_id: int,
#     user_email: str,
#     old_settings: str | None,
#     old_qr_path: str | None,
# ) -> str:
#     """
#     Creates or reuses QR code for a subscription.
#     Folder structure:
#         qrs/subs_qrs/{country_id}/{server_id}/{user_email}.png

#     If QR exists but settings_string changed → delete old → generate new.
#     """
#     folder = os.path.join(QRS_BASE_DIR, str(country_id), str(server_id))
#     os.makedirs(folder, exist_ok=True)

#     img_name = f"{user_email}.png"
#     img_path = os.path.join(folder, img_name)

#     # If settings changed and old QR exists and path differs → delete old
#     if old_qr_path and (old_qr_path != img_path) and old_settings and (old_settings != settings_string):
#         try:
#             if os.path.exists(old_qr_path):
#                 os.remove(old_qr_path)
#         except Exception:
#             logger.exception("Failed to delete old QR %s", old_qr_path)

#     # If file already exists and settings are same → reuse
#     if os.path.exists(img_path) and old_settings == settings_string:
#         return img_path

#     # Generate new QR
#     img = qrcode.make(settings_string)
#     img.save(img_path)

#     return img_path


# async def _get_or_create_subscription(
#     session,
#     user_id: int,
#     slot_number: int,
# ) -> UserSubscription:
#     r_sub = await session.execute(
#         select(UserSubscription).where(
#             UserSubscription.user_id == user_id,
#             UserSubscription.slot_number == slot_number,
#         )
#     )
#     sub = r_sub.scalar_one_or_none()
#     if sub:
#         return sub

#     sub = UserSubscription(
#         user_id=user_id,
#         slot_number=slot_number,
#         server_country_id=None,
#         server_id=None,
#         autopay_id=0,
#         stop_time=None,
#         next_server_id=0,
#         pending=False,
#         settings_string=None,
#         qr_path=None,
#     )
#     session.add(sub)
#     await session.flush()
#     return sub


# async def _choose_server_for_country(
#     session,
#     country_id: int,
# ) -> AllServers:
#     """
#     DB-based, capacity-aware server selection:
#       - all_subscriptions < max_subscriptions
#       - ordered by all_subscriptions ASC
#       - row-level lock with SKIP LOCKED
#     """
#     q = (
#         select(AllServers)
#         .where(
#             and_(
#                 AllServers.country_id == country_id,
#                 AllServers.all_subscriptions < AllServers.max_subscriptions,
#             )
#         )
#         .order_by(AllServers.all_subscriptions.asc())
#         .with_for_update(skip_locked=True)
#     )
#     r = await session.execute(q)
#     server = r.scalars().first()
#     if not server:
#         raise NoServerAvailableError(
#             f"No server available for country_id={country_id}",
#             server_country=country_id,
#         )
#     return server


# async def provision_subscription_for_user(tx_id: int) -> dict:
#     """
#     v15:
#     - Uses InvoiceItems.server_country_id to choose concrete server_id via AllServers
#     - Increments AllServers.all_subscriptions under row lock
#     - Uses UserSubscription rows instead of per-user columns
#     - Generates QR in qrs/subs_qrs/{country_id}/{server_id}/{user_email}.png
#     - Deletes old QR if settings changed
#     - No money logic here
#     """
#     logger.info("provision_subscription_for_user start tx=%s", tx_id)

#     async with SessionLocal() as session:
#         async with session.begin():
#             r_tx = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx = r_tx.scalar_one_or_none()
#             if not tx:
#                 raise ProvisioningError("tx not found")

#             if not tx.provider_invoice_id:
#                 raise ProvisioningError("tx has no provider_invoice_id")

#             r_inv = await session.execute(
#                 select(AllInvoices).where(AllInvoices.invoice_id == tx.provider_invoice_id)
#             )
#             invoice = r_inv.scalar_one_or_none()
#             if not invoice:
#                 raise ProvisioningError("invoice not found for tx")

#             r_items = await session.execute(
#                 select(InvoiceItems).where(InvoiceItems.invoice_id == tx.provider_invoice_id)
#             )
#             items = r_items.scalars().all()
#             if not items:
#                 raise ProvisioningError("no invoice_items for subscription invoice")

#             r_user = await session.execute(
#                 select(AllUsers)
#                 .where(AllUsers.user_id == invoice.user_id)
#                 .with_for_update()
#             )
#             user = r_user.scalar_one_or_none()
#             if not user:
#                 raise ProvisioningError("user not found for invoice")

#             user_id = user.user_id

#             # secrets/config per server_id
#             servers_cfg = get_servers_list()  # {server_id: {...}}
#             api_cache: dict[int, AsyncApi] = {}

#             now = _now_dt()
#             now_ms = int(now.timestamp() * 1000)

#             slots_result: dict[str, dict] = {}

#             for it in items:
#                 slot = it.acc_number
#                 server_country_id = getattr(it, "server_country_id", None)

#                 if slot < 1 or slot > 5:
#                     raise ProvisioningError(f"invalid acc_number in invoice_items: {slot}")

#                 if not server_country_id:
#                     raise ProvisioningError(f"no server_country_id for acc_number={slot}")

#                 # 1. Choose server in DB with row lock
#                 server_row = await _choose_server_for_country(session, server_country_id)
#                 server_id = server_row.server_id

#                 if server_id not in servers_cfg:
#                     raise ProvisioningError(f"server_id {server_id} not in config")

#                 # 2. Persist chosen server_id into invoice item
#                 it.server_id = server_id
#                 session.add(it)

#                 # 3. Load or create subscription row
#                 sub = await _get_or_create_subscription(session, user_id, slot)

#                 # 4. Compute new stop_time
#                 current_stop = sub.stop_time
#                 if current_stop and current_stop > now_ms:
#                     base_start_ms = current_stop
#                 else:
#                     base_start_ms = now_ms

#                 new_end_ms = _compute_new_end_ms(base_start_ms)

#                 # 5. Update subscription row (server + pending switch)
#                 if current_stop and current_stop > now_ms:
#                     if sub.server_id != server_id:
#                         sub.next_server_id = server_id
#                         sub.pending = True
#                 else:
#                     sub.server_id = server_id
#                     sub.next_server_id = 0
#                     sub.pending = False

#                 sub.server_country_id = server_country_id
#                 sub.stop_time = new_end_ms

#                 # 6. Prepare API client
#                 if server_id not in api_cache:
#                     cfg = servers_cfg[server_id]
#                     api = AsyncApi(
#                         host=cfg["http"],
#                         username=cfg["username"],
#                         password=cfg["pass"],
#                         token=cfg.get("token"),
#                         use_tls_verify=True,
#                         custom_certificate_path=cfg.get("sert"),
#                     )
#                     await api.login()
#                     api_cache[server_id] = api
#                 else:
#                     api = api_cache[server_id]

#                 client_email = f"{user_id}-slot{slot}"

#                 external_id, server_end_ts = await _find_client_on_server(api, client_email)
#                 inbounds = await api.inbound.get_list()
#                 vpn_ip = servers_cfg[server_id].get("ip")

#                 # 7. Extend or create client
#                 if external_id and server_end_ts and server_end_ts >= new_end_ms:
#                     # client already has enough time, just build settings string
#                     settings_string = _build_settings_string(inbounds, client_email, vpn_ip)
#                     final_end_ts = server_end_ts
#                 else:
#                     if external_id:
#                         now_ms_local = int(_now_dt().timestamp() * 1000)
#                         ms_diff = max(new_end_ms - now_ms_local, 0)
#                         days_to_extend = max(ms_diff // (24 * 60 * 60 * 1000), 1)
#                         await update_existing_3xui_client(api, inbounds, client_email, days_to_extend)
#                     else:
#                         await add_client_to_3xui_server(api, client_email, new_end_ms, user_id)

#                     inbounds_after = await api.inbound.get_list()
#                     settings_string = _build_settings_string(inbounds_after, client_email, vpn_ip)

#                     external_id_after, server_end_after = await _find_client_on_server(api, client_email)
#                     final_end_ts = int(server_end_after) if server_end_after else new_end_ms

#                 # 8. QR handling: delete old if settings changed, save new
#                 old_settings = sub.settings_string
#                 old_qr = sub.qr_path

#                 img_path = _get_or_create_settings_qr(
#                     settings_string=settings_string,
#                     country_id=server_country_id,
#                     server_id=server_id,
#                     user_email=client_email,
#                     old_settings=old_settings,
#                     old_qr_path=old_qr,
#                 )

#                 sub.settings_string = settings_string
#                 sub.qr_path = img_path
#                 session.add(sub)

#                 # 9. Increment server load under lock
#                 server_row.all_subscriptions = (server_row.all_subscriptions or 0) + 1
#                 session.add(server_row)

#                 slots_result[str(slot)] = {
#                     "server_id": server_id,
#                     "end_ts": final_end_ts,
#                     "settings_string": settings_string,
#                     "img_path": img_path,
#                 }

#             # Attach slots to tx payload_meta
#             r_tx2 = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx2 = r_tx2.scalar_one_or_none()
#             if not tx2:
#                 raise ProvisioningError("tx disappeared during provision")

#             meta = tx2.payload_meta or {}
#             meta["slots"] = slots_result
#             tx2.payload_meta = meta

#             await session.flush()

#     if not slots_result:
#         raise ProvisioningError("no slots processed in provision")

#     logger.info(
#         "provision_subscription_for_user completed tx=%s slots=%s",
#         tx_id,
#         list(slots_result.keys()),
#     )
#     return {"slots": slots_result}


# # services/provision.py v13 (UserSubscription + server_country_id → server_id)

# import logging
# from datetime import datetime, timezone

# from sqlalchemy import select

# from db.async_db import SessionLocal
# from db.models import (
#     SubscriptionTransaction,
#     AllInvoices,
#     InvoiceItems,
#     AllUsers,
#     UserSubscription,
# )
# from services.server_api import (
#     AsyncApi,
#     add_client_to_3xui_server,
#     update_existing_3xui_client,
#     get_client_settings_string_and_qr,
# )
# from services.helpers import get_servers_list
# from services.exceptions import ProvisioningError, NoServerAvailableError
# from config import SUBS_PERIOD_DAYS  # can be None or int

# logger = logging.getLogger(__name__)


# def _now_dt() -> datetime:
#     return datetime.now(timezone.utc)


# def _add_one_month(dt: datetime) -> datetime:
#     year = dt.year
#     month = dt.month + 1
#     if month > 12:
#         month = 1
#         year += 1
#     day = dt.day
#     while True:
#         try:
#             return dt.replace(year=year, month=month, day=day)
#         except ValueError:
#             day -= 1
#             if day < 1:
#                 return dt.replace(year=year, month=month, day=1)


# def _compute_new_end_ms(base_start_ms: int) -> int:
#     if SUBS_PERIOD_DAYS and SUBS_PERIOD_DAYS > 0:
#         period_ms = SUBS_PERIOD_DAYS * 24 * 60 * 60 * 1000
#         return base_start_ms + period_ms

#     base_dt = datetime.fromtimestamp(base_start_ms / 1000, tz=timezone.utc)
#     new_dt = _add_one_month(base_dt)
#     return int(new_dt.timestamp() * 1000)


# async def _find_client_on_server(async_api: AsyncApi, new_client_email: str):
#     inbounds = await async_api.inbound.get_list()
#     for inbound in inbounds:
#         clients = getattr(inbound.settings, "clients", []) if hasattr(inbound, "settings") else []
#         for client in clients:
#             if getattr(client, "email", None) == new_client_email:
#                 server_end = (
#                     getattr(client, "expiry", None)
#                     or getattr(client, "stop", None)
#                     or getattr(client, "expire_at", None)
#                 )
#                 try:
#                     server_end_ms = int(server_end) if server_end is not None else None
#                 except Exception:
#                     server_end_ms = None
#                 return getattr(client, "id", None), server_end_ms
#     return None, None


# def _choose_server_for_country(servers_cfg: dict[int, dict], country_id: int) -> int:
#     """
#     Pick a concrete server_id for given server_country_id.
#     Assumes each cfg has cfg["country_id"] == country_id for matching servers.
#     Strategy: first matching server.
#     """
#     for sid, cfg in servers_cfg.items():
#         if cfg.get("country_id") == country_id:
#             return sid
#     raise NoServerAvailableError(f"No server for country_id={country_id}", server_country=country_id)


# async def _get_or_create_subscription(
#     session,
#     user_id: int,
#     slot_number: int,
# ) -> UserSubscription:
#     r_sub = await session.execute(
#         select(UserSubscription).where(
#             UserSubscription.user_id == user_id,
#             UserSubscription.slot_number == slot_number,
#         )
#     )
#     sub = r_sub.scalar_one_or_none()
#     if sub:
#         return sub

#     sub = UserSubscription(
#         user_id=user_id,
#         slot_number=slot_number,
#         server_country_id=None,
#         server_id=None,
#         autopay_id=0,
#         stop_time=None,
#         next_server_id=0,
#         pending=False,
#         settings_string=None,
#         qr_path=None,
#     )
#     session.add(sub)
#     await session.flush()
#     return sub


# async def provision_subscription_for_user(tx_id: int) -> dict:
#     """
#     v13:
#     - Uses InvoiceItems.server_country_id to choose concrete server_id
#     - Writes chosen server_id back into InvoiceItems.server_id
#     - Uses UserSubscription rows instead of per-user columns
#     - No money logic here
#     """
#     logger.info("provision_subscription_for_user start tx=%s", tx_id)

#     async with SessionLocal() as session:
#         async with session.begin():
#             r_tx = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx = r_tx.scalar_one_or_none()
#             if not tx:
#                 raise ProvisioningError("tx not found")

#             if not tx.provider_invoice_id:
#                 raise ProvisioningError("tx has no provider_invoice_id")

#             r_inv = await session.execute(
#                 select(AllInvoices).where(AllInvoices.invoice_id == tx.provider_invoice_id)
#             )
#             invoice = r_inv.scalar_one_or_none()
#             if not invoice:
#                 raise ProvisioningError("invoice not found for tx")

#             r_items = await session.execute(
#                 select(InvoiceItems).where(InvoiceItems.invoice_id == tx.provider_invoice_id)
#             )
#             items = r_items.scalars().all()
#             if not items:
#                 raise ProvisioningError("no invoice_items for subscription invoice")

#             r_user = await session.execute(
#                 select(AllUsers)
#                 .where(AllUsers.user_id == invoice.user_id)
#                 .with_for_update()
#             )
#             user = r_user.scalar_one_or_none()
#             if not user:
#                 raise ProvisioningError("user not found for invoice")

#             user_id = user.user_id

#             servers_cfg = get_servers_list()
#             api_cache: dict[int, AsyncApi] = {}

#             now = _now_dt()
#             now_ms = int(now.timestamp() * 1000)

#             slots_result: dict[str, dict] = {}

#             for it in items:
#                 slot = it.acc_number
#                 server_country_id = getattr(it, "server_country_id", None)

#                 if slot < 1 or slot > 5:
#                     raise ProvisioningError(f"invalid acc_number in invoice_items: {slot}")

#                 if not server_country_id:
#                     raise ProvisioningError(f"no server_country_id for acc_number={slot}")

#                 # choose concrete server_id by country
#                 server_id = _choose_server_for_country(servers_cfg, server_country_id)

#                 # persist chosen server_id into invoice item
#                 it.server_id = server_id
#                 session.add(it)

#                 if server_id not in servers_cfg:
#                     raise ProvisioningError(f"server_id {server_id} not in config")

#                 # load or create subscription row for this slot
#                 sub = await _get_or_create_subscription(session, user_id, slot)

#                 # update subscription country/server
#                 sub.server_country_id = server_country_id
#                 # current active stop_time
#                 current_stop = sub.stop_time

#                 if current_stop and current_stop > now_ms:
#                     base_start_ms = current_stop
#                 else:
#                     base_start_ms = now_ms

#                 new_end_ms = _compute_new_end_ms(base_start_ms)

#                 if current_stop and current_stop > now_ms:
#                     # active subscription, schedule server switch if needed
#                     if sub.server_id != server_id:
#                         sub.next_server_id = server_id
#                         sub.pending = True
#                 else:
#                     # no active subscription, switch immediately
#                     sub.server_id = server_id
#                     sub.next_server_id = 0
#                     sub.pending = False

#                 sub.stop_time = new_end_ms

#                 if server_id not in api_cache:
#                     cfg = servers_cfg[server_id]
#                     api = AsyncApi(
#                         host=cfg["http"],
#                         username=cfg["username"],
#                         password=cfg["pass"],
#                         token=cfg.get("token"),
#                         use_tls_verify=True,
#                         custom_certificate_path=cfg.get("sert"),
#                     )
#                     await api.login()
#                     api_cache[server_id] = api
#                 else:
#                     api = api_cache[server_id]

#                 client_email = f"{user_id}-slot{slot}"

#                 external_id, server_end_ts = await _find_client_on_server(api, client_email)
#                 inbounds = await api.inbound.get_list()
#                 vpn_ip = servers_cfg[server_id].get("ip")

#                 if external_id and server_end_ts and server_end_ts >= new_end_ms:
#                     settings_string, img_path = get_client_settings_string_and_qr(
#                         inbounds, client_email, vpn_ip
#                     )
#                     slots_result[str(slot)] = {
#                         "server_id": server_id,
#                         "end_ts": server_end_ts,
#                         "settings_string": settings_string,
#                         "img_path": img_path,
#                     }
#                     sub.settings_string = settings_string
#                     sub.qr_path = img_path
#                     session.add(sub)
#                     continue

#                 if external_id:
#                     now_ms_local = int(_now_dt().timestamp() * 1000)
#                     ms_diff = max(new_end_ms - now_ms_local, 0)
#                     days_to_extend = max(ms_diff // (24 * 60 * 60 * 1000), 1)
#                     await update_existing_3xui_client(api, inbounds, client_email, days_to_extend)
#                 else:
#                     await add_client_to_3xui_server(api, client_email, new_end_ms, user_id)

#                 inbounds_after = await api.inbound.get_list()
#                 settings_string, img_path = get_client_settings_string_and_qr(
#                     inbounds_after, client_email, vpn_ip
#                 )

#                 external_id_after, server_end_after = await _find_client_on_server(api, client_email)
#                 final_end_ts = int(server_end_after) if server_end_after else new_end_ms

#                 slots_result[str(slot)] = {
#                     "server_id": server_id,
#                     "end_ts": final_end_ts,
#                     "settings_string": settings_string,
#                     "img_path": img_path,
#                 }
#                 sub.settings_string = settings_string
#                 sub.qr_path = img_path
#                 session.add(sub)

#             r_tx2 = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx2 = r_tx2.scalar_one_or_none()
#             if not tx2:
#                 raise ProvisioningError("tx disappeared during provision")

#             meta = tx2.payload_meta or {}
#             meta["slots"] = slots_result
#             tx2.payload_meta = meta

#             await session.flush()

#     if not slots_result:
#         raise ProvisioningError("no slots processed in provision")

#     logger.info(
#         "provision_subscription_for_user completed tx=%s slots=%s",
#         tx_id,
#         list(slots_result.keys()),
#     )
#     return {"slots": slots_result}


# # services/provision.py v12

# import logging
# from datetime import datetime, timezone

# from sqlalchemy import select
# from sqlalchemy.exc import SQLAlchemyError

# from db.async_db import SessionLocal
# from db.models import (
#     SubscriptionTransaction,
#     AllInvoices,
#     InvoiceItems,
#     AllUsers,
# )
# from services.server_api import (
#     AsyncApi,
#     add_client_to_3xui_server,
#     update_existing_3xui_client,
#     get_client_settings_string_and_qr,
# )
# from services.helpers import get_servers_list
# from services.exceptions import ProvisioningError, NoServerAvailableError
# from config import SUBS_PERIOD_DAYS  # can be None or int

# logger = logging.getLogger(__name__)


# def _now_dt() -> datetime:
#     return datetime.now(timezone.utc)


# def _add_one_month(dt: datetime) -> datetime:
#     year = dt.year
#     month = dt.month + 1
#     if month > 12:
#         month = 1
#         year += 1
#     day = dt.day
#     while True:
#         try:
#             return dt.replace(year=year, month=month, day=day)
#         except ValueError:
#             day -= 1
#             if day < 1:
#                 return dt.replace(year=year, month=month, day=1)


# def _compute_new_end_ms(base_start_ms: int) -> int:
#     if SUBS_PERIOD_DAYS and SUBS_PERIOD_DAYS > 0:
#         period_ms = SUBS_PERIOD_DAYS * 24 * 60 * 60 * 1000
#         return base_start_ms + period_ms

#     base_dt = datetime.fromtimestamp(base_start_ms / 1000, tz=timezone.utc)
#     new_dt = _add_one_month(base_dt)
#     return int(new_dt.timestamp() * 1000)


# async def _find_client_on_server(async_api: AsyncApi, new_client_email: str):
#     inbounds = await async_api.inbound.get_list()
#     for inbound in inbounds:
#         clients = getattr(inbound.settings, "clients", []) if hasattr(inbound, "settings") else []
#         for client in clients:
#             if getattr(client, "email", None) == new_client_email:
#                 server_end = (
#                     getattr(client, "expiry", None)
#                     or getattr(client, "stop", None)
#                     or getattr(client, "expire_at", None)
#                 )
#                 try:
#                     server_end_ms = int(server_end) if server_end is not None else None
#                 except Exception:
#                     server_end_ms = None
#                 return getattr(client, "id", None), server_end_ms
#     return None, None


# async def provision_subscription_for_user(tx_id: int) -> dict:
#     """
#     v12:
#     - same as v10, but tolerant to different tx.payload_meta["source"] (manual/autorenew/etc.)
#     - no money logic here
#     """
#     logger.info("provision_subscription_for_user start tx=%s", tx_id)

#     async with SessionLocal() as session:
#         async with session.begin():
#             r_tx = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx = r_tx.scalar_one_or_none()
#             if not tx:
#                 raise ProvisioningError("tx not found")

#             if not tx.provider_invoice_id:
#                 raise ProvisioningError("tx has no provider_invoice_id")

#             r_inv = await session.execute(
#                 select(AllInvoices).where(AllInvoices.invoice_id == tx.provider_invoice_id)
#             )
#             invoice = r_inv.scalar_one_or_none()
#             if not invoice:
#                 raise ProvisioningError("invoice not found for tx")

#             r_items = await session.execute(
#                 select(InvoiceItems).where(InvoiceItems.invoice_id == tx.provider_invoice_id)
#             )
#             items = r_items.scalars().all()
#             if not items:
#                 raise ProvisioningError("no invoice_items for subscription invoice")

#             r_user = await session.execute(
#                 select(AllUsers)
#                 .where(AllUsers.user_id == invoice.user_id)
#                 .with_for_update()
#             )
#             user = r_user.scalar_one_or_none()
#             if not user:
#                 raise ProvisioningError("user not found for invoice")

#             user_id = user.user_id

#             servers_cfg = get_servers_list()
#             api_cache: dict[int, AsyncApi] = {}

#             now = _now_dt()
#             now_ms = int(now.timestamp() * 1000)

#             slots_result: dict[str, dict] = {}

#             for it in items:
#                 slot = it.acc_number
#                 server_id = it.server_id

#                 if slot < 1 or slot > 5:
#                     raise ProvisioningError(f"invalid acc_number in invoice_items: {slot}")

#                 if server_id not in servers_cfg:
#                     raise ProvisioningError(f"server_id {server_id} not in config")

#                 stop_attr = f"subscription_stop_id_{slot}"
#                 cur_server_attr = f"subscription_server_id_{slot}"
#                 next_server_attr = f"subscription_server_next_id_{slot}"
#                 pending_attr = f"subscription_server_pending_{slot}"

#                 current_stop = getattr(user, stop_attr)
#                 current_server = getattr(user, cur_server_attr)
#                 next_server = getattr(user, next_server_attr)
#                 pending = getattr(user, pending_attr)

#                 if current_stop and current_stop > now_ms:
#                     base_start_ms = current_stop
#                 else:
#                     base_start_ms = now_ms

#                 new_end_ms = _compute_new_end_ms(base_start_ms)

#                 if current_stop and current_stop > now_ms:
#                     if current_server != server_id:
#                         setattr(user, next_server_attr, server_id)
#                         setattr(user, pending_attr, True)
#                 else:
#                     setattr(user, cur_server_attr, server_id)
#                     setattr(user, next_server_attr, 0)
#                     setattr(user, pending_attr, False)

#                 setattr(user, stop_attr, new_end_ms)

#                 if server_id not in api_cache:
#                     cfg = servers_cfg[server_id]
#                     api = AsyncApi(
#                         host=cfg["http"],
#                         username=cfg["username"],
#                         password=cfg["pass"],
#                         token=cfg.get("token"),
#                         use_tls_verify=True,
#                         custom_certificate_path=cfg.get("sert"),
#                     )
#                     await api.login()
#                     api_cache[server_id] = api
#                 else:
#                     api = api_cache[server_id]

#                 client_email = f"{user_id}-slot{slot}"

#                 external_id, server_end_ts = await _find_client_on_server(api, client_email)
#                 inbounds = await api.inbound.get_list()
#                 vpn_ip = servers_cfg[server_id].get("ip")

#                 if external_id and server_end_ts and server_end_ts >= new_end_ms:
#                     settings_string, img_path = get_client_settings_string_and_qr(
#                         inbounds, client_email, vpn_ip
#                     )
#                     slots_result[str(slot)] = {
#                         "server_id": server_id,
#                         "end_ts": server_end_ts,
#                         "settings_string": settings_string,
#                         "img_path": img_path,
#                     }
#                     setattr(user, f"subscription_settings_string_{slot}", settings_string)
#                     setattr(user, f"subscription_qr_path_{slot}", img_path)
#                     continue

#                 if external_id:
#                     now_ms_local = int(_now_dt().timestamp() * 1000)
#                     ms_diff = max(new_end_ms - now_ms_local, 0)
#                     days_to_extend = max(ms_diff // (24 * 60 * 60 * 1000), 1)
#                     await update_existing_3xui_client(api, inbounds, client_email, days_to_extend)
#                 else:
#                     await add_client_to_3xui_server(api, client_email, new_end_ms, user_id)

#                 inbounds_after = await api.inbound.get_list()
#                 settings_string, img_path = get_client_settings_string_and_qr(
#                     inbounds_after, client_email, vpn_ip
#                 )

#                 external_id_after, server_end_after = await _find_client_on_server(api, client_email)
#                 final_end_ts = int(server_end_after) if server_end_after else new_end_ms

#                 slots_result[str(slot)] = {
#                     "server_id": server_id,
#                     "end_ts": final_end_ts,
#                     "settings_string": settings_string,
#                     "img_path": img_path,
#                 }
#                 setattr(user, f"subscription_settings_string_{slot}", settings_string)
#                 setattr(user, f"subscription_qr_path_{slot}", img_path)

#             r_tx2 = await session.execute(
#                 select(SubscriptionTransaction).where(SubscriptionTransaction.id == tx_id)
#             )
#             tx2 = r_tx2.scalar_one_or_none()
#             if not tx2:
#                 raise ProvisioningError("tx disappeared during provision")

#             meta = tx2.payload_meta or {}
#             meta["slots"] = slots_result
#             tx2.payload_meta = meta

#             await session.flush()

#     if not slots_result:
#         raise ProvisioningError("no slots processed in provision")

#     logger.info("provision_subscription_for_user completed tx=%s slots=%s", tx_id, list(slots_result.keys()))
#     return {"slots": slots_result}
