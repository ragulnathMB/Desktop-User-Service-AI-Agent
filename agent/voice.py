"""Microphone recording (with silence detection) + speech-to-text."""
from __future__ import annotations

import base64
import io
import threading
import wave

import requests

from .errors import LLMError

SR = 16000


def pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
    return buf.getvalue()


def record(vc: dict, stop: threading.Event) -> bytes:
    import numpy as np
    import sounddevice as sd
    block = int(SR * 0.1)
    frames, ambient = [], []
    started, silent, elapsed = False, 0.0, 0.0
    with sd.InputStream(samplerate=SR, channels=1, dtype="int16", blocksize=block) as stream:
        while not stop.is_set():
            data, _ = stream.read(block)
            rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
            frames.append(data.tobytes())
            elapsed += 0.1
            if elapsed <= 0.5:  # calibrate background noise
                ambient.append(rms)
                continue
            thr = max(350.0, (sum(ambient) / len(ambient)) * 2.5)
            if rms > thr:
                started, silent = True, 0.0
            elif started:
                silent += 0.1
                if silent >= float(vc["silence_seconds"]):
                    break
            if not started and elapsed > 8:
                return b""
            if elapsed >= float(vc["max_seconds"]):
                break
    return b"".join(frames) if (started or stop.is_set()) else b""


def transcribe(cfg, pcm: bytes) -> str:
    vc = cfg.data["voice"]
    engine, lang = vc["engine"], vc["language"]
    if engine == "openai":
        key = cfg.api_key("openai")
        if not key:
            raise LLMError("OpenAI API key missing (needed for Whisper transcription).")
        r = requests.post("https://api.openai.com/v1/audio/transcriptions",
                          headers={"Authorization": f"Bearer {key}"},
                          files={"file": ("audio.wav", pcm_to_wav(pcm), "audio/wav")},
                          data={"model": "whisper-1", "language": lang.split("-")[0]}, timeout=60)
        if r.status_code != 200:
            raise LLMError(f"Whisper error {r.status_code}: {r.text[:200]}")
        return r.json().get("text", "").strip()
    if engine == "gemini":
        key = cfg.api_key("gemini")
        if not key:
            raise LLMError("Gemini API key missing (needed for transcription).")
        sec = cfg.data["providers"]["gemini"]
        payload = {"contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(pcm_to_wav(pcm)).decode()}},
            {"text": "Transcribe this audio exactly. Reply with only the transcript."}]}]}
        r = requests.post(f"{sec['base_url']}/v1beta/models/{sec['model']}:generateContent",
                          headers={"x-goog-api-key": key}, json=payload, timeout=60)
        if r.status_code != 200:
            raise LLMError(f"Gemini error {r.status_code}: {r.text[:200]}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    # default: free Google web speech via SpeechRecognition
    import speech_recognition as sr
    rec = sr.Recognizer()
    try:
        return rec.recognize_google(sr.AudioData(pcm, SR, 2), language=lang).strip()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise LLMError(f"Speech service unavailable: {e}")


class VoiceService:
    """Runs record+transcribe in a background thread, reports via callbacks."""

    def __init__(self, cfg, on_state, on_text, on_error):
        self.cfg, self.on_state, self.on_text, self.on_error = cfg, on_state, on_text, on_error
        self._stop = threading.Event()
        self._thread = None

    @property
    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        try:
            self.on_state("listening")
            pcm = record(self.cfg.data["voice"], self._stop)
            if not pcm:
                self.on_error("I didn't hear anything. Try again.")
                return
            self.on_state("transcribing")
            text = transcribe(self.cfg, pcm)
            if text:
                self.on_text(text)
            else:
                self.on_error("Couldn't understand the audio.")
        except Exception as e:
            self.on_error(f"Voice input failed: {e}")
        finally:
            self.on_state("idle")
