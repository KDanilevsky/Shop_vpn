# workers/server_cleanup_worker.py v1

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db.async_db import SessionLocal
from db.models import ServerClientDeletion, AllServers
from services.server_api import AsyncApi
from services.helpers import get_servers_list

from services.heartbeat import heartbeat

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "server_cleanup_worker"})

CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
MAX_ATTEMPTS = 10


def _now():
    return datetime.now(timezone.utc)


def _now_ms():
    return int(_now().timestamp() * 1000)


async def _delete_client_on_server(server_id: int, client_email: str) -> bool:
    servers_cfg = get_servers_list()
    cfg = servers_cfg.get(server_id)
    if not cfg:
        raise LookupError(f"Server {server_id} is not configured")

    api = AsyncApi(
        host= cfg["http"],
        username= cfg["username"],
        password= cfg.get("password", cfg.get("pass")),
        token= cfg.get("token"),
        use_tls_verify= cfg.get("use_tls_verify", True),
        custom_certificate_path= cfg.get("sert"),
    )

    try:
        await api.login()
        
        target_inbound_id = None
        target_client_id = None

        # Шаг 1: Только ищем нужного клиента, ничего не удаляя внутри цикла
        for inbound in await api.inbound.get_list():
            settings = getattr(inbound, "settings", None)
            for client in (getattr(settings, "clients", None) or []):
                if getattr(client, "email", None) == client_email:
                    target_inbound_id = inbound.id
                    target_client_id = client.id
                    break
            if target_client_id:
                break

        # Шаг 2: Удаляем за пределами циклов итерации
        if target_inbound_id and target_client_id:
            await api.client.delete(target_inbound_id, target_client_id)
            logger.info("Deleted client %s from server %s", client_email, server_id)
            return True

        logger.info("Client %s is already absent from server %s", client_email, server_id)
        return True

    finally:
        close = getattr(api, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result


async def _cleanup_batch():
    now_ms = _now_ms()

    async with SessionLocal() as session:
        async with session.begin():
            r = await session.execute(
                select(ServerClientDeletion)
                .where(
                    ServerClientDeletion.delete_not_before_ts <= now_ms,
                    ServerClientDeletion.attempts < MAX_ATTEMPTS,
                )
                .with_for_update(skip_locked=True)
            )
            deletions = r.scalars().all()

            if not deletions:
                return

            logger.info("Server cleanup: picked %s deletions", len(deletions))

            for d in deletions:
                try:
                    await _delete_client_on_server(d.server_id, d.client_email)
                except Exception as e:
                    d.attempts += 1
                    d.last_error = str(e)
                    logger.exception(
                        "Failed to delete client %s on server %s (attempt %s)",
                        d.client_email,
                        d.server_id,
                        d.attempts,
                    )
                    session.add(d)
                else:
                    await session.delete(d)


async def server_cleanup_loop(stop_event: asyncio.Event):
    logger.info("Server cleanup loop started")

    try:
        while not stop_event.is_set():
            await heartbeat("server_cleanup_worker")
            try:
                await _cleanup_batch()
            except SQLAlchemyError:
                logger.exception("DB error during server cleanup batch")
            except Exception:
                logger.exception("Unexpected error during server cleanup batch")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=CLEANUP_INTERVAL_SECONDS)
                break
            except asyncio.TimeoutError:
                continue

    except asyncio.CancelledError:
        logger.info("Server cleanup loop cancelled")
    finally:
        logger.info("Server cleanup loop stopped")
