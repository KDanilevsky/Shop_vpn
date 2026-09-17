import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import qrcode
from py3xui import AsyncApi, Client

from config import QRCODES_DIR

DEFAULT_INBOUND_ID = 1
DEFAULT_FLOW = "xtls-rprx-vision"


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _first_inbound(inbounds: Iterable[Any]) -> Any:
    inbound = next(iter(inbounds), None)
    if inbound is None:
        raise LookupError("3x-ui returned no inbounds")
    return inbound


def _clients(inbound: Any) -> list[Any]:
    settings = getattr(inbound, "settings", None)
    clients = getattr(settings, "clients", None) if settings is not None else None
    return list(clients or [])


def _find_client(inbounds: Iterable[Any], email: str) -> tuple[Any, Any] | tuple[None, None]:
    for inbound in inbounds:
        for client in _clients(inbound):
            if getattr(client, "email", None) == email:
                return inbound, client
    return None, None


async def add_client_to_3xui_server(
    async_api: AsyncApi,
    new_client_email: str,
    new_expiry_time: int,
    new_tg_id: int | str,
    inbound_id: int = DEFAULT_INBOUND_ID,
) -> Any:
    """Create a client in 3x-ui. ``expiry_time`` is Unix time in milliseconds."""
    client = Client(
        id=str(uuid.uuid4()),
        email=new_client_email,
        expiry_time=int(new_expiry_time),
        tg_id=str(new_tg_id),
        flow=DEFAULT_FLOW,
        enable=True,
    )
    return await async_api.client.add(inbound_id, [client])


async def update_existing_3xui_client(
    async_api: AsyncApi,
    inbounds: Iterable[Any],
    user_email: str,
    dayz: int,
) -> int:
    if dayz <= 0:
        raise ValueError("dayz must be positive")

    inbound_list = list(inbounds or [])
    if not inbound_list:
        raise LookupError("3x-ui returned no inbounds")

    client = await async_api.client.get_by_email(user_email)
    if client is None:
        raise LookupError(f"3x-ui client not found: {user_email}")

    current_expiry = int(getattr(client, "expiry_time", 0) or 0)
    if current_expiry <= _now_ms():
        new_expiry = _now_ms() + dayz * 24 * 60 * 60 * 1000
    else:
        new_expiry = current_expiry + dayz * 24 * 60 * 60 * 1000

    _, stored_client = _find_client(inbound_list, user_email)
    client.id = getattr(stored_client, "id", None) or getattr(client, "id", None)
    if not client.id:
        raise LookupError(f"3x-ui client id not found: {user_email}")

    client.expiry_time = new_expiry
    await async_api.client.update(client.id, client, flow=DEFAULT_FLOW)
    return new_expiry


async def delete_depleted_clients(
    async_api: AsyncApi,
    inbound: Any | None = None,
    inbound_id: int | None = None,
) -> Any:
    resolved_id = inbound_id or getattr(inbound, "id", None) or DEFAULT_INBOUND_ID
    return await async_api.client.delete_depleted(resolved_id)


async def delete_client(
    async_api: AsyncApi,
    tg_id: int | str,
    suff: str,
    inbound_id: int = DEFAULT_INBOUND_ID,
) -> bool:
    user_email = f"{tg_id}-{suff}"
    inbounds = await async_api.inbound.get_list()
    _, client = _find_client(inbounds or [], user_email)
    if client is None:
        return False

    client_id = getattr(client, "id", None)
    if not client_id:
        raise LookupError(f"3x-ui client id not found: {user_email}")
    await async_api.client.delete(inbound_id, client_id)
    return True


def _reality_settings(inbound: Any) -> dict[str, Any]:
    stream = getattr(inbound, "stream_settings", None)
    reality = getattr(stream, "reality_settings", None) if stream else None
    if not isinstance(reality, dict):
        raise ValueError("Inbound has no valid Reality settings")
    settings = reality.get("settings") or {}
    server_names = reality.get("serverNames") or []
    short_ids = reality.get("shortIds") or []
    required = settings.get("publicKey"), settings.get("fingerprint"), server_names, short_ids
    if not required[0] or not required[1] or not server_names or not short_ids:
        raise ValueError("Inbound Reality settings are incomplete")
    return {
        "public_key": settings["publicKey"],
        "fingerprint": settings["fingerprint"],
        "sni": server_names[0],
        "short_id": short_ids[0],
    }


async def get_client_settings_string_and_qr(
    inbounds: Iterable[Any],
    user_email: str,
    vpn_ip: str,
) -> tuple[str, str]:
    inbound_list = list(inbounds or [])
    inbound, client = _find_client(inbound_list, user_email)
    if inbound is None or client is None:
        raise LookupError(f"3x-ui client not found: {user_email}")

    stream = getattr(inbound, "stream_settings", None)
    reality = _reality_settings(inbound)
    network = getattr(stream, "network", "tcp")
    protocol = getattr(inbound, "protocol", "vless")
    port = getattr(inbound, "port", None)
    client_id = getattr(client, "id", None)
    if not port or not client_id:
        raise ValueError("Inbound/client is missing port or client id")

    settings = (
        f"{protocol}://{client_id}@{vpn_ip}:{port}"
        f"?type={quote(str(network))}&security=reality"
        f"&pbk={quote(str(reality['public_key']))}"
        f"&fp={quote(str(reality['fingerprint']))}"
        f"&sni={quote(str(reality['sni']))}"
        f"&sid={quote(str(reality['short_id']))}"
        f"&flow={quote(DEFAULT_FLOW)}"
    )

    qr_dir = Path(QRCODES_DIR)
    qr_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{user_email}.png"
    image_path = qr_dir / safe_name
    qrcode.make(settings).save(image_path)
    return settings, str(image_path)


__all__ = [
    "AsyncApi",
    "add_client_to_3xui_server",
    "update_existing_3xui_client",
    "delete_depleted_clients",
    "delete_client",
    "get_client_settings_string_and_qr",
]
