# services/bitpapa.py
import asyncio
from typing import Optional, Callable, TypeVar, Awaitable

from bitpapa_pay import BitpapaPay

T = TypeVar("T")


class BitpapaService:
    def __init__(
        self,
        api_token: str,
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        # НЕ создаём сетевые ресурсы здесь
        self.api_token = api_token
        self._client: Optional[BitpapaPay] = None
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def init(self) -> None:
        # Создаём BitpapaPay в контексте уже запущенного event loop
        if self._client is None:
            self._client = BitpapaPay(api_token=self.api_token)

    async def _with_retry(
        self,
        func: Callable[[], Awaitable[T]],
        *,
        operation_name: str = "bitpapa_call",
    ) -> T:
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                return await func()
            except Exception as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    raise
                delay = self._base_delay * attempt
                await asyncio.sleep(delay)

        assert last_exc is not None
        raise last_exc

    async def create_invoice(
        self,
        currency_code: str,
        amount: float,
    ):
        if self._client is None:
            # защитный вариант: инициализируем на лету, если забыли вызвать init
            await self.init()

        async def _call():
            return await self._client.create_invoice(currency_code, amount)

        return await self._with_retry(_call, operation_name="create_invoice")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
