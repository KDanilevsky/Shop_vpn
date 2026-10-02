import asyncio
import logging
from time import time

from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllServers
from services.heartbeat import heartbeat
from services.helpers import get_servers_list
from services.server_api import AsyncApi

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "server_health_worker"})

HEALTH_INTERVAL_SECONDS = 30


async def check_single_server(cfg: dict):
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
        inbounds = await api.inbound.get_list()
        active_users = sum(
            len(getattr(getattr(inbound, "settings", None), "clients", None) or [])
            for inbound in inbounds or []
        )
        return True, active_users, 0.0
    except Exception:
        logger.exception("3x-ui health check failed")
        return False, 0, 0.0
    finally:
        close = getattr(api, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result


# async def server_health_supervisor():
#     configs = get_servers_list()
#     async with SessionLocal() as session:
#         servers = (await session.scalars(select(AllServers))).all()
#         now_ms = int(time() * 1000)
#         for server in servers:
#             cfg = configs.get(server.id)
#             if not cfg:
#                 server.is_online = False
#             else:
#                 online, active_users, load = await check_single_server(cfg)
#                 server.is_online = online
#                 server.active_users = active_users
#                 server.load = load
#             server.last_check = now_ms
#         await session.commit()

async def server_health_supervisor():
    configs = get_servers_list()
    
    # 1. Быстро забираем список серверов из БД и СРАЗУ закрываем сессию
    async with SessionLocal() as session:
        servers_db = (await session.scalars(select(AllServers))).all()
        # Сохраняем ID серверов, чтобы не держать живые объекты SQLAlchemy в памяти во время сетевых запросов
        server_ids = [s.id for s in servers_db]

    now_ms = int(time() * 1000)
    results = {}

    # 2. Сетевые запросы делаются здесь — база данных полностью свободна!
    for s_id in server_ids:
        cfg = configs.get(s_id)
        if not cfg:
            results[s_id] = (False, 0, 0.0)
        else:
            online, active_users, load = await check_single_server(cfg)
            results[s_id] = (online, active_users, load)

    # 3. Открываем короткую сессию только для того, чтобы за долю миллисекунды записать результаты в БД
    async with SessionLocal() as session:
        async with session.begin():
            for s_id, (online, active_users, load) in results.items():
                server = await session.get(AllServers, s_id)
                if server:
                    server.is_online = online
                    server.active_users = active_users
                    server.load = load
                    server.last_check = now_ms


async def server_health_worker_loop(stop_event: asyncio.Event | None = None):
    while stop_event is None or not stop_event.is_set():
        await heartbeat("server_health_worker")
        try:
            await server_health_supervisor()
        except Exception:
            logger.exception("Server health scan failed")
        if stop_event is None:
            await asyncio.sleep(HEALTH_INTERVAL_SECONDS)
        else:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=HEALTH_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
