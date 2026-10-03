# services/provision.py v16

import httpx
import logging
import uuid
import time
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from typing import Dict, Any, Optional

from db.async_db import SessionLocal
from db.models import SubscriptionTransaction, UserSubscription, AllTariffs, AllUsers
from config import XUI_MASTER_URL, XUI_MASTER_USER, XUI_MASTER_PASSWORD, XUI_SUB_DOMAIN, EXCLUDED_INBOUND_IDS

logger = logging.getLogger(__name__)

class MasterXUIClient:
    def __init__(self):
        self.base_url = XUI_MASTER_URL.rstrip('/')
        self.username = XUI_MASTER_USER
        self.password = XUI_MASTER_PASSWORD
        self.cookies = None

    async def login(self) -> bool:
        """Авторизация на мастер-панели 3x-ui для получения сессии"""
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/login",
                    data={"username": self.username, "password": self.password}
                )
                if resp.status_code == 200 and resp.json().get("success"):
                    self.cookies = resp.cookies
                    return True
                return False
            except Exception as e:
                logger.error(f"Сбой авторизации на Мастере 3x-ui: {e}")
                return False

    async def get_all_inbound_ids(self) -> list:
        """Получает список всех активных инбаундов на Мастере, исключая технические"""
        if not self.cookies and not await self.login():
            return []
        async with httpx.AsyncClient(cookies=self.cookies, timeout=10.0, verify=False) as client:
            try:
                resp = await client.get(f"{self.base_url}/panel/api/inbounds/list")
                if resp.status_code == 200:
                    from config import EXCLUDED_INBOUND_IDS
                    
                    # Фильтруем: инбаунд должен быть включен и его ID не должен быть в списке исключений
                    return [
                        ib["id"] for ib in resp.json().get("obj", []) 
                        if ib.get("enable") and ib["id"] not in EXCLUDED_INBOUND_IDS
                    ]
                return []
            except Exception as e:
                logger.error(f"Ошибка получения инбаундов: {e}")
                return []


    async def add_or_update_client(self, client_spec: dict, inbound_ids: list, is_update: bool = False) -> bool:
        """Добавляет или обновляет клиента на всех инбаундах панели одновременно"""
        if not self.cookies and not await self.login():
            return False
        
        endpoint = "updateClient" if is_update else "addClient"
        payload = {
            "client": client_spec,
            "inboundIds": inbound_ids
        }
        
        async with httpx.AsyncClient(cookies=self.cookies, timeout=15.0, verify=False) as client:
            try:
                # В форке MHSanaei для добавления/изменения используется POST запрос на инбаунды
                resp = await client.post(f"{self.base_url}/panel/api/inbounds/{endpoint}", json=payload)
                return resp.status_code == 200 and resp.json().get("success")
            except Exception as e:
                logger.error(f"Ошибка взаимодействия с API 3x-ui ({endpoint}): {e}")
                return False

xui_master = MasterXUIClient()

async def provision_subscription_for_user(tx_id: int) -> Dict[str, Any]:
    """
    Vydacha podpisok na Master-paneli 3x-ui s podderzhkoj slozhnoj struktury items.
    v18: Polnostyu atomarnyj i bezopasnyj proshchet vseh slozhnyh paketov.
    """
    async with SessionLocal() as session:
        async with session.begin():
            # 1. Zagruzhaem bazu dannyh bez dolgih lockov
            tx = await session.get(SubscriptionTransaction, tx_id)
            if not tx:
                return {"status": "error", "message": "Transaction not found"}

            user = await session.get(AllUsers, tx.user_id)
            plan_id = tx.payload_meta.get("tariff_id")
            tariff = await session.get(AllTariffs, plan_id)
            
            if not user or not tariff:
                return {"status": "error", "message": "User or Tariff not found"}

            # Zdes' chitaem spisok kuplennyh slotov iz vashego massiva items
            items_list = tx.payload_meta.get("items", [])
            if not items_list:
                return {"status": "error", "message": "No items found in payload_meta"}

    # 2. Poluchaem spisok chistyh inbound_ids (Uzhe s uchetom iskluchenij!)
    inbound_ids = await xui_master.get_all_inbound_ids()
    if not inbound_ids:
        return {"status": "error", "message": "No active inbounds on 3x-ui master"}

    # Obshchie raschety vremeni i trafika dlya vseh slotov paketa
    now_dt = datetime.now(timezone.utc)
    stop_dt = now_dt + timedelta(days=tariff.duration_days)
    expiry_time_ms = int(stop_dt.timestamp() * 1000)
    total_bytes = tariff.gb_limit * 1024 * 1024 * 1024 if tariff.gb_limit > 0 else 0

    slots_result = {}

    # 3. Glavnyj cikl: Iteraem po kazhdomu slotu v pakete pokupki
    for item in items_list:
        acc_number = item.get("acc_number", 1)

        # Proveryaem, est' li uzhe tokeny u etogo konkretnogo slota
        async with SessionLocal() as session_slot:
            async with session_slot.begin():
                r_sub = await session_slot.execute(
                    select(UserSubscription).where(
                        UserSubscription.user_id == user.user_id,
                        UserSubscription.acc_number == acc_number
                    )
                )
                existing_sub = r_sub.scalar_one_or_none()

        if existing_sub:
            sub_id_token = existing_sub.sub_id
            client_uuid = existing_sub.client_uuid
            is_update = True
        else:
            sub_id_token = str(uuid.uuid4())
            client_uuid = str(uuid.uuid4())
            is_update = False

        client_email = f"user_{user.user_id}_slot_{acc_number}"
        
        client_spec = {
            "id": client_uuid,
            "email": client_email,
            "limitIp": tx.payload_meta.get("device_limit", 1), # Читаем из метаданных tx
            "totalGB": tx.payload_meta.get("gb_limit", 0) * 1024 * 1024 * 1024,
            "expiryTime": expiry_time_ms,
            "enable": True,
            "tgId": str(user.user_id),
            "subId": sub_id_token
        }


        # 4. Sinhroniziruem klienta s panel'yu 3x-ui
        success = await xui_master.add_or_update_client(client_spec, inbound_ids, is_update=is_update)
        if not success:
            return {"status": "error", "message": f"Failed to sync slot {acc_number} with 3x-ui master"}

        subscription_link = f"{XUI_SUB_DOMAIN.rstrip('/')}/sub/{sub_id_token}"

        # Skladyvaem rezul'tat v obshchij massiv slots dlya process_tx.py
        slots_result[str(acc_number)] = {
            "settings_string": subscription_link,
            "img_path": None,
            "sub_id_token": sub_id_token,
            "client_uuid": client_uuid,
            "stop_time": stop_dt
        }

    return {
        "status": "success",
        "slots": slots_result
    }

