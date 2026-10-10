"""Checks request shape + response parsing of the 3 providers against a local mock server."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent.llm import PROVIDERS, Message

SEEN = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN[self.path] = (dict(self.headers), body)
        if self.path.startswith("/v1/messages"):
            out = {"content": [{"type": "text", "text": '{"ok": "claude"}'}]}
        elif ":generateContent" in self.path:
            out = {"candidates": [{"content": {"parts": [{"text": '{"ok": "gemini"}'}]}}]}
        else:
            out = {"choices": [{"message": {"content": '{"ok": "openai"}'}}]}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def msgs(self): return [Message("user", "hi", [b"\xff\xd8fakejpeg"])]

    def test_claude(self):
        r = PROVIDERS["claude"]("k", "m", self.base).complete("sys", self.msgs(), True)
        h, b = SEEN["/v1/messages"]
        self.assertIn('claude', r)
        self.assertEqual(h["x-api-key"], "k")
        self.assertEqual(b["system"], "sys")
        self.assertEqual(b["messages"][0]["content"][0]["type"], "image")

    def test_gemini(self):
        r = PROVIDERS["gemini"]("k", "gem", self.base).complete("sys", self.msgs(), True)
        h, b = SEEN["/v1beta/models/gem:generateContent"]
        self.assertIn('gemini', r)
        self.assertEqual(h["x-goog-api-key"], "k")
        self.assertIn("inline_data", b["contents"][0]["parts"][0])
        self.assertEqual(b["generationConfig"]["responseMimeType"], "application/json")

    def test_openai(self):
        r = PROVIDERS["openai"]("k", "gpt", self.base).complete("sys", self.msgs(), True)
        h, b = SEEN["/chat/completions"]
        self.assertIn('openai', r)
        self.assertEqual(h["Authorization"], "Bearer k")
        self.assertTrue(b["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(b["response_format"], {"type": "json_object"})

    def test_missing_key(self):
        from agent.errors import LLMError
        with self.assertRaises(LLMError):
            PROVIDERS["claude"]("", "m", self.base)


if __name__ == "__main__":
    unittest.main()
