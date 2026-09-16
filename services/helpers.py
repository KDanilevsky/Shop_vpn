# services/helpers.py
import os
import json
import asyncio
import logging

from db.models import SecretToken, UserNotifications
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import random
from typing import Tuple, Dict, List, Any, Optional
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

import secrets

# import os
# from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# def encrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
#     aes = AESGCM(key)
#     nonce = os.urandom(12)
#     ct = aes.encrypt(nonce, data, None)
#     return nonce + ct

# def decrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
#     aes = AESGCM(key)
#     nonce, ct = data[:12], data[12:]
#     return aes.decrypt(nonce, ct, None)


# # Optional imports for vault integrations
# try:
#     import boto3
#     from botocore.exceptions import BotoCoreError, ClientError
# except Exception:
#     boto3 = None

# try:
#     import hvac
# except Exception:
#     hvac = None

# try:
#     from google.cloud import secretmanager
# except Exception:
#     secretmanager = None

# logger = logging.getLogger(__name__)

def _now_utc():
    return datetime.now(timezone.utc)

# -------------------------
# Settings
# -------------------------
# class ServerConfig(BaseSettings):
#     id: Optional[int]
#     http: Optional[str]
#     username: Optional[str]
#     password: Optional[str]
#     token: Optional[str]
#     ip: Optional[str]
#     sert: Optional[str]
#     max_subscriptions: int = Field(default=999999)
#     all_subscriptions: int = Field(default=0)
#     region: Optional[int] = None

#     model_config = {"extra": "allow"}


# class ServersSettings(BaseSettings):
#     servers_json_path: str = Field(default="servers.json", env="SERVERS_JSON")
#     servers_json_inline: Optional[str] = Field(default=None, env="SERVERS_JSON_INLINE")
#     refresh_interval_seconds: int = Field(default=60, env="SERVERS_REFRESH_SECONDS")
#     vault_type: Optional[str] = Field(default=None, env="SERVERS_VAULT_TYPE")  # "aws_sm" or "hashicorp"
#     aws_region: Optional[str] = Field(default=None, env="AWS_REGION")
#     hashicorp_addr: Optional[str] = Field(default=None, env="VAULT_ADDR")
#     hashicorp_token: Optional[str] = Field(default=None, env="VAULT_TOKEN")

#     model_config = {
#         "env_file": ".env",
#         "env_file_encoding": "utf-8",
#     }

#     @field_validator("servers_json_inline", mode="before")
#     @classmethod
#     def empty_to_none(cls, v):
#         return v or None


# -------------------------
# Global cache
# -------------------------
_SERVERS_CACHE: List[Dict[str, Any]] = []
_SERVERS_META: Dict[int, Dict[str, Any]] = {}
_CACHE_LOCK = asyncio.Lock()
_REFRESH_TASK: Optional[asyncio.Task] = None

# -------------------------
# Secret resolvers
# -------------------------
# def _is_vault_ref(value: Optional[str]) -> bool:
#     return isinstance(value, str) and (value.startswith("vault://") or value.startswith("aws-sm://"))

# def _parse_vault_ref(ref: str) -> Tuple[str, str]:
#     if "#" in ref:
#         base, key = ref.split("#", 1)
#     else:
#         base, key = ref, ""
#     return base, key

# async def resolve_secret(ref: str, settings: ServersSettings) -> Optional[str]:
#     """
#     Resolve a secret reference. Supports:
#       - aws-sm://secret-name[#json_key]
#       - vault://path/to/secret[#key]
#     Returns resolved string or None on failure.
#     """
#     if ref.startswith("aws-sm://"):
#         if boto3 is None:
#             raise RuntimeError("boto3 not installed for AWS Secrets Manager resolution")
#         secret_name, json_key = _parse_vault_ref(ref.replace("aws-sm://", "", 1))
#         try:
#             client = boto3.client("secretsmanager", region_name=settings.aws_region)
#             resp = client.get_secret_value(SecretId=secret_name)
#             secret_string = resp.get("SecretString")
#             if not secret_string:
#                 return None
#             if json_key:
#                 try:
#                     data = json.loads(secret_string)
#                     return data.get(json_key)
#                 except Exception:
#                     return None
#             return secret_string
#         except (BotoCoreError, ClientError) as e:
#             logger.exception("AWS SM error resolving %s: %s", ref, e)
#             return None

#     if ref.startswith("vault://"):
#         if hvac is None:
#             raise RuntimeError("hvac not installed for HashiCorp Vault resolution")
#         path, key = _parse_vault_ref(ref.replace("vault://", "", 1))
#         try:
#             client = hvac.Client(url=settings.hashicorp_addr, token=settings.hashicorp_token)
#             # Try KV v2 first, fallback to v1
#             try:
#                 resp = client.secrets.kv.v2.read_secret_version(path=path)
#                 data = resp["data"]["data"]
#             except Exception:
#                 resp = client.secrets.kv.v1.read_secret(path=path)
#                 data = resp.get("data", {})
#             if key:
#                 return data.get(key)
#             if isinstance(data, dict) and len(data) == 1:
#                 return next(iter(data.values()))
#             return json.dumps(data)
#         except Exception as e:
#             logger.exception("Vault error resolving %s: %s", ref, e)
#             return None
        
