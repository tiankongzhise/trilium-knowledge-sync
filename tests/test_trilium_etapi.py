#!/usr/bin/env python3
"""Unit tests for trilium_etapi.py without requiring a live Trilium instance."""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skill" / "trilium-knowledge-sync" / "scripts" / "trilium_etapi.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))

import trilium_etapi as te  # noqa: E402


def http_error(status: int, payload: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example.test", status, "error", {}, io.BytesIO(payload))


def response_context(status: int = 200, body: bytes = b"{}", content_type: str = "application/json"):
    response = mock.Mock()
    response.status = status
    response.headers = {"Content-Type": content_type}
    response.read.return_value = body
    response.__enter__ = mock.Mock(return_value=response)
    response.__exit__ = mock.Mock(return_value=False)
    return response


class NormalizeTests(unittest.TestCase):
    def test_normalize_lf(self):
        self.assertEqual(te.normalize_lf("a\r\nb\rc\n"), "a\nb\nc\n")

    def test_sha256_text(self):
        self.assertEqual(
            te.sha256_text("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_normalize_root_url(self):
        self.assertEqual(te.normalize_etapi_base("http://127.0.0.1:37840/"), "http://127.0.0.1:37840/etapi")

    def test_normalize_healthcheck_url(self):
        self.assertEqual(
            te.normalize_etapi_base("http://127.0.0.1:37840/api/health-check"),
            "http://127.0.0.1:37840/etapi",
        )

    def test_normalize_etapi_url(self):
        self.assertEqual(te.normalize_etapi_base("http://127.0.0.1:37840/etapi/"), "http://127.0.0.1:37840/etapi")

    def test_custom_reverse_proxy_path_is_preserved(self):
        self.assertEqual(
            te.normalize_etapi_base("https://example.test/trilium/etapi"),
            "https://example.test/trilium/etapi",
        )

    def test_invalid_scheme_rejected(self):
        for url in ["", "ftp://127.0.0.1", "127.0.0.1:37840"]:
            with self.subTest(url=url):
                with self.assertRaises(te.EndpointDiscoveryError):
                    te.normalize_etapi_base(url)

    def test_query_and_fragment_rejected(self):
        for url in ["http://127.0.0.1:37840/etapi?token=x", "http://127.0.0.1:37840/etapi#x"]:
            with self.subTest(url=url):
                with self.assertRaises(te.EndpointDiscoveryError):
                    te.normalize_etapi_base(url)

    def test_loopback_detection(self):
        for url in ["http://127.0.0.1:37840/etapi", "http://localhost:37840/etapi", "http://[::1]:37840/etapi"]:
            with self.subTest(url=url):
                self.assertTrue(te.is_loopback_base_url(url))
        self.assertFalse(te.is_loopback_base_url("https://example.com/etapi"))


class EndpointDiscoveryTests(unittest.TestCase):
    def test_non_loopback_healthcheck_requires_explicit_base_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            healthcheck = Path(tmp) / "healthcheck-url"
            healthcheck.write_text("https://example.com/api/health-check", encoding="utf-8")
            with mock.patch.dict(os.environ, {"TRILIUM_ETAPI_URL": ""}), mock.patch.object(
                te, "healthcheck_file_candidates", return_value=[healthcheck]
            ):
                with self.assertRaises(te.EndpointDiscoveryError) as ctx:
                    te.resolve_base_url(None, "secret", 0.1)
        self.assertIn("not loopback", str(ctx.exception))

    def test_loopback_healthcheck_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            healthcheck = Path(tmp) / "healthcheck-url"
            healthcheck.write_text("http://127.0.0.1:37840/api/health-check", encoding="utf-8")
            with mock.patch.dict(os.environ, {"TRILIUM_ETAPI_URL": ""}), mock.patch.object(
                te, "healthcheck_file_candidates", return_value=[healthcheck]
            ):
                self.assertEqual(te.resolve_base_url(None, "secret", 0.1), "http://127.0.0.1:37840/etapi")


class CredentialBlobTests(unittest.TestCase):
    def test_decode_utf16le_blob(self):
        self.assertEqual(te.decode_credential_blob("abc123".encode("utf-16le")), "abc123")

    def test_decode_utf8_blob(self):
        self.assertEqual(te.decode_credential_blob("abc123".encode("utf-8")), "abc123")

    def test_decode_empty_blob_rejected(self):
        with self.assertRaises(te.TokenResolutionError):
            te.decode_credential_blob(b"")


class TokenResolutionTests(unittest.TestCase):
    def test_env_token_reads_named_variable(self):
        with mock.patch.dict(os.environ, {"TEST_TRILIUM_TOKEN": "abc123"}):
            self.assertEqual(te.resolve_token("env:TEST_TRILIUM_TOKEN"), "abc123")

    def test_env_token_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(te.TokenResolutionError):
                te.resolve_token("env:TEST_MISSING_TOKEN")

    def test_file_token_reads_exact_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.txt"
            path.write_text("abc123\n", encoding="utf-8")
            self.assertEqual(te.resolve_token(f"file:{path}"), "abc123")

    def test_stdin_token_source_rejected(self):
        with self.assertRaises(te.TokenResolutionError):
            te.resolve_token("stdin")

    def test_literal_token_rejected(self):
        for source in ["", "abc123", "etapi_abc123", "--token"]:
            with self.subTest(source=source):
                with self.assertRaises(te.TokenResolutionError):
                    te.resolve_token(source)

    def test_whitespace_inside_token_rejected(self):
        with mock.patch.dict(os.environ, {"TEST_TRILIUM_TOKEN": "abc 123"}):
            with self.assertRaises(te.TokenResolutionError):
                te.resolve_token("env:TEST_TRILIUM_TOKEN")

    def test_win_cred_requires_target_name(self):
        with self.assertRaises(te.TokenResolutionError):
            te.resolve_token("win-cred:")

    def test_win_cred_preserves_trailing_space_in_target_name(self):
        with mock.patch.object(te, "read_windows_credential", return_value="abc123") as read_cred:
            self.assertEqual(te.resolve_token("win-cred:My-Trilium-ETAPI "), "abc123")
        read_cred.assert_called_once_with("My-Trilium-ETAPI ")


class ProbeTests(unittest.TestCase):
    def test_probe_does_not_send_token_to_non_trilium_service(self):
        def fake_urlopen(req, timeout=0):
            self.assertNotIn("Authorization", req.headers)
            raise urllib.error.URLError("connection refused")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertFalse(te.probe_base_url("http://127.0.0.1:37840/etapi", "secret", 0.1))

    def test_probe_does_not_send_token_when_app_info_is_unauthenticated_success(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            calls.append(dict(req.headers))
            return response_context(200, b'{"appVersion":"unexpected"}')

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertFalse(te.probe_base_url("http://127.0.0.1:37840/etapi", "secret", 0.1))
        self.assertEqual(len(calls), 1)
        self.assertNotIn("Authorization", calls[0])

    def test_probe_sends_token_only_after_trilium_shape(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            calls.append(dict(req.headers))
            if "Authorization" not in req.headers:
                raise http_error(401, b'{"code":"NOT_AUTHENTICATED","message":"Not authenticated"}')
            return response_context(200, b'{"appVersion":"0.107.0"}')

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertTrue(te.probe_base_url("http://127.0.0.1:37840/etapi", "secret", 0.1))

        self.assertEqual(len(calls), 2)
        self.assertNotIn("Authorization", calls[0])
        self.assertEqual(calls[1].get("Authorization"), "Bearer secret")


class ClientTests(unittest.TestCase):
    def test_json_request_uses_bearer_token(self):
        client = te.TriliumClient("http://127.0.0.1:37840", "secret", timeout=1)
        captured = {}

        def fake_urlopen(req, timeout=0):
            captured["authorization"] = req.headers.get("Authorization")
            captured["content_type"] = req.headers.get("Content-type") or req.headers.get("Content-Type")
            captured["body"] = req.data.decode("utf-8")
            return response_context(200, b'{"ok":true}')

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.request("POST", "/create-note", {"title": "x"})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["authorization"], "Bearer secret")
        self.assertEqual(json.loads(captured["body"]), {"title": "x"})

    def test_http_error_redacts_token(self):
        client = te.TriliumClient("http://127.0.0.1:37840/etapi", "secret", timeout=1)
        error = http_error(401, b'{"message":"bad token secret"}')
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(te.TriliumApiError) as ctx:
                client.request("GET", "/app-info")
        self.assertIn("<redacted>", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))

    def test_find_children_exact_title_and_skips_deleted(self):
        client = te.TriliumClient("http://x/etapi", "token")

        def get_note(note_id):
            values = {
                "parent": {"childNoteIds": ["a", "b", "c"]},
                "a": {"noteId": "a", "title": "report", "isDeleted": True},
                "b": {"noteId": "b", "title": "report"},
                "c": {"noteId": "c", "title": "report "},
            }
            return values[note_id]

        with mock.patch.object(client, "get_note", side_effect=get_note):
            matches = client.find_children("parent", "report")
            self.assertEqual([m["noteId"] for m in matches], ["b"])
            self.assertEqual(client.find_children("parent", "missing"), [])

    def test_find_children_returns_all_duplicates(self):
        client = te.TriliumClient("http://x/etapi", "token")

        def get_note(note_id):
            values = {
                "parent": {"childNoteIds": ["a", "b", "c"]},
                "a": {"noteId": "a", "title": "report"},
                "b": {"noteId": "b", "title": "report"},
                "c": {"noteId": "c", "title": "other"},
            }
            return values[note_id]

        with mock.patch.object(client, "get_note", side_effect=get_note):
            matches = client.find_children("parent", "report")
            self.assertEqual([m["noteId"] for m in matches], ["a", "b"])

    def test_describe_note_includes_identifying_fields(self):
        note = {
            "noteId": "abc",
            "type": "code",
            "mime": "text/x-markdown",
            "utcDateModified": "2026-01-01T00:00:00.000Z",
            "childNoteIds": ["x", "y"],
        }
        description = te.TriliumClient.describe_note(note)
        self.assertIn("noteId=abc", description)
        self.assertIn("utcDateModified=2026-01-01T00:00:00.000Z", description)
        self.assertIn("children=2", description)

    def test_list_children_skips_deleted(self):
        client = te.TriliumClient("http://x/etapi", "token")

        def get_note(note_id):
            values = {
                "parent": {"childNoteIds": ["a", "b"]},
                "a": {"noteId": "a", "title": "deleted", "isDeleted": True, "childNoteIds": []},
                "b": {"noteId": "b", "title": "kept", "type": "text", "mime": "text/html", "childNoteIds": ["x"]},
            }
            return values[note_id]

        with mock.patch.object(client, "get_note", side_effect=get_note):
            children = client.list_children("parent")
        self.assertEqual(children, [{"noteId": "b", "title": "kept", "type": "text", "mime": "text/html", "childCount": 1}])


class UpsertTests(unittest.TestCase):
    def test_upsert_creates_missing_note(self):
        client = te.TriliumClient("http://x/etapi", "token")

        def get_note(note_id):
            if note_id == "p1":
                return {"childNoteIds": ["new1"]}
            return {"noteId": "new1", "type": "code", "mime": "text/x-markdown"}

        with mock.patch.object(client, "find_children", return_value=[]), mock.patch.object(
            client, "create_note", return_value={"noteId": "new1"}
        ) as create, mock.patch.object(
            client, "get_note", side_effect=get_note
        ), mock.patch.object(client, "get_content", return_value="hello"):
            result = client.upsert_note("p1", "title", "code", "text/x-markdown", "hello", 10, True)
        self.assertEqual(result["action"], "created")
        create.assert_called_once_with("p1", "title", "code", "text/x-markdown", "hello", 10, True)

    def test_upsert_unchanged_when_hash_matches(self):
        client = te.TriliumClient("http://x/etapi", "token")
        existing = {"noteId": "n1", "type": "code", "mime": "text/x-markdown"}
        with mock.patch.object(client, "find_children", return_value=[existing]), mock.patch.object(
            client, "get_content", return_value="hello\r\n"
        ), mock.patch.object(client, "put_content") as put:
            result = client.upsert_note("p1", "title", "code", "text/x-markdown", "hello\n")
        self.assertEqual(result["action"], "unchanged")
        put.assert_not_called()

    def test_upsert_updates_changed_content(self):
        client = te.TriliumClient("http://x/etapi", "token")
        existing = {"noteId": "n1", "type": "code", "mime": "text/x-markdown"}
        with mock.patch.object(client, "find_children", return_value=[existing]), mock.patch.object(
            client, "get_content", side_effect=["old", "new"]
        ), mock.patch.object(client, "put_content") as put:
            result = client.upsert_note("p1", "title", "code", "text/x-markdown", "new")
        self.assertEqual(result["action"], "updated")
        put.assert_called_once_with("n1", "new")

    def test_verify_note_content_raises_on_mismatch(self):
        client = te.TriliumClient("http://x/etapi", "token")
        with mock.patch.object(client, "get_content", return_value="different"):
            with self.assertRaises(te.TriliumSyncError):
                client.verify_note_content("n1", "expected")

    def test_verify_parent_contains_raises_when_missing(self):
        client = te.TriliumClient("http://x/etapi", "token")
        with mock.patch.object(client, "get_note", return_value={"childNoteIds": ["other"]}):
            with self.assertRaises(te.TriliumSyncError):
                client.verify_parent_contains("p1", "n1")

    def test_verify_note_metadata_raises_on_type_or_mime_mismatch(self):
        client = te.TriliumClient("http://x/etapi", "token")
        with mock.patch.object(client, "get_note", return_value={"type": "text", "mime": "text/html"}):
            with self.assertRaises(te.TriliumSyncError):
                client.verify_note_metadata("n1", "code", "text/x-markdown")

    def test_upsert_patches_type_and_mime_before_content_check(self):
        client = te.TriliumClient("http://x/etapi", "token")
        existing = {"noteId": "n1", "type": "text", "mime": "text/html"}
        with mock.patch.object(client, "find_children", return_value=[existing]), mock.patch.object(
            client, "patch_note"
        ) as patch, mock.patch.object(
            client, "get_note", return_value={"noteId": "n1", "type": "code", "mime": "text/x-markdown"}
        ), mock.patch.object(client, "get_content", return_value="new"), mock.patch.object(
            client, "put_content"
        ) as put:
            result = client.upsert_note("p1", "title", "code", "text/x-markdown", "new")
        patch.assert_called_once_with("n1", type="code", mime="text/x-markdown")
        put.assert_not_called()
        self.assertEqual(result["action"], "updated")

    def test_upsert_refuses_duplicate_titles_and_lists_candidates(self):
        client = te.TriliumClient("http://x/etapi", "token")
        duplicates = [
            {"noteId": "n1", "type": "code", "mime": "text/x-markdown", "utcDateModified": "2026-01-01T00:00:00Z"},
            {"noteId": "n2", "type": "text", "mime": "text/html", "utcDateModified": "2026-02-02T00:00:00Z"},
        ]
        with mock.patch.object(client, "find_children", return_value=duplicates), mock.patch.object(
            client, "create_note"
        ) as create, mock.patch.object(client, "put_content") as put:
            with self.assertRaises(te.TriliumSyncError) as ctx:
                client.upsert_note("p1", "title", "code", "text/x-markdown", "hello")
        message = str(ctx.exception)
        self.assertIn("noteId=n1", message)
        self.assertIn("noteId=n2", message)
        self.assertIn("Not choosing one silently", message)
        self.assertIn("patch-note/put-content", message)
        create.assert_not_called()
        put.assert_not_called()


class CliTests(unittest.TestCase):
    def test_no_literal_token_argument(self):
        stderr = io.StringIO()
        parser = te.build_parser()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--token=abc", "app-info"])
        self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_stdin_token_source_rejected_at_cli_level(self):
        args = te.build_parser().parse_args(
            [
                "--token-source",
                "stdin",
                "--base-url",
                "http://127.0.0.1:37840/etapi",
                "upsert-note",
                "--parent-id",
                "p",
                "--title",
                "t",
                "--type",
                "code",
                "--content-file",
                "-",
            ]
        )
        with self.assertRaises(te.TokenResolutionError):
            te.run(args)


if __name__ == "__main__":
    unittest.main()
