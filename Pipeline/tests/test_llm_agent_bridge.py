import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from core.llm_agent_bridge import LLMAgentBridge


def make_server(model_reply):
    """Local fake of an Ollama /api/generate endpoint returning `model_reply`."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            payload = json.dumps({"response": model_reply}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class BridgeTests(unittest.TestCase):
    def ask(self, model_reply):
        server = make_server(model_reply)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        bridge = LLMAgentBridge(f"http://127.0.0.1:{server.server_port}", timeout=5)
        return bridge.generate_tactical_plan({"x": 2, "y": 3})

    def test_valid_model_reply_is_used(self):
        plan = self.ask(json.dumps({"action": "hold_position", "target": [5, 6]}))
        self.assertEqual(plan, {"action": "hold_position", "target": [5.0, 6.0], "source": "llm"})

    def test_unknown_action_falls_back(self):
        plan = self.ask(json.dumps({"action": "self_destruct", "target": [1, 1]}))
        self.assertEqual(plan["source"], "fallback")

    def test_malformed_target_falls_back(self):
        plan = self.ask(json.dumps({"action": "hold_position", "target": ["a", 1]}))
        self.assertEqual(plan["source"], "fallback")

    def test_non_json_reply_falls_back(self):
        self.assertEqual(self.ask("not json at all")["source"], "fallback")

    def test_unreachable_endpoint_falls_back(self):
        bridge = LLMAgentBridge("http://127.0.0.1:1", timeout=1)
        plan = bridge.generate_tactical_plan({"x": 2, "y": 3})
        self.assertEqual(plan, {"action": "reposition_swarm", "target": [3.0, 3], "source": "fallback"})


if __name__ == "__main__":
    unittest.main()