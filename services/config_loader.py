# services/config_loader.py

import os
import json
from pathlib import Path
from typing import Optional, Any, Dict, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.secret_resolver import resolve_secret

def encrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, data, None)
    return nonce + ct

def decrypt_aes_gcm(data: bytes, key: bytes) -> bytes:
    aes = AESGCM(key)
    nonce, ct = data[:12], data[12:]
    return aes.decrypt(nonce, ct, None)

class EncryptedConfigLoader:
    """
    Unified loader for plaintext or AES‑GCM encrypted JSON configs.
    Supports:
      - servers.json / servers.enc
      - config.json / config.enc
      - secret key resolution via AWS SM / GCP SM / Vault
    """

    def __init__(
        self,
        path: str,
        key_ref: Optional[str] = None,
        settings: Optional[Any] = None,
        auto_resolve_key: bool = True,
    ):
        self.path = Path(path)
        self.key_ref = key_ref
        self.settings = settings
        self.key: Optional[bytes] = None

        if auto_resolve_key and key_ref:
            self.key = self._resolve_key()

    # -------------------------
    # Key resolution
    # -------------------------
    def _resolve_key(self) -> Optional[bytes]:
        key_hex = resolve_secret(self.key_ref, self.settings)
        if not key_hex:
            raise RuntimeError(f"Failed to resolve key for {self.path}")
        return bytes.fromhex(key_hex)

    # -------------------------
    # AES‑GCM decrypt
    # -------------------------
    @staticmethod
    def _decrypt(data: bytes, key: bytes) -> bytes:
        aes = AESGCM(key)
        nonce, ct = data[:12], data[12:]
        return aes.decrypt(nonce, ct, None)

    # -------------------------
    # Load + parse JSON
    # -------------------------
    def load(self) -> Any:
        if not self.path.exists():
            return None

        raw = self.path.read_bytes()

        if self.key:
            raw = self._decrypt(raw, self.key)

        return json.loads(raw.decode("utf-8"))

    # -------------------------
    # Convenience helpers
    # -------------------------
    def load_dict(self) -> Dict[str, Any]:
        data = self.load()
        return data if isinstance(data, dict) else {}

    def load_list(self) -> List[Any]:
        data = self.load()
        return data if isinstance(data, list) else []
