"""Run: python -m unittest discover tests   (no GUI / API key needed)"""
import io
import threading
import unittest

from PIL import Image

from agent.config import Config
from agent.errors import Cancelled
from agent.llm import extract_json
from agent.prompts import describe_action, normalize_action, parse_step, parse_verify
from agent.screen import ScreenCapture, Shot
from agent.service import ServiceAgent


def fake_shot(w=1280, h=720):
    img = Image.new("RGB", (w, h), (30, 30, 30))
    return ScreenCapture._encode(img, {"max_dimension": 1280, "jpeg_quality": 70}, False)


class FakeEvents:
    def __init__(self, answers=()):
        self.logs, self.chat, self.result, self.answers = [], [], None, list(answers)
    def log(self, l, t): self.logs.append((l, t))
    def set_state(self, s, d=""): self.logs.append(("state", s))
    def set_step(self, i, n): pass
    def say(self, t): self.chat.append(t)
    def drain_inbox(self): return []
    def ask_user(self, q, cancel): self.chat.append(q); return self.answers.pop(0)
    def confirm(self, q, cancel): return True
    def finish(self, ok, msg): self.result = (ok, msg)


class FakeCapture:
    def grab(self, grid=None): return fake_shot()


class FakeController:
    def __init__(self): self.done = []
    def execute(self, a, shot, cancel=None): self.done.append(a)


class ScriptedClient:
    provider, model = "fake", "fake-1"
    def __init__(self, replies): self.replies = list(replies); self.calls = 0
    def complete(self, system, messages, json_mode=False, max_tokens=1500):
        self.calls += 1
        return self.replies.pop(0)


def step(action, **kw):
    import json
    return json.dumps({"observation": "obs", "reasoning": "why", "action": action,
                       "expected_result": "x", "risky": False, **kw})


VERIFY_OK = '{"verified": true, "observation": "looks right", "problem": "", "suggestion": ""}'
VERIFY_BAD = '{"verified": false, "observation": "nothing changed", "problem": "no change", "suggestion": "retry"}'


class Tests(unittest.TestCase):
    def test_extract_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n``` trailing')["a"], 1)
        self.assertEqual(extract_json('Sure! {"a": {"b": 2}} done')["a"]["b"], 2)
        with self.assertRaises(ValueError):
            extract_json("no json")

    def test_actions(self):
        self.assertEqual(normalize_action({"type": "hotkey", "keys": ["ctrl", "l"]})["keys"], "ctrl+l")
        self.assertEqual(normalize_action({"type": "left_click", "x": "10.4", "y": 20})["x"], 10)
        with self.assertRaises(ValueError):
            normalize_action({"type": "teleport"})
        with self.assertRaises(ValueError):
            normalize_action({"type": "click", "x": 1})
        self.assertIn("type", describe_action(normalize_action({"type": "type", "text": "hi", "enter": True})))
        self.assertEqual(parse_verify({"verified": "yes"})["verified"], True)

    def test_config_merge(self):
        c = Config({"agent": {"max_steps": 5}})
        self.assertEqual(c.data["agent"]["max_steps"], 5)
        self.assertIn("verify_each_step", c.data["agent"])

    def test_capture_shot(self):
        s = fake_shot(2560, 1440)
        self.assertEqual(s.width, 1280)
        self.assertEqual(Image.open(io.BytesIO(s.jpeg)).size, (1280, 720))
        self.assertLess(s.diff(fake_shot(2560, 1440)), 0.001)

    def run_agent(self, replies, answers=()):
        cfg = Config(); cfg.data["agent"]["post_action_delay"] = 0.0
        ev, ctl, cl = FakeEvents(answers), FakeController(), ScriptedClient(replies)
        ServiceAgent(cfg, cl, FakeCapture(), ctl, ev).run("send email", threading.Event())
        return ev, ctl, cl

    def test_loop_happy_path_with_verification(self):
        ev, ctl, cl = self.run_agent([
            step({"type": "click", "x": 100, "y": 50}), VERIFY_OK,
            step({"type": "type", "text": "hello", "enter": True}), VERIFY_OK,
            step({"type": "done", "summary": "sent"})])
        self.assertEqual([a["type"] for a in ctl.done], ["click", "type"])
        self.assertEqual(ev.result, (True, "sent"))
        self.assertEqual(cl.calls, 5)  # 3 plans + 2 verifications

    def test_loop_ask_user_then_continue(self):
        ev, ctl, _ = self.run_agent([
            step({"type": "ask_user", "question": "Which profile?"}),
            step({"type": "click", "x": 5, "y": 5}), VERIFY_OK,
            step({"type": "done", "summary": "ok"})], answers=["Work profile"])
        self.assertIn("Which profile?", ev.chat)
        self.assertEqual(len(ctl.done), 1)
        self.assertTrue(ev.result[0])

    def test_loop_retries_when_not_verified(self):
        ev, ctl, _ = self.run_agent([
            step({"type": "click", "x": 5, "y": 5}), VERIFY_BAD,
            step({"type": "click", "x": 9, "y": 9}), VERIFY_OK,
            step({"type": "done", "summary": "ok"})])
        self.assertEqual(len(ctl.done), 2)
        self.assertTrue(ev.result[0])

    def test_malformed_reply_is_retried(self):
        ev, ctl, _ = self.run_agent(["sorry, no json", step({"type": "done", "summary": "ok"})])
        self.assertTrue(ev.result[0])

    def test_cancel(self):
        cfg = Config(); ev = FakeEvents(); c = threading.Event(); c.set()
        with self.assertRaises(Cancelled):
            ServiceAgent(cfg, ScriptedClient([]), FakeCapture(), FakeController(), ev).run("x", c)


if __name__ == "__main__":
    unittest.main()
