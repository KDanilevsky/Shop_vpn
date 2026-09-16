# listener.py
import asyncio
import asyncpg
import logging
import signal
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# TxCallback = Callable[[int], Awaitable[None]]

PgCallback = Callable[[str], Awaitable[None]]


class PgListener:
    """
    Persistent LISTEN on a PostgreSQL channel with:
    - auto-reconnect (exponential backoff)
    - graceful shutdown
    - heartbeat logging
    """

    def __init__(
        self,
        dsn: str,
        channel: str,
        callback: PgCallback,
        min_backoff: float = 1.0,
        max_backoff: float = 30.0,
        heartbeat_interval: float = 60.0,
    ) -> None:
        self.dsn = dsn
        self.channel = channel
        self.callback = callback
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.heartbeat_interval = heartbeat_interval

        self._stop_event = asyncio.Event()
        self._conn: Optional[asyncpg.Connection] = None
        self._main_task: Optional[asyncio.Task] = None
        self._hb_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._main_task:
            return
        self._main_task = asyncio.create_task(self._run(), name="pg_listener_main")
        self._hb_task = asyncio.create_task(self._heartbeat(), name="pg_listener_heartbeat")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._main_task:
            await self._main_task

        if self._hb_task:
            self._hb_task.cancel()
            try:
                await self._hb_task
            except asyncio.CancelledError:
                pass

        await self._close_conn()

    async def _run(self) -> None:
        backoff = self.min_backoff

        while not self._stop_event.is_set():
            try:
                logger.info("PG LISTEN: connecting to DB...")
                self._conn = await asyncpg.connect(self.dsn)

                await self._conn.add_listener(
                    self.channel,
                    self._on_notify,
                )

                logger.info("PG LISTEN: listening on channel '%s'", self.channel)
                backoff = self.min_backoff  # reset backoff after success

                while not self._stop_event.is_set():
                    await asyncio.sleep(1)

            except Exception as e:
                logger.exception(
                    "PG LISTEN: connection error, reconnecting in %.1fs: %s",
                    backoff, e
                )
                await self._close_conn()

                if self._stop_event.is_set():
                    break

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff)

        logger.info("PG LISTEN: stopped")

    async def _close_conn(self) -> None:
        if self._conn:
            try:
                await self._conn.close()
            except Exception:
                logger.exception("PG LISTEN: error closing connection")
            finally:
                self._conn = None

    def _on_notify(self, connection, pid, channel, payload: str) -> None:
        # Pass raw payload to callback
        asyncio.create_task(self._safe_callback(payload))

    async def _safe_callback(self, payload: str) -> None:
        try:
            await self.callback(payload)
        except Exception:
            logger.exception("PG LISTEN: callback failed for payload=%s", payload)

    async def _heartbeat(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(self.heartbeat_interval)
            alive = self._conn is not None and not self._conn.is_closed()
            logger.info("PG LISTEN heartbeat: alive=%s channel=%s", alive, self.channel)
