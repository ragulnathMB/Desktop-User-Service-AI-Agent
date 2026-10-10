"""Screenshot capture (own windows are hidden / excluded)."""
from __future__ import annotations

import io
import time
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Shot:
    jpeg: bytes
    width: int
    height: int
    ts: float = field(default_factory=time.time)
    thumb: np.ndarray | None = None

    def diff(self, other: "Shot") -> float:
        """Mean absolute difference 0..1 between two screenshots."""
        if self.thumb is None or other.thumb is None:
            return 1.0
        return float(np.mean(np.abs(self.thumb - other.thumb)) / 255.0)


class ScreenCapture:
    def __init__(self, cfg, hider=None):
        self.cfg = cfg
        self.hider = hider  # object with needs_hide(), hide(), restore()

    def grab(self, grid: bool | None = None) -> Shot:
        import mss
        c = self.cfg.data["capture"]
        hide = bool(self.hider and self.hider.needs_hide())
        if hide:
            self.hider.hide()
            time.sleep(0.18)  # let the compositor repaint without our windows
        try:
            with mss.mss() as sct:
                mon = sct.monitors[1]  # primary monitor
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        finally:
            if hide:
                self.hider.restore()
        return self._encode(img, c, grid if grid is not None else self.cfg.data["agent"]["grid_overlay"])

    @staticmethod
    def _encode(img: Image.Image, c: dict, grid: bool) -> Shot:
        scale = min(1.0, c["max_dimension"] / max(img.size))
        if scale < 1.0:
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        thumb = np.asarray(img.convert("L").resize((64, 36)), dtype=np.float32)
        if grid:
            d = ImageDraw.Draw(img, "RGBA")
            step = 100
            for x in range(0, img.width, step):
                d.line([(x, 0), (x, img.height)], fill=(255, 0, 80, 70), width=1)
                d.text((x + 2, 2), str(x), fill=(255, 0, 80, 230))
            for y in range(0, img.height, step):
                d.line([(0, y), (img.width, y)], fill=(255, 0, 80, 70), width=1)
                d.text((2, y + 2), str(y), fill=(255, 0, 80, 230))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=int(c["jpeg_quality"]))
        return Shot(buf.getvalue(), img.width, img.height, thumb=thumb)
