from __future__ import annotations

import base64
import secrets


def main() -> None:
    print("PRISM_AUDIT_HMAC_KEY=" + secrets.token_urlsafe(48))
    print(
        "PRISM_DATA_ENCRYPTION_KEY_B64="
        + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    )


if __name__ == "__main__":
    main()
