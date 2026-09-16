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


async def _delete_client_on_server(server_id: int, client_email: str):
    servers_cfg = get_servers_list()
    if server_id not in servers_cfg:
        logger.warning("Server %s not in config, skipping deletion for %s", server_id, client_email)
        return

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

    inbounds = await api.inbound.get_list()
    # naive search by email
    for inbound in inbounds:
        clients = getattr(inbound.settings, "clients", []) if hasattr(inbound, "settings") else []
        for client in clients:
            if getattr(client, "email", None) == client_email:
                await api.client.remove(inbound.id, client.id)
                logger.info("Deleted client %s from server %s", client_email, server_id)
                return

    logger.info("Client %s not found on server %s (already deleted?)", client_email, server_id)


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
