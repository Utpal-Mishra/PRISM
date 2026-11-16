from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
import psycopg
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.crypto import EncryptedValue, FieldCipher
from enterprise.models import Connector, ConnectorCredential
from enterprise.tenancy import WorkspaceAccess

SUPPORTED_CONNECTORS = {
    "rest_https",
    "postgresql",
    "snowflake_sql_api",
    "databricks_sql",
    "azure_blob_https",
    "gcs_https",
    "s3_presigned_https",
}
PLAINTEXT_SECRET_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "bearer_token",
    "api_key",
    "apikey",
    "authorization",
    "username",
    "user",
}


def _contains_plaintext_secret(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in PLAINTEXT_SECRET_KEYS:
                return True
            if _contains_plaintext_secret(item):
                return True
    elif isinstance(value, list):
        return any(_contains_plaintext_secret(item) for item in value)
    return False


class ConnectorError(RuntimeError):
    pass


def host_allowed(host: str, settings: EnterpriseSettings) -> bool:
    host = host.strip().lower()
    for allowed in settings.connector_allowed_host_list:
        if allowed.startswith("*."):
            suffix = allowed[1:]
            if host.endswith(suffix) and host != suffix[1:]:
                return True
        elif host == allowed:
            return True
    return False


def validate_connector(
    connector_type: str,
    endpoint_host: str,
    configuration: dict,
    settings: EnterpriseSettings | None = None,
) -> None:
    settings = settings or get_settings()
    if connector_type not in SUPPORTED_CONNECTORS:
        raise ConnectorError("Unsupported enterprise connector type.")
    if _contains_plaintext_secret(configuration):
        raise ConnectorError(
            "Connector configuration must not contain credentials or secret-like fields."
        )
    if not host_allowed(endpoint_host, settings):
        raise ConnectorError("Connector host is not present in the deployment allowlist.")

    if connector_type == "rest_https":
        base_url = str(configuration.get("base_url", ""))
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != endpoint_host:
            raise ConnectorError("REST connector base_url must use HTTPS and the allowed host.")
        if parsed.username or parsed.password:
            raise ConnectorError("REST connector URLs must not contain credentials.")

    if connector_type == "postgresql":
        database = str(configuration.get("database", "")).strip()
        port = int(configuration.get("port", 5432))
        if not database or not 1 <= port <= 65535:
            raise ConnectorError("PostgreSQL connector requires a database and valid port.")

    if connector_type in {
        "snowflake_sql_api",
        "databricks_sql",
        "azure_blob_https",
        "gcs_https",
    }:
        base_url = str(configuration.get("base_url", ""))
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != endpoint_host:
            raise ConnectorError(
                "Cloud connector base_url must use HTTPS and the allowed host."
            )
        if parsed.username or parsed.password:
            raise ConnectorError("Cloud connector URLs must not contain credentials.")

    if connector_type == "databricks_sql" and not str(
        configuration.get("warehouse_id", "")
    ).strip():
        raise ConnectorError("Databricks SQL requires warehouse_id.")

    if connector_type in {"azure_blob_https", "gcs_https"}:
        object_format = str(configuration.get("object_format", "json")).lower()
        if object_format not in {"json", "csv"}:
            raise ConnectorError("Object connector format must be json or csv.")


def _aad(connector_id: str, credential_version: int) -> str:
    return f"connector:{connector_id}:credential:{credential_version}"


def store_connector_credential(
    db: Session,
    access: WorkspaceAccess,
    connector: Connector,
    secret: dict,
    cipher: FieldCipher | None = None,
) -> ConnectorCredential:
    cipher = cipher or FieldCipher()
    highest = db.scalar(
        select(func.max(ConnectorCredential.credential_version)).where(
            ConnectorCredential.tenant_id == access.tenant_id,
            ConnectorCredential.workspace_id == access.workspace_id,
            ConnectorCredential.connector_id == connector.id,
        )
    )
    version = int(highest or 0) + 1
    encrypted = cipher.encrypt_json(secret, _aad(connector.id, version))

    credential = ConnectorCredential(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        connector_id=connector.id,
        credential_version=version,
        ciphertext=encrypted.ciphertext,
        key_version=encrypted.key_version,
        status="active",
    )
    db.add(credential)
    db.flush()

    previous_id = connector.active_credential_id
    connector.active_credential_id = credential.id
    if previous_id:
        previous = db.get(ConnectorCredential, previous_id)
        if (
            previous
            and previous.tenant_id == access.tenant_id
            and previous.workspace_id == access.workspace_id
        ):
            previous.status = "revoked"
            previous.revoked_at = datetime.now(UTC)
    return credential


def read_connector_secret(
    db: Session,
    connector: Connector,
    cipher: FieldCipher | None = None,
) -> dict:
    if not connector.active_credential_id:
        raise ConnectorError("Connector has no active credential.")
    credential = db.get(ConnectorCredential, connector.active_credential_id)
    if not credential or credential.status != "active":
        raise ConnectorError("Connector credential is unavailable or revoked.")
    cipher = cipher or FieldCipher()
    return cipher.decrypt_json(
        EncryptedValue(
            key_version=credential.key_version,
            ciphertext=credential.ciphertext,
        ),
        _aad(connector.id, credential.credential_version),
    )


def _schema_summary(rows: list[dict]) -> dict:
    columns: dict[str, str] = {}
    for row in rows[:100]:
        for key, value in row.items():
            current = columns.get(str(key))
            value_type = type(value).__name__
            if current is None:
                columns[str(key)] = value_type
            elif current != value_type:
                columns[str(key)] = "mixed"
    return {"columns": columns, "sampled_rows": min(len(rows), 100)}


def _content_hash(rows: list[dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def execute_rest_get(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    path = str(operation.get("path", "/"))
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise ConnectorError("REST operation path must be relative to the configured base URL.")

    headers = {"Accept": "application/json"}
    token = secret.get("bearer_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    extra_headers = secret.get("headers", {})
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if str(key).lower() in {"host", "content-length"}:
                continue
            headers[str(key)] = str(value)

    base_url = str(connector.configuration["base_url"]).rstrip("/")
    with httpx.Client(
        timeout=settings.connector_timeout_seconds,
        follow_redirects=False,
    ) as client:
        response = client.get(
            f"{base_url}{path}",
            params=operation.get("params") or {},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        rows = payload["items"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ConnectorError("REST response must be a JSON object or array.")

    normalized = [row for row in rows if isinstance(row, dict)]
    return normalized[: settings.connector_max_rows]


def _rows_from_stream(
    response: httpx.Response,
    object_format: str,
    settings: EnterpriseSettings,
) -> list[dict]:
    declared = response.headers.get("content-length")
    if declared and int(declared) > settings.max_upload_bytes:
        raise ConnectorError("Cloud object exceeds the configured ingestion byte limit.")

    if object_format == "csv":
        reader = csv.DictReader(response.iter_lines())
        rows: list[dict] = []
        for row in reader:
            rows.append(dict(row))
            if len(rows) >= settings.connector_max_rows:
                break
        return rows

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > settings.max_upload_bytes:
            raise ConnectorError("Cloud object exceeds the configured ingestion byte limit.")
        chunks.append(chunk)
    try:
        payload = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConnectorError("Cloud object contains invalid JSON.") from exc

    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        rows = payload["items"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ConnectorError("Object JSON must contain an object or array.")
    return [
        item
        for item in rows
        if isinstance(item, dict)
    ][: settings.connector_max_rows]


def execute_snowflake_sql_api(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    token = str(secret.get("bearer_token", ""))
    statement = str(operation.get("query", "")).strip()
    if not token or not statement:
        raise ConnectorError("Snowflake SQL API requires bearer_token and query.")

    config = connector.configuration
    payload: dict = {
        "statement": statement,
        "timeout": min(settings.connector_timeout_seconds, 45),
    }
    for key in ["database", "schema", "warehouse", "role"]:
        value = config.get(key)
        if value:
            payload[key] = value

    url = f"{str(config['base_url']).rstrip('/')}/api/v2/statements"
    with httpx.Client(
        timeout=settings.connector_timeout_seconds,
        follow_redirects=False,
    ) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    data = body.get("data")
    metadata = body.get("resultSetMetaData", {})
    columns = [
        str(item.get("name", f"column_{index + 1}"))
        for index, item in enumerate(metadata.get("rowType", []))
    ]
    if not isinstance(data, list):
        raise ConnectorError("Snowflake SQL API did not return inline row data.")
    if not columns and data:
        columns = [f"column_{index + 1}" for index in range(len(data[0]))]
    return [
        dict(zip(columns, row, strict=False))
        for row in data[: settings.connector_max_rows]
        if isinstance(row, list)
    ]


def execute_databricks_sql(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    token = str(secret.get("bearer_token", ""))
    statement = str(operation.get("query", "")).strip()
    if not token or not statement:
        raise ConnectorError("Databricks SQL requires bearer_token and query.")

    config = connector.configuration
    url = f"{str(config['base_url']).rstrip('/')}/api/2.0/sql/statements"
    payload = {
        "statement": statement,
        "warehouse_id": config["warehouse_id"],
        "wait_timeout": "10s",
        "on_wait_timeout": "CANCEL",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }
    with httpx.Client(
        timeout=settings.connector_timeout_seconds,
        follow_redirects=False,
    ) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    state = str(body.get("status", {}).get("state", ""))
    if state and state != "SUCCEEDED":
        raise ConnectorError(f"Databricks SQL statement ended in state {state}.")
    columns = [
        str(item.get("name", f"column_{index + 1}"))
        for index, item in enumerate(
            body.get("manifest", {}).get("schema", {}).get("columns", [])
        )
    ]
    rows = body.get("result", {}).get("data_array", [])
    return [
        dict(zip(columns, row, strict=False))
        for row in rows[: settings.connector_max_rows]
        if isinstance(row, list)
    ]


def execute_object_https(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    config = connector.configuration
    path = str(operation.get("path", config.get("resource_path", "")))
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise ConnectorError("Object path must be relative to the configured host.")

    headers = {"Accept": "application/json,text/csv;q=0.9,*/*;q=0.1"}
    token = str(secret.get("bearer_token", ""))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if connector.connector_type == "azure_blob_https":
        headers["x-ms-version"] = str(config.get("api_version", "2023-11-03"))

    url = f"{str(config['base_url']).rstrip('/')}{path}"
    with httpx.Client(
        timeout=settings.connector_timeout_seconds,
        follow_redirects=False,
    ) as client:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            return _rows_from_stream(
                response,
                str(config.get("object_format", "json")).lower(),
                settings,
            )


def execute_s3_presigned_https(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    signed_url = str(secret.get("signed_url", ""))
    if not signed_url:
        raise ConnectorError("S3 presigned connector requires encrypted signed_url.")
    parsed = urlparse(signed_url)
    if parsed.scheme != "https" or parsed.hostname != connector.endpoint_host:
        raise ConnectorError("S3 presigned URL must use the approved connector host.")

    with httpx.Client(
        timeout=settings.connector_timeout_seconds,
        follow_redirects=False,
    ) as client:
        with client.stream("GET", signed_url) as response:
            response.raise_for_status()
            return _rows_from_stream(
                response,
                str(connector.configuration.get("object_format", "json")).lower(),
                settings,
            )


def execute_postgresql_read(
    connector: Connector,
    secret: dict,
    operation: dict,
    settings: EnterpriseSettings,
) -> list[dict]:
    query = str(operation.get("query", "")).strip()
    if not query:
        raise ConnectorError("PostgreSQL operation requires a query.")

    user = str(secret.get("username", ""))
    password = str(secret.get("password", ""))
    if not user or not password:
        raise ConnectorError("PostgreSQL connector credential is incomplete.")

    config = connector.configuration
    with psycopg.connect(
        host=connector.endpoint_host,
        port=int(config.get("port", 5432)),
        dbname=str(config["database"]),
        user=user,
        password=password,
        connect_timeout=settings.connector_timeout_seconds,
        options="-c default_transaction_read_only=on",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, operation.get("parameters") or None)
            if cursor.description is None:
                raise ConnectorError("Connector queries must return rows.")
            columns = [item.name for item in cursor.description]
            values = cursor.fetchmany(settings.connector_max_rows)
    return [dict(zip(columns, row, strict=True)) for row in values]


def fetch_connector_rows(
    db: Session,
    connector: Connector,
    operation: dict,
    settings: EnterpriseSettings | None = None,
) -> list[dict]:
    settings = settings or get_settings()
    validate_connector(
        connector.connector_type,
        connector.endpoint_host,
        connector.configuration,
        settings,
    )
    secret = read_connector_secret(db, connector)
    if connector.connector_type == "rest_https":
        return execute_rest_get(connector, secret, operation, settings)
    if connector.connector_type == "postgresql":
        return execute_postgresql_read(connector, secret, operation, settings)
    if connector.connector_type == "snowflake_sql_api":
        return execute_snowflake_sql_api(connector, secret, operation, settings)
    if connector.connector_type == "databricks_sql":
        return execute_databricks_sql(connector, secret, operation, settings)
    if connector.connector_type in {"azure_blob_https", "gcs_https"}:
        return execute_object_https(connector, secret, operation, settings)
    if connector.connector_type == "s3_presigned_https":
        return execute_s3_presigned_https(connector, secret, operation, settings)
    raise ConnectorError("Unsupported enterprise connector type.")


def execute_connector(
    db: Session,
    connector: Connector,
    operation: dict,
    settings: EnterpriseSettings | None = None,
) -> dict:
    settings = settings or get_settings()
    rows = fetch_connector_rows(db, connector, operation, settings)
    return {
        "row_count": len(rows),
        "content_hash": _content_hash(rows),
        "schema_summary": _schema_summary(rows),
    }
