import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db.async_db import SessionLocal
from db.models import ServerClientDeletion
from services.heartbeat import heartbeat
from services.helpers import get_servers_list
from services.server_api import AsyncApi

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "server_cleanup_worker"})

CLEANUP_INTERVAL_SECONDS = 300
MAX_ATTEMPTS = 10
BATCH_SIZE = 50


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


async def _delete_client_on_server(server_id: int, client_email: str) -> bool:
    servers_cfg = get_servers_list()
    cfg = servers_cfg.get(server_id)
    if not cfg:
        raise LookupError(f"Server {server_id} is not configured")

    api = AsyncApi(
        host=cfg["http"],
        username=cfg["username"],
        password=cfg.get("password", cfg.get("pass")),
        token=cfg.get("token"),
        use_tls_verify=cfg.get("use_tls_verify", True),
        custom_certificate_path=cfg.get("sert"),
    )
    try:
        await api.login()
        # for inbound in await api.inbound.get_list():
        #     settings = getattr(inbound, "settings", None)
        #     for client in list(getattr(settings, "clients", None) or []):
        #         if getattr(client, "email", None) == client_email:
        #             await api.client.delete(inbound.id, client.id)
        #             logger.info("Deleted client %s from server %s", client_email, server_id)
        #             return True
        # logger.info("Client %s is already absent from server %s", client_email, server_id)
        # return True

        target_inbound_id = None
        target_client_id = None

        # Шаг 1: Только ищем координаты клиента, ничего не удаляя внутри итерации
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

    finally:
        close = getattr(api, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result


async def _cleanup_batch() -> None:
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(ServerClientDeletion)
                .where(
                    ServerClientDeletion.delete_not_before_ts <= _now_ms(),
                    ServerClientDeletion.attempts < MAX_ATTEMPTS,
                )
                .order_by(ServerClientDeletion.id)
                .limit(BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            deletions = result.scalars().all()
            for deletion in deletions:
                try:
                    await _delete_client_on_server(deletion.server_id, deletion.client_email)
                except Exception as exc:
                    deletion.attempts = (deletion.attempts or 0) + 1
                    deletion.last_error = str(exc)[:1000]
                    logger.exception("Failed cleanup for %s", deletion.client_email)
                else:
                    await session.delete(deletion)


async def server_cleanup_loop(stop_event: asyncio.Event):
    logger.info("Server cleanup loop started")
    try:
        while not stop_event.is_set():
            await heartbeat("server_cleanup_worker")
            try:
                await _cleanup_batch()
            except SQLAlchemyError:
                logger.exception("DB error during server cleanup")
            except Exception:
                logger.exception("Unexpected server cleanup error")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=CLEANUP_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
    except asyncio.CancelledError:
        logger.info("Server cleanup loop cancelled")
    finally:
        logger.info("Server cleanup loop stopped")
