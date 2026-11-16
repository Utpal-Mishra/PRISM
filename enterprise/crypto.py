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
        keyring: dict[str, str] = {}
        raw_keyring = self.settings.data_encryption_keys_json.get_secret_value()
        if raw_keyring:
            try:
                parsed = json.loads(raw_keyring)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "PRISM data encryption keyring must be valid JSON."
                ) from exc
            if not isinstance(parsed, dict):
                raise RuntimeError(
                    "PRISM data encryption keyring must be a version-to-key object."
                )
            keyring.update({str(key): str(value) for key, value in parsed.items()})

        current_version = self.settings.data_encryption_key_version
        current_key = self.settings.data_encryption_key_b64.get_secret_value()
        if current_key:
            keyring[current_version] = current_key
        if current_version not in keyring:
            raise RuntimeError(
                "PRISM current data encryption key version is not configured."
            )

        self._keys: dict[str, AESGCM] = {}
        for version, encoded in keyring.items():
            try:
                key = base64.urlsafe_b64decode(encoded.encode("ascii"))
            except Exception as exc:
                raise RuntimeError(
                    f"PRISM encryption key {version} is not valid urlsafe-base64."
                ) from exc
            if len(key) != 32:
                raise RuntimeError(
                    f"PRISM encryption key {version} must decode to exactly 32 bytes."
                )
            self._keys[version] = AESGCM(key)

        self._current_version = current_version

    def encrypt_json(self, value: dict, aad: str) -> EncryptedValue:
        nonce = os.urandom(12)
        plaintext = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        ciphertext = self._keys[self._current_version].encrypt(
            nonce,
            plaintext,
            aad.encode(),
        )
        packed = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
        return EncryptedValue(
            key_version=self._current_version,
            ciphertext=packed,
        )

    def decrypt_json(self, value: EncryptedValue, aad: str) -> dict:
        aes = self._keys.get(value.key_version)
        if aes is None:
            raise RuntimeError(
                f"Encrypted value requires unavailable key version {value.key_version}."
            )
        packed = base64.urlsafe_b64decode(value.ciphertext.encode("ascii"))
        plaintext = aes.decrypt(
            packed[:12],
            packed[12:],
            aad.encode(),
        )
        return json.loads(plaintext.decode())