#     if ref.startswith("gcp-sm://"):
#         if secretmanager is None:
#             raise RuntimeError("google-cloud-secret-manager not installed")
#         name, json_key = _parse_vault_ref(ref.replace("gcp-sm://", "", 1))
#         try:
#             client = secretmanager.SecretManagerServiceClient()
#             resp = client.access_secret_version(request={"name": name})
#             secret_string = resp.payload.data.decode("utf-8")
#             if json_key:
#                 data = json.loads(secret_string)
#                 return data.get(json_key)
#             return secret_string
#         except Exception as e:
#             logger.exception("GCP SM error resolving %s: %s", ref, e)
#             return None

#     # not a vault ref -> return as-is
#     return ref

# -------------------------
# Loading and normalization
# -------------------------
def _load_servers_from_file(path: str, key: Optional[bytes]) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []

    data = p.read_bytes()

    # If key is provided → decrypt
    if key is not None:
        try:
            data = decrypt_aes_gcm(data, key)
        except Exception:
            logger.exception("Failed to decrypt servers file %s", path)
            return []

    # Try to parse JSON
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        logger.exception("Failed to parse servers file %s", path)
        return []

def load_config_file(path: str, key: Optional[bytes]) -> dict:
    p = Path(path)
    if not p.exists():
        return {}

    data = p.read_bytes()

    if key is not None:
        try:
            data = decrypt_aes_gcm(data, key)
        except Exception:
            logger.exception("Failed to decrypt config file %s", path)
            return {}

    return json.loads(data.decode("utf-8"))



async def _resolve_server_secrets(server: Dict[str, Any], settings: ServersSettings) -> Dict[str, Any]:
    out = dict(server)
    for key in ("username", "password", "token"):
        val = out.get(key)
        if val and _is_vault_ref(val):
            try:
                resolved = await resolve_secret(val, settings)
                if resolved is not None:
                    out[key] = resolved
            except Exception:
                logger.exception("Failed to resolve secret for server %s key %s", server.get("id"), key)
    return out

async def _load_and_normalize(settings: ServersSettings) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    if settings.servers_json_inline:
        try:
            raw = json.loads(settings.servers_json_inline)
        except Exception:
            logger.exception("Failed to parse SERVERS_JSON_INLINE")
            raw = []
    else:
        raw = _load_servers_from_file(settings.servers_json_path)

    normalized: List[Dict[str, Any]] = []
    for i, s in enumerate(raw):
        server = dict(s)
        if "id" not in server or server["id"] is None:
            server["id"] = i + 1
        server["max_subscriptions"] = int(server.get("max_subscriptions", 999999))
        server["all_subscriptions"] = int(server.get("all_subscriptions", 0))
        normalized.append(server)

    tasks = [_resolve_server_secrets(s, settings) for s in normalized]
    resolved = await asyncio.gather(*tasks, return_exceptions=False)

    meta = {int(s["id"]): s for s in resolved}
    return resolved, meta

# -------------------------
# Public API and cache management
# -------------------------

async def refresh_servers_cache():
    global _SERVERS_CACHE, _SERVERS_META

    async with _CACHE_LOCK:
        try:
            loader = EncryptedConfigLoader(
                path=os.getenv("SERVERS_PATH", "servers.enc"),
                key_ref=os.getenv("SERVERS_KEY_REF"),
            )

            raw = loader.load_list()
            servers, meta = await _load_and_normalize_from_raw(raw)

            _SERVERS_CACHE = servers
            _SERVERS_META = meta

            await sync_servers_to_db()

        except Exception:
            logger.exception("Failed to refresh servers cache")

# async def refresh_servers_cache(settings: ServersSettings):
#     global _SERVERS_CACHE, _SERVERS_META
#     async with _CACHE_LOCK:
#         try:
#             servers, meta = await _load_and_normalize(settings)
#             _SERVERS_CACHE = servers
#             _SERVERS_META = meta

#             # NEW: sync DB metadata
#             await sync_servers_to_db()

#             logger.info("Servers cache refreshed: %d servers", len(servers))
#         except Exception:
#             logger.exception("Failed to refresh servers cache")

async def init_servers_cache(settings: Optional[ServersSettings] = None):
    """
    Initialize cache and start background refresh task.
    Call this once at application startup.
    """
    global _REFRESH_TASK
    if settings is None:
        settings = ServersSettings()

    await refresh_servers_cache(settings)

    if _REFRESH_TASK is None or _REFRESH_TASK.done():
        loop = asyncio.get_running_loop()
        _REFRESH_TASK = loop.create_task(_periodic_refresh(settings))

