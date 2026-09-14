#!/usr/bin/env python3
"""Integray Remote API connection, Config Transfer download, and backup."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urljoin

import httpx

CONNECTION_HELP = (
    "Fill projects/<name>/.integray-connection.json with baseUrl, companySlug, and token. "
    "Do not infer companySlug from baseUrl."
)

DEFAULT_TIMEOUT_SECONDS = 300.0

_CONTENT_DISPOSITION_FILENAME = re.compile(
    r"filename\*?=(?:UTF-8''([^;]+)|\"([^\"]+)\"|([^;\s]+))",
    re.IGNORECASE,
)


class RemoteError(RuntimeError):
    """Remote API call failed."""


DownloadError = RemoteError


@dataclass
class ConnectionConfig:
    base_url: str
    company_slug: str
    token: str
    path: Path | None = None

    @classmethod
    def load(cls, path: Path) -> "ConnectionConfig":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: connection file must be a JSON object")
        base_url = data.get("baseUrl")
        company_slug = data.get("companySlug")
        token = data.get("token")
        if not base_url or not str(base_url).strip():
            raise ValueError(f"{path}: missing baseUrl. {CONNECTION_HELP}")
        if not company_slug or not str(company_slug).strip():
            raise ValueError(f"{path}: missing companySlug. {CONNECTION_HELP}")
        if not token or not str(token).strip():
            raise ValueError(f"{path}: missing token. {CONNECTION_HELP}")
        return cls(
            base_url=str(base_url).strip().rstrip("/"),
            company_slug=str(company_slug).strip(),
            token=str(token).strip(),
            path=path,
        )

    def __repr__(self) -> str:
        return (
            "ConnectionConfig("
            f"base_url={self.base_url!r}, company_slug={self.company_slug!r}, "
            f"token='***', path={self.path!r})"
        )

    def config_transfer_url(self, suffix: str) -> str:
        slug = self.company_slug.strip("/")
        rel = f"api/Remote/{slug}/ConfigTransfer/{suffix.lstrip('/')}"
        return urljoin(self.base_url + "/", rel)

    @property
    def download_url(self) -> str:
        return self.config_transfer_url("Download")

    @property
    def backup_url(self) -> str:
        return self.config_transfer_url("Backup")

    def auth_headers(self, *, accept: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": accept}


def filename_from_content_disposition(header: str | None, fallback: str) -> str:
    if not header:
        return fallback
    match = _CONTENT_DISPOSITION_FILENAME.search(header)
    if not match:
        return fallback
    raw = next(g for g in match.groups() if g)
    name = Path(unquote(raw.strip().strip('"'))).name
    if not name or name in {".", ".."}:
        return fallback
    return name


def _raise_http_error(
    url: str,
    response: httpx.Response,
    *,
    allow_sharing_hint: bool = False,
) -> None:
    if response.status_code == 401:
        raise RemoteError(
            f"{url}: 401 Unauthorized. Check the Remote control token "
            "(Company Detail → Remote control). Not a login JWT."
        )
    if response.status_code == 403:
        if allow_sharing_hint:
            raise RemoteError(
                f"{url}: 403 Forbidden. Enable "
                "'Allow sharing remote config transfer' on the company, or the token "
                "cannot download."
            )
        body = (response.text or "")[:500]
        raise RemoteError(f"{url}: 403 Forbidden. {body}")
    if response.status_code == 404:
        raise RemoteError(
            f"{url}: 404 Not Found. Check baseUrl and companySlug."
        )
    if response.status_code >= 400:
        body = (response.text or "")[:500]
        raise RemoteError(f"{url}: HTTP {response.status_code}. {body}")


def download_config_transfer(
    config: ConnectionConfig,
    *,
    dest_dir: Path,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> Path:
    """GET Config Transfer JSON and write it under dest_dir. Returns the file path."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fallback_name = f"Transfer_{config.company_slug}_{stamp}.json"
    headers = config.auth_headers(accept="application/octet-stream")

    own_client = client is None
    http = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        try:
            response = http.get(config.download_url, headers=headers)
        except httpx.HTTPError as exc:
            raise RemoteError(f"{config.download_url}: {exc}") from exc
    finally:
        if own_client:
            http.close()

    _raise_http_error(config.download_url, response, allow_sharing_hint=True)

    filename = filename_from_content_disposition(
        response.headers.get("content-disposition"), fallback_name
    )
    if not filename.lower().endswith(".json"):
        filename = f"{filename}.json"
    out_path = dest_dir / filename
    out_path.write_bytes(response.content)

    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RemoteError(f"{out_path}: downloaded file is not UTF-8 JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise RemoteError(f"{out_path}: expected a JSON object (Config Transfer)")
    transfer_type = payload.get("TransferType")
    if transfer_type and transfer_type != "ConfigTransfer":
        raise RemoteError(
            f"{out_path}: TransferType is {transfer_type!r}, expected 'ConfigTransfer'"
        )
    return out_path


def backup_config_transfer(
    config: ConnectionConfig,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> int:
    """POST Backup. Stores a transfer record on the server. Returns transferId.

    Do not Process this id as a deploy — Process the id from Upload of the edited file.
    """
    headers = config.auth_headers(accept="application/json")
    own_client = client is None
    http = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
    try:
        try:
            response = http.post(config.backup_url, headers=headers)
        except httpx.HTTPError as exc:
            raise RemoteError(f"{config.backup_url}: {exc}") from exc
    finally:
        if own_client:
            http.close()

    _raise_http_error(config.backup_url, response)

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise RemoteError(f"{config.backup_url}: response is not JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise RemoteError(f"{config.backup_url}: expected a JSON object")
    transfer_id = payload.get("transferId", payload.get("TransferId"))
    if transfer_id is None:
        raise RemoteError(f"{config.backup_url}: missing transferId in {payload!r}")
    try:
        return int(transfer_id)
    except (TypeError, ValueError) as exc:
        raise RemoteError(
            f"{config.backup_url}: transferId is not an integer: {transfer_id!r}"
        ) from exc
