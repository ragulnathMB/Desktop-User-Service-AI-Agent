"""Thread-safe bridge: worker threads -> Qt signals (also acts as the agent's `events` sink)."""
from __future__ import annotations

import queue

from PySide6.QtCore import QObject, Signal

from agent.errors import Cancelled


class Bridge(QObject):
    sig_log = Signal(str, str)          # level, text
    sig_state = Signal(str, str)        # state, detail
    sig_step = Signal(int, int)
    sig_chat = Signal(str, str)         # role, text
    sig_ask = Signal(str)
    sig_confirm = Signal(str)
    sig_task_finished = Signal(bool, str)
    sig_voice_state = Signal(str)
    sig_transcript = Signal(str)
    sig_voice_error = Signal(str)

    def __init__(self):
        super().__init__()
        self._answers: queue.Queue = queue.Queue()
        self._confirms: queue.Queue = queue.Queue()
        self._inbox: queue.Queue = queue.Queue()
        self.awaiting_answer = False
        self.awaiting_confirm = False

    # ---- events sink API (called from worker threads)
    def log(self, level: str, text: str):
        self.sig_log.emit(level, text)

    def set_state(self, state: str, detail: str = ""):
        self.sig_state.emit(state, detail)

    def set_step(self, i: int, n: int):
        self.sig_step.emit(i, n)

    def say(self, text: str):
        self.sig_chat.emit("assistant", text)

    def finish(self, ok: bool, message: str):
        self.sig_task_finished.emit(ok, message)

    def drain_inbox(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self._inbox.get_nowait())
            except queue.Empty:
                return out

    def ask_user(self, question: str, cancel) -> str:
        self._flush(self._answers)
        self.awaiting_answer = True
        self.sig_ask.emit(question)
        try:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                try:
                    return self._answers.get(timeout=0.2)
                except queue.Empty:
                    pass
        finally:
            self.awaiting_answer = False

    def confirm(self, question: str, cancel) -> bool:
        self._flush(self._confirms)
        self.awaiting_confirm = True
        self.sig_confirm.emit(question)
        try:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                try:
                    return self._confirms.get(timeout=0.2)
                except queue.Empty:
                    pass
        finally:
            self.awaiting_confirm = False

    # ---- called from the GUI thread
    def provide_answer(self, text: str):
        self._answers.put(text)

    def provide_confirm(self, ok: bool):
        self._confirms.put(ok)

    def push_inbox(self, text: str):
        self._inbox.put(text)

    @staticmethod
    def _flush(q: queue.Queue):
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break
