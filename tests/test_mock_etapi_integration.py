#!/usr/bin/env python3
"""End-to-end CLI tests against a small in-process mock ETAPI server."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skill" / "trilium-knowledge-sync" / "scripts" / "trilium_etapi.py"
TOKEN = "mock-etapi-token"


class MockTriliumState:
    def __init__(self):
        self.lock = threading.Lock()
        self.counter = 0
        self.notes = {
            "root": {
                "noteId": "root",
                "title": "root",
                "type": "text",
                "mime": "text/html",
                "childNoteIds": [],
                "isDeleted": False,
            }
        }
        self.contents = {"root": ""}

    def create_note(self, payload):
        with self.lock:
            self.counter += 1
            note_id = f"n{self.counter}"
            parent = payload["parentNoteId"]
            note = {
                "noteId": note_id,
                "title": payload["title"],
                "type": payload["type"],
                "mime": payload.get("mime"),
                "childNoteIds": [],
                "parentNoteIds": [parent],
                "isDeleted": False,
            }
            self.notes[note_id] = note
            self.contents[note_id] = payload.get("content", "")
            self.notes[parent]["childNoteIds"].append(note_id)
            return note


STATE = MockTriliumState()


class MockEtapiHandler(BaseHTTPRequestHandler):
    server_version = "MockTrilium/0.1"

    def log_message(self, fmt, *args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, text):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if self.headers.get("Authorization") != "Bearer " + TOKEN:
            self.send_json(401, {"status": 401, "code": "NOT_AUTHENTICATED", "message": "Not authenticated"})
            return False
        return True

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def read_text_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length).decode("utf-8")

    def parsed(self):
        return urllib.parse.urlparse(self.path)

    def note_id_from_path(self, suffix=""):
        path = self.parsed().path
        prefix = "/etapi/notes/"
        if not path.startswith(prefix):
            return None
        rest = path[len(prefix) :]
        if suffix and rest.endswith(suffix):
            rest = rest[: -len(suffix)]
        return urllib.parse.unquote(rest)

    def do_GET(self):
        path = self.parsed().path
        if path == "/etapi/app-info":
            if not self.authorized():
                return
            self.send_json(200, {"appVersion": "mock", "dbVersion": 242})
            return
        if not self.authorized():
            return
        if path.startswith("/etapi/notes/") and path.endswith("/content"):
            note_id = self.note_id_from_path("/content")
            if note_id not in STATE.notes:
                self.send_json(404, {"message": "note not found"})
                return
            self.send_text(200, STATE.contents[note_id])
            return
        if path.startswith("/etapi/notes/"):
            note_id = self.note_id_from_path()
            note = STATE.notes.get(note_id)
            if not note:
                self.send_json(404, {"message": "note not found"})
                return
            self.send_json(200, note)
            return
        if path == "/etapi/notes":
            query = urllib.parse.parse_qs(self.parsed().query).get("search", [""])[0]
            results = [n for n in STATE.notes.values() if query.lower() in n.get("title", "").lower()]
            self.send_json(200, {"results": results})
            return
        self.send_json(404, {"message": "unknown path"})

    def do_POST(self):
        if not self.authorized():
            return
        if self.parsed().path == "/etapi/create-note":
            payload = self.read_json()
            parent = payload.get("parentNoteId")
            if parent not in STATE.notes:
                self.send_json(404, {"message": "parent not found"})
                return
            note = STATE.create_note(payload)
            self.send_json(201, {"note": note, "branch": {"branchId": "b" + note["noteId"], "noteId": note["noteId"], "parentNoteId": parent}})
            return
        self.send_json(404, {"message": "unknown path"})

    def do_PUT(self):
        if not self.authorized():
            return
        if self.parsed().path.startswith("/etapi/notes/") and self.parsed().path.endswith("/content"):
            note_id = self.note_id_from_path("/content")
            if note_id not in STATE.notes:
                self.send_json(404, {"message": "note not found"})
                return
            STATE.contents[note_id] = self.read_text_body()
            self.send_response(204)
            self.end_headers()
            return
        self.send_json(404, {"message": "unknown path"})

    def do_PATCH(self):
        if not self.authorized():
            return
        if self.parsed().path.startswith("/etapi/notes/"):
            note_id = self.note_id_from_path()
            if note_id not in STATE.notes:
                self.send_json(404, {"message": "note not found"})
                return
            STATE.notes[note_id].update(self.read_json())
            self.send_json(200, STATE.notes[note_id])
            return
        self.send_json(404, {"message": "unknown path"})


class MockEtapiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        STATE.__init__()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockEtapiHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}/etapi"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def run_cli(self, *args, input_text=None):
        env = os.environ.copy()
        env["MOCK_TRILIUM_TOKEN"] = TOKEN
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--token-source",
            "env:MOCK_TRILIUM_TOKEN",
            "--base-url",
            self.base_url,
            *args,
        ]
        return subprocess.run(
            cmd,
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
            timeout=15,
        )

    def test_app_info(self):
        result = self.run_cli("app-info")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["appVersion"], "mock")
        self.assertNotIn(TOKEN, result.stdout)
        self.assertNotIn(TOKEN, result.stderr)

    def test_upsert_create_noop_update_and_tree_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = Path(tmp) / "note.md"
            content.write_text("# 标题\n\n第一版\n", encoding="utf-8")

            first = self.run_cli(
                "upsert-note",
                "--parent-id",
                "root",
                "--title",
                "Mock 笔记",
                "--type",
                "code",
                "--mime",
                "text/x-markdown",
                "--content-file",
                str(content),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertEqual(first_payload["action"], "created")
            note_id = first_payload["noteId"]

            second = self.run_cli(
                "upsert-note",
                "--parent-id",
                "root",
                "--title",
                "Mock 笔记",
                "--type",
                "code",
                "--mime",
                "text/x-markdown",
                "--content-file",
                str(content),
            )
            self.assertEqual(json.loads(second.stdout)["action"], "unchanged")

            found = self.run_cli("find-child", "root", "Mock 笔记")
            self.assertEqual(json.loads(found.stdout)["noteId"], note_id)

            children = self.run_cli("list-children", "root")
            titles = [item["title"] for item in json.loads(children.stdout)]
            self.assertIn("Mock 笔记", titles)

            content.write_text("# 标题\n\n第二版\n", encoding="utf-8")
            third = self.run_cli(
                "upsert-note",
                "--parent-id",
                "root",
                "--title",
                "Mock 笔记",
                "--type",
                "code",
                "--mime",
                "text/x-markdown",
                "--content-file",
                str(content),
            )
            self.assertEqual(json.loads(third.stdout)["action"], "updated")

            output = Path(tmp) / "out.md"
            readback = self.run_cli("get-content", note_id, "--output", str(output))
            self.assertEqual(readback.returncode, 0, readback.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "# 标题\n\n第二版\n")

    def test_wrong_token_does_not_leak_token(self):
        env_token = "wrong-token"
        env = os.environ.copy()
        env["MOCK_TRILIUM_TOKEN"] = env_token
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--token-source",
                "env:MOCK_TRILIUM_TOKEN",
                "--base-url",
                self.base_url,
                "app-info",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
            timeout=15,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(env_token, result.stdout)
        self.assertNotIn(env_token, result.stderr)


if __name__ == "__main__":
    unittest.main()
