"""Isolated, local read-only Search Console export. No application imports."""

import argparse
import json
import logging
import os
import stat
import sys
import tempfile
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from zoneinfo import ZoneInfo

import google.auth.transport.requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

REPO = Path(__file__).resolve().parents[1]
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
TOKEN_URI = "https://oauth2.googleapis.com/token"
HTTP_TIMEOUT = 30
STORAGE_ERROR = "Unsafe private storage location or permissions."
PROPERTY = "sc-domain:regalame.app"
QUERY_URL = "https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Aregalame.app/searchAnalytics/query"
LIMITATIONS = (
    "Top rows only, not guaranteed exhaustive; anonymized queries omitted for privacy; "
    "recent final days may be absent due to reporting latency. Pagination does not remove these limits."
)


class SafeError(Exception):
    """A fixed, non-secret message suitable for terminal output."""


def reporting_window(now=None):
    today = (now or datetime.now(ZoneInfo("America/Los_Angeles"))).astimezone(
        ZoneInfo("America/Los_Angeles")
    ).date()
    end = today - timedelta(days=1)
    return (end - timedelta(days=89)).isoformat(), end.isoformat()


def private_path(path):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or path.is_relative_to(REPO):
        raise SafeError(STORAGE_ERROR)
    for component in reversed((path, *path.parents)):
        if component.is_symlink():
            raise SafeError(STORAGE_ERROR)
        if component.exists() and component.is_dir():
            info = component.stat()
            if info.st_mode & 0o022 and not (info.st_mode & stat.S_ISVTX and info.st_uid == 0):
                raise SafeError(STORAGE_ERROR)
    if not path.parent.exists():
        path.parent.mkdir(mode=0o700)
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise SafeError(STORAGE_ERROR)
    if path.exists():
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise SafeError(STORAGE_ERROR)
    return path


def write_private(path, data):
    path = private_path(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".search-console-")
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        private_path(path)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_private(path):
    path = private_path(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "r") as stream:
        return json.load(stream)


def load_credentials(client, token, reauthorize=False):
    client, token = private_path(client), private_path(token)
    if client == token:
        raise SafeError(STORAGE_ERROR)
    try:
        config = read_private(client)
        installed = config["installed"]
        if "web" in config or installed["token_uri"] != TOKEN_URI or installed["auth_uri"] not in (
            "https://accounts.google.com/o/oauth2/auth",
            "https://accounts.google.com/o/oauth2/v2/auth",
        ):
            raise ValueError()
    except Exception:
        raise SafeError("Use the selected official Google desktop client in private storage.") from None
    # This is a single-purpose CLI. Suppress library debug/callback logs, including URLs.
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if token.exists() and not reauthorize:
            try:
                data = read_private(token)
                if (
                    data.get("scopes") != [SCOPE]
                    or data.get("client_id") != installed["client_id"]
                    or data.get("token_uri") != TOKEN_URI
                ):
                    raise ValueError()
                credentials = Credentials.from_authorized_user_info(data, scopes=[SCOPE])
                if not credentials.valid:
                    if not credentials.refresh_token:
                        raise ValueError()
                    request = Request()
                    request.session.trust_env = False
                    try:
                        credentials.refresh(partial(request, timeout=HTTP_TIMEOUT, allow_redirects=False))
                    finally:
                        request.session.close()
            except Exception:
                raise SafeError("Session unusable; rerun with --reauthorize for browser consent.") from None
        else:
            try:
                flow = InstalledAppFlow.from_client_config(
                    config, scopes=[SCOPE], autogenerate_code_verifier=True
                )
                flow.oauth2session.trust_env = False
                original_request = flow.oauth2session.request

                def bounded_request(*args, **kwargs):
                    # fetch_token passes timeout=None, overriding partial defaults.
                    kwargs.update(timeout=HTTP_TIMEOUT, allow_redirects=False)
                    return original_request(*args, **kwargs)

                flow.oauth2session.request = bounded_request
                credentials = flow.run_local_server(
                    host="127.0.0.1", bind_addr="127.0.0.1", port=0, timeout_seconds=180,
                    authorization_prompt_message="", open_browser=True,
                    access_type="offline", prompt="consent",
                )
            except Exception:
                raise SafeError("OAuth authorization failed; rerun with --reauthorize when ready.") from None
        if (
            set(credentials.scopes or []) != {SCOPE}
            or (
                credentials.granted_scopes is not None
                and set(credentials.granted_scopes) != {SCOPE}
            )
        ):
            raise SafeError("Unexpected session scope; rerun with --reauthorize.")
        write_private(token, json.loads(credentials.to_json()))
        return credentials
    finally:
        logging.disable(previous_logging)


def query_export(session, now=None, row_limit=25000):
    start, end = reporting_window(now)
    settings = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query", "page"],
        "type": "web",
        "dataState": "final",
    }
    rows = []
    while True:
        try:
            response = session.post(
                QUERY_URL, json={**settings, "rowLimit": row_limit, "startRow": len(rows)},
                timeout=HTTP_TIMEOUT, allow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError()
            page = response.json().get("rows", [])
            if not isinstance(page, list):
                raise ValueError()
        except Exception:
            raise SafeError("Search Console request failed; check property access and session authorization.") from None
        rows.extend(page)
        if len(page) < row_limit:
            break
    return {
        "property": PROPERTY,
        **settings,
        "timezone": "America/Los_Angeles",
        "limitations": LIMITATIONS,
        "rows": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private local read-only Search Console export.")
    parser.add_argument("--client-secret", required=True, type=Path, metavar="PRIVATE_CLIENT_JSON")
    parser.add_argument("--token", required=True, type=Path, metavar="PRIVATE_TOKEN_JSON")
    parser.add_argument("--output", required=True, type=Path, metavar="PRIVATE_EXPORT_JSON")
    parser.add_argument("--property", default=PROPERTY, help="Only sc-domain:regalame.app is permitted.")
    parser.add_argument("--reauthorize", action="store_true", help="Replace the local session after browser consent.")
    args = parser.parse_args(argv)
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if args.property != PROPERTY:
            raise SafeError("Only sc-domain:regalame.app is permitted.")
        paths = [private_path(path) for path in (args.client_secret, args.token, args.output)]
        if len(set(paths)) != 3:
            raise SafeError(STORAGE_ERROR)
        credentials = load_credentials(args.client_secret, args.token, args.reauthorize)
        refresh_request = Request()
        refresh_request.session.trust_env = False
        try:
            session = google.auth.transport.requests.AuthorizedSession(
                credentials, refresh_timeout=HTTP_TIMEOUT, max_refresh_attempts=0,
                auth_request=partial(refresh_request, allow_redirects=False),
            )
            session.trust_env = False
            try:
                export = query_export(session)
                write_private(args.token, json.loads(credentials.to_json()))
                write_private(args.output, export)
            finally:
                session.close()
        finally:
            refresh_request.session.close()
        print("Private export saved.")
        return 0
    except SafeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print("Local export failed; check private paths and authorization.", file=sys.stderr)
        return 1
    finally:
        logging.disable(previous_logging)


if __name__ == "__main__":
    raise SystemExit(main())
