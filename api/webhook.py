# api/webhook.py
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, FastAPI, HTTPException, Request, Depends, status
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import AllInvoices
from services.events import create_pg_event
from services.cryptomus import CryptomusService

logger = logging.getLogger(__name__)

app = FastAPI()
router = APIRouter()  # Убираем префикс отсюда, чтобы жестко контролировать пути эндпоинтов

# Переменная окружения для проверки оригинального вебхука Bitpapa / внутренней системы
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

def _verify_secret(provided: str | None) -> bool:
    if not WEBHOOK_SECRET or not provided:
        return False
    return hmac.compare_digest(str(provided), WEBHOOK_SECRET)

# Фабрика для инициализации сервиса Cryptomus
def get_cryptomus_service() -> CryptomusService:
    from config import CRYPTOMUS_MERCHANT_ID, CRYPTOMUS_API_KEY
    return CryptomusService(
        merchant_id=CRYPTOMUS_MERCHANT_ID, 
        api_key=CRYPTOMUS_API_KEY
    )


# =====================================================================
# 1. ВОССТАНОВЛЕННЫЙ ЭНДПОИНТ ДЛЯ BITPAPA (Оригинальный /webhook/invoice)
# =====================================================================
@router.post("/webhook/invoice")
async def invoice_webhook(request: Request):
    if not WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=503, detail="webhook is not configured")
        
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid json")

    # Оригинальная валидация секретного ключа
    if not isinstance(payload, dict) or not _verify_secret(payload.get("secret_key")):
        raise HTTPException(status_code=401, detail="invalid secret")

    invoice_id = payload.get("invoice_id")
    status_str = payload.get("status")

    if not invoice_id or status_str is None:
        raise HTTPException(status_code=400, detail="missing invoice_id or status")

    if status_str != "paid":
        return {"status": "ignored"}

    now_dt = datetime.now(timezone.utc)
    already_paid = False

    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(AllInvoices)
                .where(AllInvoices.invoice_id == str(invoice_id))
                .with_for_update()
            )
            invoice = result.scalar_one_or_none()

            if not invoice:
                raise HTTPException(status_code=404, detail="invoice not found")

            already_paid = invoice.invoice_status == "paid"

            if not already_paid:
                invoice.invoice_status = "paid"
                invoice.processing_status = "pending"
                invoice.invoice_updated_at = now_dt  # Сохраняем логику обновления даты
                
                # Записываем источник шлюза, если колонка существует
                if hasattr(invoice, "invoice_source"):
                    invoice.invoice_source = "bitpapa"
                
                session.add(invoice)

            # Пушим событие в базу для воркеров
            await create_pg_event("invoice_paid", {"invoice_id": str(invoice_id)})

    return {"status": "already_paid" if already_paid else "accepted"}


