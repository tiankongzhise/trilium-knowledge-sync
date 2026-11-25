#!/usr/bin/env python3
"""Small Trilium ETAPI client used by the trilium-knowledge-sync skill.

The CLI intentionally accepts only token *locations* (file/env/Windows Credential
Manager/stdin), never literal token values. It uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

VERSION = "0.1.0"
DEFAULT_PORTS = (37840, 37740, 8080)


class TriliumSyncError(Exception):
    """Base exception for expected operational errors."""


class TokenResolutionError(TriliumSyncError):
    """Raised when a token location cannot be resolved."""


class EndpointDiscoveryError(TriliumSyncError):
    """Raised when no ETAPI endpoint can be found."""


class TriliumConnectionError(TriliumSyncError):
    """Raised when the ETAPI endpoint cannot be reached."""


class TriliumApiError(TriliumSyncError):
    def __init__(self, status: int, method: str, path: str, detail: str):
        super().__init__(f"HTTP {status} during {method} {path}: {detail}")
        self.status = status
        self.method = method
        self.path = path
        self.detail = detail


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_lf(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def normalize_etapi_base(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        raise EndpointDiscoveryError("Empty ETAPI base URL")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise EndpointDiscoveryError(f"Invalid ETAPI base URL (expected http/https): {url}")
    if parsed.query or parsed.fragment:
        raise EndpointDiscoveryError("ETAPI base URL must not include a query string or fragment")
    path = parsed.path.rstrip("/")
    if path == "/api/health-check":
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/etapi", "", "", ""))
    if path in ("", "/"):
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/etapi", "", "", ""))
    if path == "/etapi":
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/etapi", "", "", ""))
    # A reverse proxy may expose ETAPI under a custom path; preserve it.
    return url


def read_text_file(path_or_dash: str) -> str:
    if path_or_dash == "-":
        return sys.stdin.read()
    path = Path(os.path.expandvars(os.path.expanduser(path_or_dash)))
    with path.open("r", encoding="utf-8-sig", newline=None) as f:
        return f.read()


def decode_credential_blob(raw: bytes) -> str:
    if not raw:
        raise TokenResolutionError("Windows credential blob is empty")

    def decode_with(encoding: str) -> Optional[str]:
        try:
            value = raw.decode(encoding).rstrip("\x00").strip()
        except UnicodeDecodeError:
            return None
        return value or None

    looks_utf16le = len(raw) % 2 == 0 and len(raw) >= 4
    if looks_utf16le:
        high_zeroes = sum(1 for i in range(1, len(raw), 2) if raw[i] == 0)
        looks_utf16le = high_zeroes / (len(raw) / 2) > 0.5

    encodings = ("utf-16le", "utf-8") if looks_utf16le else ("utf-8", "utf-16le")
    for encoding in encodings:
        value = decode_with(encoding)
        if value:
            return value
    raise TokenResolutionError("Windows credential exists but could not be decoded as UTF-16LE or UTF-8")


def read_windows_credential(target_name: str) -> str:
    if os.name != "nt":
        raise TokenResolutionError("win-cred token source is only available on Windows")

    import ctypes.wintypes as wt

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    class CREDENTIAL(ctypes.Structure):
        pass

    PCREDENTIAL = ctypes.POINTER(CREDENTIAL)
    CREDENTIAL._fields_ = [
        ("Flags", wt.DWORD),
        ("Type", wt.DWORD),
        ("TargetName", wt.LPCWSTR),
        ("Comment", wt.LPCWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wt.DWORD),
        ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPCWSTR),
        ("UserName", wt.LPCWSTR),
    ]
    advapi32.CredReadW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.POINTER(PCREDENTIAL)]
    advapi32.CredReadW.restype = wt.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]

    CRED_TYPE_GENERIC = 1
    pcred = PCREDENTIAL()
    if not advapi32.CredReadW(target_name, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
        err = ctypes.get_last_error()
        raise TokenResolutionError(
            f"Windows Credential Manager target not readable (Win32 error {err}). "
            "Check the exact target name, including spaces."
        )
    try:
        raw = ctypes.string_at(pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize)
    finally:
        advapi32.CredFree(pcred)

    return decode_credential_blob(raw)


def resolve_token(source: str) -> str:
    """Resolve a token location. Literal token values are deliberately unsupported."""
    if not source or not source.strip():
        raise TokenResolutionError("Missing token source")

    if source == "stdin":
        token = sys.stdin.read().strip()
    elif source.startswith("env:"):
        name = source[4:].strip()
        if not name:
            raise TokenResolutionError("env token source requires a variable name")
        token = os.environ.get(name, "").strip()
        if not token:
            raise TokenResolutionError(f"Environment variable is empty or missing: {name}")
    elif source.startswith("file:"):
        path = source[5:]
        if not path:
            raise TokenResolutionError("file token source requires a path")
        try:
            token = read_text_file(path).strip()
        except OSError as exc:
            raise TokenResolutionError(f"Cannot read token file: {exc}") from exc
    elif source.startswith("win-cred:"):
        target = source[len("win-cred:"):]
        if not target:
            raise TokenResolutionError("win-cred token source requires an exact target name")
        token = read_windows_credential(target).strip()
    else:
        raise TokenResolutionError(
            "Unsupported token source. Use win-cred:<target>, file:<path>, env:<name>, or stdin. "
            "Literal token values are not accepted."
        )

    if not token:
        raise TokenResolutionError("Resolved token is empty")
    if any(ch.isspace() for ch in token):
        raise TokenResolutionError("Resolved token contains whitespace; check the token source")
    return token


def healthcheck_file_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_file = os.environ.get("TRILIUM_HEALTHCHECK_URL_FILE")
    if env_file:
        candidates.append(Path(os.path.expandvars(os.path.expanduser(env_file))))
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "trilium-data" / "healthcheck-url")
    home = Path.home()
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        candidates.append(Path(xdg_data) / "trilium-data" / "healthcheck-url")
    candidates.extend(
        [
            home / ".local" / "share" / "trilium-data" / "healthcheck-url",
            home / ".config" / "trilium-data" / "healthcheck-url",
            home / "Library" / "Application Support" / "trilium-data" / "healthcheck-url",
        ]
    )
    # Preserve order while removing duplicates.
    result: list[Path] = []
    seen = set()
    for item in candidates:
        key = str(item).lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def is_loopback_base_url(base_url: str) -> bool:
    hostname = urllib.parse.urlparse(base_url).hostname
    if not hostname:
        return False
    hostname = hostname.lower().strip("[]")
    return hostname == "localhost" or hostname == "::1" or hostname.startswith("127.")


def probe_base_url(base_url: str, token: str, timeout: float) -> bool:
    """Probe a candidate ETAPI endpoint without sending the token to arbitrary services.

    Trilium's unauthenticated /etapi/app-info response is a JSON 401 with
    code NOT_AUTHENTICATED. Only after seeing that shape do we send the token.
    """
    url = normalize_etapi_base(base_url) + "/app-info"
    unauth_req = urllib.request.Request(url, headers={"Accept": "application/json"})
    looks_like_trilium = False
    try:
        with urllib.request.urlopen(unauth_req, timeout=timeout):
            looks_like_trilium = False
    except urllib.error.HTTPError as exc:
        try:
            if exc.code in (401, 403):
                try:
                    payload = json.loads(exc.read().decode("utf-8", "replace"))
                    looks_like_trilium = payload.get("code") == "NOT_AUTHENTICATED" or "Not authenticated" in payload.get("message", "")
                except Exception:
                    looks_like_trilium = False
        finally:
            exc.close()
    except Exception:
        return False

    if not looks_like_trilium:
        return False

    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def resolve_base_url(explicit: Optional[str], token: str, timeout: float) -> str:
    if explicit:
        return normalize_etapi_base(explicit)
    env_url = os.environ.get("TRILIUM_ETAPI_URL")
    if env_url:
        return normalize_etapi_base(env_url)

    for candidate in healthcheck_file_candidates():
        try:
            if not candidate.is_file():
                continue
            health_url = candidate.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
        if not health_url:
            continue
        try:
            discovered = normalize_etapi_base(health_url)
        except EndpointDiscoveryError:
            continue
        if not is_loopback_base_url(discovered):
            raise EndpointDiscoveryError(
                "Discovered Trilium healthcheck endpoint is not loopback. "
                "Pass --base-url explicitly if this remote endpoint is intentional."
            )
        return discovered

    for port in DEFAULT_PORTS:
        candidate = f"http://127.0.0.1:{port}/etapi"
        if probe_base_url(candidate, token, min(timeout, 2.0)):
            return candidate

    raise EndpointDiscoveryError(
        "Could not discover a reachable Trilium ETAPI endpoint. Start Trilium Notes or pass --base-url "
        "explicitly, for example --base-url http://127.0.0.1:37840/etapi"
    )


class TriliumClient:
    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        self.base_url = normalize_etapi_base(base_url)
        self.token = token
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        content_type: Optional[str] = None,
        query: Optional[dict[str, Any]] = None,
        expect: str = "json",
    ) -> Any:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        if query:
            clean_query = {k: v for k, v in query.items() if v is not None}
            if clean_query:
                url += "?" + urllib.parse.urlencode(clean_query)

        data = None
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json" if expect == "json" else "text/plain"}
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                headers["Content-Type"] = "application/json; charset=utf-8"
            elif isinstance(body, str):
                data = body.encode("utf-8")
                headers["Content-Type"] = content_type or "text/plain; charset=utf-8"
            else:
                data = body
                headers["Content-Type"] = content_type or "application/octet-stream"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if resp.status == 204 or not raw:
                    return None
                text = raw.decode("utf-8", "replace")
                if expect == "json":
                    return json.loads(text)
                return text
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:1200]
                detail = detail.replace(self.token, "<redacted>")
            finally:
                exc.close()
            raise TriliumApiError(exc.code, method, path, detail) from exc
        except urllib.error.URLError as exc:
            raise TriliumConnectionError(f"Cannot reach Trilium ETAPI at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TriliumConnectionError(f"Timed out reaching Trilium ETAPI at {self.base_url}") from exc

    @staticmethod
    def note_path(note_id: str) -> str:
        return "/notes/" + urllib.parse.quote(note_id, safe="")

    def app_info(self) -> dict[str, Any]:
        return self.request("GET", "/app-info")

    def get_note(self, note_id: str) -> dict[str, Any]:
        return self.request("GET", self.note_path(note_id))

    def get_content(self, note_id: str) -> str:
        return self.request("GET", self.note_path(note_id) + "/content", expect="text")

    def put_content(self, note_id: str, content: str) -> None:
        self.request("PUT", self.note_path(note_id) + "/content", content, "text/plain; charset=utf-8")

    def create_note(
        self,
        parent_id: str,
        title: str,
        note_type: str,
        mime: Optional[str],
        content: str = "",
        position: Optional[int] = None,
        expanded: Optional[bool] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parentNoteId": parent_id,
            "title": title,
            "type": note_type,
            "content": content,
        }
        if mime:
            payload["mime"] = mime
        if position is not None:
            payload["notePosition"] = position
        if expanded is not None:
            payload["isExpanded"] = expanded
        result = self.request("POST", "/create-note", payload)
        note = result.get("note") if isinstance(result, dict) else None
        if not note or "noteId" not in note:
            raise TriliumSyncError("Unexpected create-note response shape")
        return note

    def patch_note(self, note_id: str, **fields: Any) -> dict[str, Any]:
        payload = {k: v for k, v in fields.items() if v is not None}
        if not payload:
            raise TriliumSyncError("patch-note requires at least one field")
        return self.request("PATCH", self.note_path(note_id), payload)

    def find_child(self, parent_id: str, title: str) -> Optional[dict[str, Any]]:
        parent = self.get_note(parent_id)
        for child_id in parent.get("childNoteIds", []):
            child = self.get_note(child_id)
            if child.get("title") == title and not child.get("isDeleted"):
                return child
        return None

    def list_children(self, parent_id: str) -> list[dict[str, Any]]:
        parent = self.get_note(parent_id)
        children = []
        for child_id in parent.get("childNoteIds", []):
            child = self.get_note(child_id)
            if child.get("isDeleted"):
                continue
            children.append(
                {
                    "noteId": child.get("noteId"),
                    "title": child.get("title"),
                    "type": child.get("type"),
                    "mime": child.get("mime"),
                    "childCount": len(child.get("childNoteIds", [])),
                }
            )
        return children

    def search(self, query: str, limit: int = 10, fast: bool = False) -> dict[str, Any]:
        return self.request(
            "GET",
            "/notes",
            query={"search": query, "limit": limit, "fastSearch": "true" if fast else "false"},
        )

    def verify_note_content(self, note_id: str, content: str) -> None:
        actual = self.get_content(note_id)
        if sha256_text(normalize_lf(actual)) != sha256_text(normalize_lf(content)):
            raise TriliumSyncError(f"Post-write content verification failed for note {note_id}")

    def verify_parent_contains(self, parent_id: str, note_id: str) -> None:
        parent = self.get_note(parent_id)
        if note_id not in parent.get("childNoteIds", []):
            raise TriliumSyncError(f"Post-write parent verification failed: {parent_id} does not contain {note_id}")

    def verify_note_metadata(self, note_id: str, note_type: str, mime: Optional[str]) -> None:
        note = self.get_note(note_id)
        if note.get("type") != note_type:
            raise TriliumSyncError(f"Post-write type verification failed for note {note_id}")
        if mime and note.get("mime") != mime:
            raise TriliumSyncError(f"Post-write MIME verification failed for note {note_id}")

    def upsert_note(
        self,
        parent_id: str,
        title: str,
        note_type: str,
        mime: Optional[str],
        content: str,
        position: Optional[int] = None,
        expanded: Optional[bool] = None,
    ) -> dict[str, Any]:
        existing = self.find_child(parent_id, title)
        desired_hash = sha256_text(normalize_lf(content))
        if existing:
            note_id = existing["noteId"]
            patch_fields: dict[str, Any] = {}
            if existing.get("type") != note_type:
                patch_fields["type"] = note_type
            if mime and existing.get("mime") != mime:
                patch_fields["mime"] = mime
            metadata_changed = bool(patch_fields)
            if patch_fields:
                self.patch_note(note_id, **patch_fields)
                self.verify_note_metadata(note_id, note_type, mime)
            current = self.get_content(note_id)
            current_hash = sha256_text(normalize_lf(current))
            if current_hash != desired_hash:
                self.put_content(note_id, content)
                self.verify_note_content(note_id, content)
                action = "updated"
            else:
                action = "updated" if metadata_changed else "unchanged"
        else:
            note = self.create_note(parent_id, title, note_type, mime, content, position, expanded)
            note_id = note["noteId"]
            self.verify_parent_contains(parent_id, note_id)
            self.verify_note_metadata(note_id, note_type, mime)
            self.verify_note_content(note_id, content)
            action = "created"

        return {
            "action": action,
            "noteId": note_id,
            "parentNoteId": parent_id,
            "title": title,
            "type": note_type,
            "mime": mime,
            "contentSha256": desired_hash,
            "verified": True,
        }


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trilium ETAPI helper for the trilium-knowledge-sync skill. Token values are never accepted directly.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--token-source",
        help="Token location: win-cred:<target>, file:<path>, env:<name>, or stdin. May also use TRILIUM_TOKEN_SOURCE.",
    )
    parser.add_argument("--base-url", help="ETAPI base URL, for example http://127.0.0.1:37840/etapi")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds (default: 15)")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks for unexpected errors")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("app-info", help="Verify token and print Trilium application info")

    p = sub.add_parser("get-note", help="Get note metadata")
    p.add_argument("note_id")

    p = sub.add_parser("get-content", help="Get note content as UTF-8 text")
    p.add_argument("note_id")
    p.add_argument("--output", help="Write content to this file instead of stdout")

    p = sub.add_parser("list-children", help="List direct children of a note")
    p.add_argument("parent_id")

    p = sub.add_parser("find-child", help="Find one direct child by exact title")
    p.add_argument("parent_id")
    p.add_argument("title")

    p = sub.add_parser("search", help="Search notes")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--fast", action="store_true")

    p = sub.add_parser("create-note", help="Create a note")
    p.add_argument("--parent-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--type", required=True, dest="note_type")
    p.add_argument("--mime")
    p.add_argument("--content-file", help="UTF-8 text file, or '-' for stdin; omitted means empty content")
    p.add_argument("--position", type=int)
    p.add_argument("--expanded", action="store_true")

    p = sub.add_parser("patch-note", help="Patch note metadata")
    p.add_argument("note_id")
    p.add_argument("--title")
    p.add_argument("--type", dest="note_type")
    p.add_argument("--mime")

    p = sub.add_parser("put-content", help="Replace text content of a note")
    p.add_argument("note_id")
    p.add_argument("--content-file", required=True, help="UTF-8 text file, or '-' for stdin")

    p = sub.add_parser("upsert-note", help="Create or update a direct child note by exact title")
    p.add_argument("--parent-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--type", required=True, dest="note_type")
    p.add_argument("--mime")
    p.add_argument("--content-file", required=True, help="UTF-8 text file, or '-' for stdin")
    p.add_argument("--position", type=int)
    p.add_argument("--expanded", action="store_true")
    return parser


def run(args: argparse.Namespace) -> Any:
    token_source = args.token_source or os.environ.get("TRILIUM_TOKEN_SOURCE", "")
    if not token_source:
        raise TokenResolutionError(
            "Missing token source. Pass --token-source or set TRILIUM_TOKEN_SOURCE. "
            "The value must be a location, not the token itself."
        )
    if token_source == "stdin":
        for content_file in [getattr(args, "content_file", None)]:
            if content_file == "-":
                raise TokenResolutionError("stdin cannot supply both the token and note content")

    token = resolve_token(token_source)
    base_url = resolve_base_url(args.base_url, token, args.timeout)
    client = TriliumClient(base_url, token, args.timeout)

    if args.command == "app-info":
        return client.app_info()
    if args.command == "get-note":
        return client.get_note(args.note_id)
    if args.command == "get-content":
        content = client.get_content(args.note_id)
        if args.output:
            output = Path(os.path.expandvars(os.path.expanduser(args.output)))
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", encoding="utf-8", newline="") as f:
                f.write(content)
            return {"noteId": args.note_id, "output": str(output), "contentSha256": sha256_text(normalize_lf(content))}
        sys.stdout.write(content)
        return None
    if args.command == "list-children":
        return client.list_children(args.parent_id)
    if args.command == "find-child":
        return client.find_child(args.parent_id, args.title)
    if args.command == "search":
        return client.search(args.query, args.limit, args.fast)
    if args.command == "create-note":
        content = read_text_file(args.content_file) if args.content_file else ""
        return client.create_note(
            args.parent_id,
            args.title,
            args.note_type,
            args.mime,
            content,
            args.position,
            True if args.expanded else None,
        )
    if args.command == "patch-note":
        return client.patch_note(args.note_id, title=args.title, type=args.note_type, mime=args.mime)
    if args.command == "put-content":
        content = read_text_file(args.content_file)
        client.put_content(args.note_id, content)
        client.verify_note_content(args.note_id, content)
        return {"noteId": args.note_id, "contentSha256": sha256_text(normalize_lf(content)), "updated": True, "verified": True}
    if args.command == "upsert-note":
        content = read_text_file(args.content_file)
        return client.upsert_note(
            args.parent_id,
            args.title,
            args.note_type,
            args.mime,
            content,
            args.position,
            True if args.expanded else None,
        )
    raise TriliumSyncError(f"Unknown command: {args.command}")


def main(argv: Optional[list[str]] = None) -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
        if result is not None:
            print_json(result)
        return 0
    except TriliumSyncError as exc:
        if args.debug:
            raise
        print(f"ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # defensive boundary: never expose token values in output
        if args.debug:
            raise
        print(f"ERROR {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
