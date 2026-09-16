import asyncio
from time import time
from sqlalchemy import select
from db import SessionLocal
from db.models import AllServers
from api_client import AsyncApi
from servers_cache import get_servers_meta  # your existing cache

async def check_single_server(cfg: dict):
    api = AsyncApi(
        host=cfg["http"],
        username=cfg["username"],
        password=cfg["password"],
        token=cfg.get("token"),
        use_tls_verify=True,
        custom_certificate_path=cfg.get("sert"),
    )

    try:
        await api.login()

        # Check panel + Xray
        await api.inbound.get_list()

        # Active users
        try:
            clients = await api.client.get_list()
            active_users = len(clients)
        except:
            active_users = 0

        # Load (optional)
        load = 0.0

        return True, active_users, load

    except Exception:
        return False, 0, 0.0


async def server_health_supervisor():
    async with SessionLocal() as session:
        servers = await session.scalars(select(AllServers))
        servers = servers.all()

        meta = get_servers_meta()
        now_ms = int(time() * 1000)

        for server in servers:
            cfg = meta.get(server.id)
            if not cfg:
                server.is_online = False
                server.last_check = now_ms
                continue

            is_online, active_users, load = await check_single_server(cfg)

            server.is_online = is_online
            server.last_check = now_ms
            server.active_users = active_users
            server.load = load

        await session.commit()


async def server_health_worker_loop():
    while True:
        await heartbeat("server_health_worker")
        await server_health_supervisor()
        await asyncio.sleep(30)
