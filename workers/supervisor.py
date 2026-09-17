# workers/supervisor.py
import asyncio
import logging
from aiohttp import web

from config import DATABASE_URL_PG_PG, PAYMENT_PROVIDER_TOKEN
from services.bitpapa import BitpapaService
from services.events import on_event
from services.heartbeat import get_heartbeats, heartbeat, supervisor_check
from services.listener import PgListener
from workers.autorenew_worker import autorenew_loop
from workers.bitpappa_invoice_reconciller import bitpappa_invoice_reconciller
from workers.invoice_processor import invoice_processor
from workers.reconciler import reconciliation_loop
from workers.server_cleanup_worker import server_cleanup_loop
from workers.server_health_worker import server_health_worker_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def health_handler(request):
    return web.json_response({"status": "ok", "workers": await get_heartbeats()})


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8081).start()
    return runner


async def supervisor_check_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        await supervisor_check()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass


async def run_worker(name: str, coro_factory):
    while True:
        heartbeat(name)
        try:
            logger.info("Starting worker: %s", name)
            await coro_factory()
        except asyncio.CancelledError:
            logger.info("Worker %s cancelled", name)
            raise
        except Exception:
            logger.exception("Worker %s crashed; restarting in 5s", name)
            await asyncio.sleep(5)


async def supervisor():
    stop_event = asyncio.Event()
    bitpapa_service = BitpapaService(
        api_token=PAYMENT_PROVIDER_TOKEN,
        max_retries=3,
        base_delay=1.0,
    )
    listener = PgListener(dsn=DATABASE_URL_PG_PG, channel="events", callback=on_event)
    health_runner = None
    tasks = []
    try:
        await listener.start()
        health_runner = await start_health_server()
        tasks = [
            asyncio.create_task(supervisor_check_loop(stop_event)),
            asyncio.create_task(run_worker("reconciler", lambda: reconciliation_loop(stop_event))),
            asyncio.create_task(run_worker("bitpappa_invoice_reconciller", lambda: bitpappa_invoice_reconciller(bitpapa_service))),
            asyncio.create_task(run_worker("invoice_processor", invoice_processor)),
            asyncio.create_task(run_worker("autorenew_worker", lambda: autorenew_loop(stop_event))),
            asyncio.create_task(run_worker("server_cleanup_worker", lambda: server_cleanup_loop(stop_event))),
            asyncio.create_task(run_worker("server_health_worker", lambda: server_health_worker_loop(stop_event))),
        ]
        await asyncio.gather(*tasks)
    finally:
        stop_event.set()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await listener.stop()
        await bitpapa_service.close()
        if health_runner:
            await health_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(supervisor())
