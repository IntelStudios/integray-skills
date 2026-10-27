#!/usr/bin/env python3
"""Print a Debugger/Run call as curl or as an HTTP file.

Does not call the API. The body is the JSON object for
POST /api/Remote/{companySlug}/Debugger/Run. Read it from --body or stdin.

Formats:
  curl   shell command. Authorization uses $REMOTE_CONTROL_TOKEN.
  http   REST Client file (.http). JetBrains HTTP Client and the VS Code
         REST Client both read this: @name = value, {{name}}, and ###
         between requests.

The remote control token is not written unless --include-token is set.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from integray_remote import ConnectionConfig  # noqa: E402


def load_body(path: Path | None) -> dict[str, Any]:
    raw = sys.stdin.read() if path is None else path.read_text(encoding="utf-8")
    if not raw.strip():
        raise SystemExit("request body is empty")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"request body is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("request body must be a JSON object")
    return data


def resolve_target(args: argparse.Namespace) -> tuple[str, str, str]:
    """Return base URL, company slug, and token (token empty unless requested)."""
    base = (args.base_url or "").strip().rstrip("/")
    company = (args.company or "").strip()
    token = ""
    if args.connection is not None:
        config = ConnectionConfig.load(args.connection)
        base = base or config.base_url.rstrip("/")
        company = company or config.company_slug
        if args.include_token:
            token = config.token
    if not base or not company:
        raise SystemExit("pass --connection, or both --base-url and --company")
    return base, company, token


def title_for(body: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        return explicit
    guid = body.get("connectorGuid") or "Debugger/Run"
    version = body.get("connectorVersion") or ""
    action = body.get("actionCode") or ""
    bits = [str(guid)]
    if version:
        bits.append(str(version))
    if action:
        bits.append(str(action))
    return " ".join(bits)


def render_curl(base: str, company: str, body: dict[str, Any], token: str) -> str:
    url = f"{base}/api/Remote/{company}/Debugger/Run"
    if token:
        auth = shlex.quote(f"Authorization: Bearer {token}")
    else:
        auth = '"Authorization: Bearer $REMOTE_CONTROL_TOKEN"'
    payload = json.dumps(body, indent=2, ensure_ascii=False)
    return (
        f"curl -sS -X POST {shlex.quote(url)} \\\n"
        f"  -H {auth} \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -H 'Accept: application/json' \\\n"
        f"  -d @- <<'EOF'\n"
        f"{payload}\n"
        f"EOF\n"
    )


def render_http(base: str, company: str, body: dict[str, Any], token: str, title: str) -> str:
    payload = json.dumps(body, indent=2, ensure_ascii=False)
    return (
        f"@host = {base}\n"
        f"@company = {company}\n"
        f"@token = {token}\n"
        f"\n"
        f"### {title}\n"
        f"POST {{{{host}}}}/api/Remote/{{{{company}}}}/Debugger/Run\n"
        f"Authorization: Bearer {{{{token}}}}\n"
        f"Content-Type: application/json\n"
        f"\n"
        f"{payload}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body",
        type=Path,
        help="Debugger/Run JSON object. Omit to read stdin.",
    )
    parser.add_argument(
        "--connection",
        type=Path,
        help="projects/<name>/.integray-connection.json (baseUrl, companySlug, token)",
    )
    parser.add_argument("--base-url", help="Overrides baseUrl from --connection")
    parser.add_argument("--company", help="Overrides companySlug from --connection")
    parser.add_argument(
        "--format",
        choices=("curl", "http"),
        default="curl",
        help="curl (default) or http (REST Client .http file)",
    )
    parser.add_argument("--title", help="### heading when --format http")
    parser.add_argument(
        "--include-token",
        action="store_true",
        help="Write the remote control token from --connection into the output",
    )
    args = parser.parse_args()
    if args.include_token and args.connection is None:
        raise SystemExit("--include-token needs --connection")

    body = load_body(args.body)
    base, company, token = resolve_target(args)
    if args.format == "curl":
        sys.stdout.write(render_curl(base, company, body, token))
    else:
        sys.stdout.write(render_http(base, company, body, token, title_for(body, args.title)))


if __name__ == "__main__":
    main()