# =====================================================================
# 2. НОВЫЙ БЕЗОПАСНЫЙ ЭНДПОИНТ ДЛЯ CRYPTOMUS С ПРОВЕРКОЙ ПОДПИСИ
# =====================================================================
@router.post("/webhook/cryptomus")
async def cryptomus_webhook(
    request: Request,
    cryptomus_service: CryptomusService = Depends(get_cryptomus_service)
):
    """
    Новый изолированный вебхук Cryptomus. 
    Проверяет валидность входящей MD5 подписи шлюза.
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON structure")

    sign_to_verify = payload.get("sign")
    if not sign_to_verify:
        logger.error("Cryptomus webhook error: missing 'sign' field")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    # Валидация подписи алгоритмом MD5(base64(json) + api_key)
    if not cryptomus_service.verify_webhook_signature(payload, sign_to_verify):
        logger.error("Cryptomus webhook error: signature verification failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    status_payment = payload.get("status")
    order_id = payload.get("order_id")  # Наш внутренний invoice_id
    
    logger.info(f"Cryptomus webhook verified. Order/Invoice: {order_id}, Gateway Status: {status_payment}")

    # Обрабатываем только успешные финальные статусы
    if status_payment in ["paid", "paid_over"]:
        now_dt = datetime.now(timezone.utc)
        
        async with SessionLocal() as db:
            async with db.begin():
                stmt = select(AllInvoices).where(AllInvoices.invoice_id == str(order_id)).with_for_update()
                result = await db.execute(stmt)
                invoice = result.scalar_one_or_none()

                if not invoice:
                    logger.error(f"Cryptomus webhook: Invoice {order_id} not found in DB")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

                if invoice.invoice_status == "paid":
                    return {"status": "already_processed"}

                # Корректно обновляем все статусы и таймстампы в соответствии с вашей моделью
                invoice.invoice_status = "paid"
                invoice.processing_status = "pending"
                invoice.invoice_updated_at = now_dt
                
                if hasattr(invoice, "invoice_source"):
                    invoice.invoice_source = "cryptomus"

                db.add(invoice)
                
                # Передаем управление бизнес-логикой вашему процессору инвойсов
                await create_pg_event("invoice_paid", {"invoice_id": str(order_id)})
                logger.info(f"Cryptomus payment confirmed and event pushed for invoice: {order_id}")

    return {"status": "OK"}

# ТА САМАЯ СТРОКА, КОТОРАЯ СВЯЗЫВАЕТ РОУТЕР И ПРИЛОЖЕНИЕ FASTAPI
app.include_router(router)


# import hmac
# import json
# import logging
# import os
# from datetime import datetime, timezone

# from fastapi import APIRouter, FastAPI, HTTPException, Request
# from sqlalchemy import select

# from db.async_db import SessionLocal
# from db.models import AllInvoices
# from services.events import create_pg_event

# logger = logging.getLogger(__name__)
# app = FastAPI()
# router = APIRouter()

# # No fallback is intentional: a missing secret must disable webhook processing.
# WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


# def _verify_secret(provided: str | None) -> bool:
#     if not WEBHOOK_SECRET or not provided:
#         return False
#     return hmac.compare_digest(str(provided), WEBHOOK_SECRET)


# @router.post("/webhook/invoice")
# async def invoice_webhook(request: Request):
#     if not WEBHOOK_SECRET:
#         logger.error("WEBHOOK_SECRET is not configured")
#         raise HTTPException(status_code=503, detail="webhook is not configured")

#     try:
#         payload = await request.json()
#     except (json.JSONDecodeError, ValueError):
#         raise HTTPException(status_code=400, detail="invalid json")

#     if not isinstance(payload, dict) or not _verify_secret(payload.get("secret_key")):
#         raise HTTPException(status_code=401, detail="invalid secret")

#     invoice_id = payload.get("invoice_id")
#     status_str = payload.get("status")
#     if not invoice_id or status_str is None:
#         raise HTTPException(status_code=400, detail="missing invoice_id or status")
#     if status_str != "paid":
#         return {"status": "ignored"}

#     now_dt = datetime.now(timezone.utc)
#     already_paid = False

#     async with SessionLocal() as session:
#         async with session.begin():
#             result = await session.execute(
#                 select(AllInvoices)
#                 .where(AllInvoices.invoice_id == str(invoice_id))
#                 .with_for_update()
#             )
#             invoice = result.scalar_one_or_none()
#             if not invoice:
#                 raise HTTPException(status_code=404, detail="invoice not found")

#             already_paid = invoice.invoice_status == "paid"
#             if not already_paid:
#                 invoice.invoice_status = "paid"
#                 invoice.processing_status = "pending"
#                 invoice.invoice_updated_at = now_dt
#                 session.add(invoice)

#                 # The invoice processor owns all business processing. The webhook only marks paid.
#                 await create_pg_event("invoice_paid", {"invoice_id": str(invoice_id)})
#     return {"status": "already_paid" if already_paid else "accepted"}


# app.include_router(router)
