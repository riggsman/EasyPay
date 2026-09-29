"""Symmetric encryption for provider secrets stored in the database.

Uses Fernet (AES-128-CBC + HMAC) with a key derived from CONFIG_ENCRYPTION_KEY
or SECRET_KEY so the same engine encrypts and decrypts all provider credentials.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    settings = get_settings()
    raw = (settings.CONFIG_ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(plaintext: str) -> str:
    if plaintext is None:
        raise ValueError("plaintext required")
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_text(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    if not ciphertext.startswith(_PREFIX):
        # Legacy/plain values — returned as-is for migration safety
        return ciphertext
    token = ciphertext[len(_PREFIX) :].encode("utf-8")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt configuration value") from exc


def encrypt_json(data: dict[str, Any]) -> str:
    return encrypt_text(json.dumps(data, separators=(",", ":")))


def decrypt_json(ciphertext: str) -> dict[str, Any]:
    raw = decrypt_text(ciphertext)
    if not raw:
        return {}
    return json.loads(raw)


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(_PREFIX)


def mask_secret(value: str | None, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{'*' * max(4, len(value) - visible)}{value[-visible:]}"