async def _periodic_refresh(settings: ServersSettings):
    interval = max(10, int(settings.refresh_interval_seconds))
    try:
        while True:
            await asyncio.sleep(interval)
            await refresh_servers_cache(settings)
    except asyncio.CancelledError:
        logger.info("Servers cache refresh task cancelled")
        raise

def get_servers_list() -> List[Dict[str, Any]]:
    """Return cached list of servers. Call init_servers_cache at startup."""
    return list(_SERVERS_CACHE)

def get_servers_meta() -> Dict[int, Dict[str, Any]]:
    """Return cached mapping server_id -> server dict."""
    return dict(_SERVERS_META)

def choose_server_for_subs(subs_id: int, prefer_region: Optional[int] = None) -> Optional[int]:
    """
    Choose server id using cached servers.
    Strategy:
      - prefer servers with available capacity
      - prefer region if provided
      - pick least-loaded by ratio
    Returns server_id or None.
    """
    servers = get_servers_list()
    candidates = [s for s in servers if int(s.get("all_subscriptions", 0)) < int(s.get("max_subscriptions", 999999))]
    if not candidates:
        return None
    if prefer_region is not None:
        for s in candidates:
            if s.get("region") == prefer_region:
                return int(s["id"])
    def load_ratio(s):
        max_subs = int(s.get("max_subscriptions", 999999))
        current = int(s.get("all_subscriptions", 0))
        return current / max_subs if max_subs else 1.0
    chosen = min(candidates, key=load_ratio)
    return int(chosen["id"])


async def sync_servers_to_db():
    async with SessionLocal() as session:
        meta = get_servers_meta()
        existing = await session.scalars(select(AllServers.id))
        existing_ids = set(existing.all())

        for sid, cfg in meta.items():
            if sid not in existing_ids:
                session.add(AllServers(
                    id=sid,
                    country_id=cfg.get("region") or 0,
                    server_id=sid,
                ))

        await session.commit()



# ---------------------------------------------------------
# SECRET TOKEN (payfor, invite)
# ---------------------------------------------------------
# usage example:
# payfor_token = await get_or_create_secret_token(session, user_id, "payfor", days=1, metadata={"subs_id": subs_id})
# invite_token = await get_or_create_secret_token(session, user_id, "invite")
# promo_token = await get_or_create_secret_token(session, user_id, "promo", days=1)

async def get_or_create_secret_token(
    session,
    owner_user_id: int,
    purpose: str,
    days: int | None = None,
    metadata: dict | None = None,
) -> str:
    now = _now_utc()

    # Try to reuse existing non-expired token
    result = await session.execute(
        select(SecretToken)
        .where(
            SecretToken.owner_user_id == owner_user_id,
            SecretToken.purpose == purpose,
            (SecretToken.expires_at.is_(None)) | (SecretToken.expires_at > now),
        )
        .order_by(SecretToken.created_at.desc())
        .limit(1)
    )
    token_obj = result.scalar_one_or_none()
    if token_obj:
        return token_obj.token

    # Create new token
    token = secrets.token_hex(16)  # 128-bit

    expires_at = None
    if days is not None:
        expires_at = now + timedelta(days=days)

    token_obj = SecretToken(
        token=token,
        owner_user_id=owner_user_id,
        purpose=purpose,
        created_at=now,
        expires_at=expires_at,
        metadata_=metadata,
    )

    session.add(token_obj)
    await session.commit()
    return token


# notifications to users enqueue creation (to be processed by background worker):

async def enqueue_notification(
    session,
    user_id: int,
    reason: str,
    invoice_id: str | None = None,
    subscription_id: int | None = None,
    payload: dict | None = None,
):
    notif = UserNotifications(
        user_id=user_id,
        reason=reason,
        invoice_id=invoice_id,
        subscription_id=subscription_id,
        payload=payload or {},
        sent_at=None,
        attempt_count=0,
        next_attempt_at=None,
        failed_permanently=False,
        last_error=None,
    )
    session.add(notif)


# async def create_pg_event(
#     event: str,
#     payload: str | int | None = None,
#     session: Optional[AsyncSession] = None,
#     channel: str = "events",
# ) -> None:
#     """
#     Emit a NOTIFY event on the given channel.
#     event: event type, e.g. "tx", "invoice", "notify"
#     payload: optional payload (int or str)
#     """
#     if payload is None:
#         full_payload = event
#     else:
#         full_payload = f"{event}:{payload}"

#     try:
#         if session is not None:
#             conn = await session.connection()
#             await conn.execute(
#                 text(f"NOTIFY {channel}, :payload"),
#                 {"payload": full_payload},
#             )
#             return

#         async with SessionLocal() as s:
#             async with s.begin():
#                 conn = await s.connection()
#                 await conn.execute(
#                     text(f"NOTIFY {channel}, :payload"),
#                     {"payload": full_payload},
#                 )

#     except Exception:
#         logger.exception("Failed to NOTIFY %s with payload %s", channel, full_payload)

