# systemd watchdog
# Create /etc/systemd/system/vpn-backend.service:
# [Unit]
# Description=VPN Backend Supervisor
# After=network.target

# [Service]
# ExecStart=/usr/bin/python3 /opt/app/supervisor.py
# Restart=always
# RestartSec=5
# WatchdogSec=30
# Type=simple

# [Install]
# WantedBy=multi-user.target


# Enable:
# systemctl enable vpn-backend
# systemctl start vpn-backend



# supervisor.py — final version

import asyncio
import logging

from services.listener import PgListener
from services.events import on_event

from workers.reconciler import reconciliation_loop
from workers.bitpappa_invoice_reconciller import bitpappa_invoice_reconciller
from workers.invoice_processor import invoice_processor
from workers.autorenew_worker import autorenew_loop
from workers.server_cleanup_worker import server_cleanup_loop
from workers.server_health_worker import server_health_worker_loop

from services.bitpapa import BitpapaService
from config import DATABASE_URL_PG_PG, PAYMENT_PROVIDER_TOKEN

logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {"worker": "supervisor"})

from services.logging_format import WorkerFormatter

handler = logging.StreamHandler()
handler.setFormatter(WorkerFormatter("%(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])



# Helper to run a worker forever, restarting on crash
from aiohttp import web
from services.heartbeat import get_heartbeats, supervisor_check, heartbeat

async def health_handler(request):
    workers = await get_heartbeats()

    return web.json_response({
        "status": "ok",
        "workers": workers,
    })


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()

async def supervisor_check_loop():
    while True:
        await supervisor_check()  # checks DB heartbeats
        await asyncio.sleep(10)




async def run_worker(name: str, coro_factory):
    """Run a worker forever, restarting on crash."""
    while True:
        heartbeat("run_worker")
        try:
            logger.info("Starting worker: %s", name)
            await coro_factory()
        except asyncio.CancelledError:
            logger.info("Worker %s cancelled", name)
            return
        except Exception:
            logger.exception("Worker %s crashed, restarting in 5s", name)
            await asyncio.sleep(5)


async def supervisor():
    stop_event = asyncio.Event()

    # Bitpapa service for this process
    bitpapa_service = BitpapaService(
        api_token=PAYMENT_PROVIDER_TOKEN,
        max_retries=3,
        base_delay=1.0,
    )

    # Postgres listener
    listener = PgListener(
        dsn=DATABASE_URL_PG_PG,
        channel="events",
        callback=on_event,
    )
    await listener.start()

    # Start health server for supervisor and workers
    asyncio.create_task(start_health_server())
    logger.info("Health server started on :8081")

    # Start supervisor health checker
    asyncio.create_task(supervisor_check_loop())
    logger.info("Supervisor health checker started")



    # All workers
    workers = [
        run_worker("reconciler", lambda: reconciliation_loop(stop_event)),
        run_worker("bitpappa_invoice_reconciller", lambda: bitpappa_invoice_reconciller(bitpapa_service)),
        run_worker("invoice_processor", invoice_processor),
        run_worker("autorenew_worker", lambda: autorenew_loop(stop_event)),
        run_worker("server_cleanup_worker", lambda: server_cleanup_loop(stop_event)),
        run_worker("server_health_worker", server_health_worker_loop),
    ]

    tasks = [asyncio.create_task(w) for w in workers]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        stop_event.set()
        await listener.stop()
        await bitpapa_service.close()
        logger.info("Supervisor stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(supervisor())


# # supervisor.py

# import asyncio
# import logging

# from services.listener import PgListener
# from services.events import on_event
# from workers.reconciler import reconciliation_loop
# from workers.bitpappa_invoice_reconciller import bitpappa_invoice_reconciller
# from workers.invoice_processor import invoice_processor
# from services.bitpapa import BitpapaService
# from config import DATABASE_URL_PG_PG, PAYMENT_PROVIDER_TOKEN

# logger = logging.getLogger(__name__)

# async def run_worker(name: str, coro_factory):
#     """Run a worker forever, restarting on crash."""
#     while True:
#         try:
#             logger.info("Starting worker: %s", name)
#             await coro_factory()
#         except asyncio.CancelledError:
#             logger.info("Worker %s cancelled", name)
#             return
#         except Exception:
#             logger.exception("Worker %s crashed, restarting in 5s", name)
#             await asyncio.sleep(5)


# async def supervisor():
#     stop_event = asyncio.Event()

#     # Create BitpapaService for THIS process
#     bitpapa_service = BitpapaService(
#         api_token=PAYMENT_PROVIDER_TOKEN,
#         max_retries=3,
#         base_delay=1.0,
#     )

#     # Listener for this process
#     listener = PgListener(
#         dsn=DATABASE_URL_PG_PG,
#         channel="events",
#         callback=on_event,
#     )
#     await listener.start()

#     # Define workers
#     workers = [
#         run_worker("reconciler", lambda: reconciliation_loop(stop_event)),
#         run_worker("bitpappa_invoice_reconciller", lambda: bitpappa_invoice_reconciller(bitpapa_service)),
#         run_worker("invoice_processor", invoice_processor),
#     ]

#     tasks = [asyncio.create_task(w) for w in workers]

#     try:
#         await asyncio.gather(*tasks)
#     except asyncio.CancelledError:
#         pass
#     finally:
#         stop_event.set()
#         await listener.stop()
#         await bitpapa_service.close()
#         logger.info("Supervisor stopped")


# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(supervisor())
