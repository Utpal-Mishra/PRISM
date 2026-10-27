from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from enterprise.config import EnterpriseSettings, get_settings


@dataclass(frozen=True)
class EncryptedValue:
    key_version: str
    ciphertext: str


class FieldCipher:
    def __init__(self, settings: EnterpriseSettings | None = None) -> None:
        self.settings = settings or get_settings()
        encoded = self.settings.data_encryption_key_b64.get_secret_value()
        if not encoded:
            raise RuntimeError("PRISM data encryption key is not configured.")
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
        if len(key) != 32:
            raise RuntimeError("PRISM data encryption key must decode to exactly 32 bytes.")
        self._aes = AESGCM(key)

    def encrypt_json(self, value: dict, aad: str) -> EncryptedValue:
        nonce = os.urandom(12)
        plaintext = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ciphertext = self._aes.encrypt(nonce, plaintext, aad.encode("utf-8"))
        packed = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return EncryptedValue(
            key_version=self.settings.data_encryption_key_version,
            ciphertext=packed,
        )

    def decrypt_json(self, value: EncryptedValue, aad: str) -> dict:
        if value.key_version != self.settings.data_encryption_key_version:
            raise RuntimeError("Encrypted value requires a different key version.")
        packed = base64.urlsafe_b64decode(value.ciphertext.encode("ascii"))
        plaintext = self._aes.decrypt(packed[:12], packed[12:], aad.encode("utf-8"))
        return json.loads(plaintext.decode("utf-8"))
