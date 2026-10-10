import sys, types, unittest
from agent.config import Config
from agent.controller import DesktopController, normalize_keys
from agent.errors import ControllerError


class FakePG(types.SimpleNamespace):
    pass


def make():
    calls = []
    pg = types.ModuleType("pyautogui")
    pg.FAILSAFE = True; pg.PAUSE = 0
    pg.KEYBOARD_KEYS = ["ctrl", "l", "enter", "win", "a", "v", "tab", "alt"]
    pg.FailSafeException = type("FailSafeException", (Exception,), {})
    pos = [0, 0]
    pg.size = lambda: (1920, 1080)
    pg.position = lambda: tuple(pos)
    def moveTo(x, y, duration=0, _pause=True, **k): pos[:] = [x, y]; calls.append(("move", round(x), round(y)))
    pg.moveTo = moveTo
    pg.click = lambda x, y, clicks=1, interval=0, button="left": calls.append(("click", x, y, clicks, button))
    pg.press = lambda k: calls.append(("press", k))
    pg.hotkey = lambda *k, interval=0: calls.append(("hotkey",) + k)
    pg.write = lambda ch, interval=0: calls.append(("write", ch))
    pg.scroll = lambda n: calls.append(("scroll", n))
    sys.modules["pyautogui"] = pg
    cfg = Config(); cfg.data["agent"]["human_like"] = False
    return DesktopController(cfg), calls


class Shot:  # 1280x720 screenshot of a 1920x1080 screen
    width, height = 1280, 720


class T(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(normalize_keys("Ctrl + L"), ["ctrl", "l"])
        self.assertEqual(normalize_keys("Return"), ["enter"])
        self.assertEqual(normalize_keys("windows"), ["win"])

    def test_click_scaling(self):
        c, calls = make()
        c.execute({"type": "click", "x": 640, "y": 360}, Shot())
        self.assertIn(("click", 960, 540, 1, "left"), calls)   # scaled 1.5x

    def test_double_right(self):
        c, calls = make()
        c.execute({"type": "double_click", "x": 100, "y": 100}, Shot())
        c.execute({"type": "right_click", "x": 100, "y": 100}, Shot())
        self.assertIn(("click", 150, 150, 2, "left"), calls)
        self.assertIn(("click", 150, 150, 1, "right"), calls)

    def test_keys_and_type(self):
        c, calls = make()
        c.execute({"type": "key", "keys": "ctrl+l"}, Shot())
        c.execute({"type": "type", "text": "a@b", "enter": True}, Shot())
        self.assertIn(("hotkey", "ctrl", "l"), calls)
        self.assertEqual([x[1] for x in calls if x[0] == "write"], ["a", "@", "b"])
        self.assertIn(("press", "enter"), calls)

    def test_bad_key(self):
        c, _ = make()
        with self.assertRaises(ControllerError):
            c.execute({"type": "key", "keys": "ctrl+banana"}, Shot())

    def test_corner_clamped(self):
        c, calls = make()
        c.execute({"type": "click", "x": 0, "y": 0}, Shot())
        self.assertNotIn(("click", 0, 0, 1, "left"), calls)


if __name__ == "__main__":
    unittest.main()
