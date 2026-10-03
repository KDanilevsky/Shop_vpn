# services/cryptomus.py
import hashlib
import json
import base64
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class CryptomusService:
    def __init__(self, merchant_id: str, api_key: str, api_url: str = "https://cryptomus.com"):
        self.merchant_id = merchant_id
        self.api_key = api_key
        self.api_url = api_url

    def _generate_signature(self, payload: dict) -> str:
        """Спецификация Cryptomus: md5(base64(json) + api_key)"""
        json_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
        encoded_payload = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return hashlib.md5((encoded_payload + self.api_key).encode('utf-8')).hexdigest()

    def verify_webhook_signature(self, payload: dict, sign_to_verify: str) -> bool:
        """Проверка подписи входящего вебхука."""
        data = payload.copy()
        data.pop("sign", None)
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        encoded_payload = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return hashlib.md5((encoded_payload + self.api_key).encode('utf-8')).hexdigest() == sign_to_verify

    async def create_invoice(self, amount_usd: float, order_id: str, callback_url: str, success_url: str) -> Optional[Dict[str, Any]]:
        """Создание счета СБП в рублях с конвертацией из USD."""
        url = f"{self.api_url}/payment"
        payload = {
            "amount": f"{amount_usd:.2f}",
            "currency": "USD",
            "order_id": str(order_id),
            "url_callback": callback_url,
            "url_return": success_url,
            "to_currency": "RUB",
            "payment_method": "sbp"
        }
        headers = {
            "merchant": self.merchant_id,
            "sign": self._generate_signature(payload),
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("state") == 0:
                        return {
                            "uuid": data["result"]["uuid"],
                            "pay_url": data["result"]["url"],
                            "status": data["result"]["status"]
                        }
                logger.error(f"Cryptomus error {response.status_code}: {response.text}")
            except Exception as e:
                logger.exception(f"Cryptomus connection failed: {e}")
        return None

    async def check_status(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Аварийная проверка статуса счета по нашему внутреннему invoice_id (order_id).
        Используется воркером-реконсиллером для подстраховки вебхуков.
        """
        url = f"{self.api_url}/payment/info"
        
        # Передаем order_id, так как воркер при парсинге незавершенных счетов из БД 
        # знает только наш внутренний номер инвойса
        payload = {
            "order_id": str(invoice_id)
        }
        
        headers = {
            "merchant": self.merchant_id,
            "sign": self._generate_signature(payload),
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    # state = 0 означает, что запрос к API прошел успешно
                    if data.get("state") == 0:
                        return {
                            "uuid": data["result"]["uuid"],
                            "status": data["result"]["status"],  # 'paid', 'pending', 'cancel' и т.д.
                            "is_paid": data["result"]["status"] in ["paid", "paid_over"]
                        }
                logger.error(f"Cryptomus check_status error {response.status_code}: {response.text}")
            except Exception as e:
                logger.exception(f"Cryptomus check_status connection failed for invoice {invoice_id}: {e}")
        return None
