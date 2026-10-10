"""All prompts + action parsing helpers."""
from __future__ import annotations

# --------------------------------------------------------------- summarizer
DETAIL_HINTS = {
    "brief": "Keep it to at most 3 short lines.",
    "balanced": "Start with a one-line bold headline, then 3-6 concise bullet points.",
    "detailed": ("Start with a bold headline, then use the sections: **What's on screen**, "
                 "**Key details** (names, numbers, dates, errors, links) and **Suggested next steps**."),
}


def summarizer_system(language: str, detail: str) -> str:
    return (f"You are a screen summarizer. You receive a screenshot of the user's desktop and explain what is "
            f"happening on it: which app/site is open, what the user seems to be doing, and the important "
            f"content (text, numbers, errors, messages). Be factual, never invent text you cannot read. "
            f"{DETAIL_HINTS.get(detail, DETAIL_HINTS['balanced'])} Reply in {language} using Markdown.")


def summarizer_user(focus: str, previous: str) -> str:
    t = "Summarize this screenshot."
    if focus.strip():
        t += f"\nFocus on: {focus.strip()}"
    if previous:
        t += ("\n\nFor context, the previous summary was:\n" + previous[:600] +
              "\nIf the screen is similar, concentrate on what changed.")
    return t


# -------------------------------------------------------------------- agent
ACTION_TYPES = {"click", "double_click", "right_click", "move", "drag", "type", "key",
                "scroll", "wait", "ask_user", "done", "fail"}
ALIASES = {"left_click": "click", "tap": "click", "doubleclick": "double_click", "rightclick": "right_click",
           "press": "key", "hotkey": "key", "keypress": "key", "write": "type", "input": "type",
           "text": "type", "finish": "done", "complete": "done", "ask": "ask_user", "wait_for": "wait",
           "sleep": "wait", "drag_and_drop": "drag", "mouse_move": "move", "scroll_down": "scroll",
           "scroll_up": "scroll"}
NO_VERIFY = {"wait", "move"}


def planner_system(os_name: str, w: int, h: int, language: str, modifier: str) -> str:
    return f"""You are the reasoning engine of a desktop automation agent that operates a {os_name} computer exactly like a careful human: you look at a screenshot and then use the mouse and keyboard, ONE action at a time. After every action a fresh screenshot is taken and verified, so never assume an action worked.

SCREENSHOT GEOMETRY
- The screenshot is {w}x{h} pixels, (0,0) is the top-left corner. Every x/y you output MUST be pixel coordinates inside that image, aimed at the centre of the target element.
- The mouse pointer is not drawn in screenshots. The agent's own windows are invisible to you; ignore them.

REPLY FORMAT: return ONLY one JSON object (no markdown fences, no extra text):
{{
  "observation": "one sentence: what is on screen right now",
  "reasoning": "one sentence: why this is the next step",
  "say": "optional short progress note for the user in {language} (empty string if nothing to say)",
  "action": {{"type": "...", ...}},
  "expected_result": "what should be visible after this action succeeds",
  "risky": false
}}

ACTION TYPES (action.type):
- click | double_click | right_click : {{"x":int,"y":int}}
- move : {{"x":int,"y":int}}
- drag : {{"x":int,"y":int,"x2":int,"y2":int}}
- type : {{"text":"...","enter":false}}  types into the currently focused field (set enter=true to press Enter afterwards)
- key : {{"keys":"ctrl+l"}}  a single key or a combo joined by '+', e.g. "enter", "win", "alt+tab", "{modifier}+a", "{modifier}+v"
- scroll : {{"amount":int,"x":int,"y":int}}  positive = up, negative = down, in wheel notches (x,y optional)
- wait : {{"seconds":number}}  while something loads (max 30)
- ask_user : {{"question":"..."}}  ask the human in chat (in {language})
- done : {{"summary":"..."}}  ONLY when the whole task is finished and you can SEE proof of it on screen
- fail : {{"reason":"..."}}  the task cannot be completed

RULES
1. Exactly one action per reply. Look at the screenshot first; never act on stale assumptions.
2. Click a text field before typing into it. Prefer reliable keyboard shortcuts when obviously correct (e.g. ctrl+l for a browser address bar, the Win/Cmd key to search for apps).
3. If something is ambiguous (several browser profiles/accounts/windows, several matching contacts, a choice only the user can make) or essential information is missing (dates, recipient, amounts), use ask_user. Don't guess important details. For minor details (e.g. an email subject or a polite short body) you may draft sensible content yourself and mention it in "say".
4. Never type passwords or handle CAPTCHAs/2FA; ask the user to do it themselves via ask_user, then continue.
5. Set "risky": true for actions that are destructive, financial, or go beyond what the user asked (deleting data, purchases, changing settings, sending something the user did not request). Normal steps of the requested task, including sending a message the user asked for, are NOT risky.
6. If the previous action failed, do not repeat it blindly: try another approach (different element, keyboard shortcut, scroll, wait).
7. If the PROGRESS list shows the work is already finished, reply with done.
8. Be efficient: no unnecessary steps. Output valid JSON only."""


def planner_user(task: str, history: list[str]) -> str:
    omitted = max(0, len(history) - 14)
    hist = "\n".join(history[-14:]) if history else "(no steps taken yet)"
    if omitted:
        hist = f"({omitted} earlier steps omitted)\n" + hist
    return (f"TASK FROM USER: {task}\n\nPROGRESS SO FAR:\n{hist}\n\n"
            "The attached image is the CURRENT screen. Decide the single next action. JSON only.")


def verifier_system(language: str) -> str:
    return f"""You verify the outcome of ONE desktop action performed by an automation agent. You get the task, the action that was just performed, what was expected, and a screenshot taken AFTER the action.

Judge strictly from the screenshot. Reply with ONLY this JSON object:
{{
  "verified": true or false,
  "observation": "what the screen shows now, one sentence",
  "problem": "if not verified: what went wrong or what is different from expectation, else empty string",
  "suggestion": "if not verified: a concrete alternative approach, else empty string"
}}
Be fair: if the expected result is clearly visible (or the screen changed in the intended way), verified is true. If the screen did not change, a wrong element was hit, a dialog/popup blocks the way, or text went to the wrong place, verified is false. Write text in {language}."""


def verifier_user(task: str, action_desc: str, expected: str) -> str:
    return (f"TASK: {task}\nACTION PERFORMED: {action_desc}\nEXPECTED RESULT: {expected or '(not specified)'}\n\n"
            "The attached image is the screen AFTER the action. JSON only.")


# --------------------------------------------------------------- parsing
def _num(v, name):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        raise ValueError(f"action field '{name}' must be a number")


def normalize_action(a: dict) -> dict:
    if not isinstance(a, dict):
        raise ValueError("'action' must be an object")
    t = str(a.get("type", "")).strip().lower().replace("-", "_").replace(" ", "_")
    t = ALIASES.get(t, t)
    if t not in ACTION_TYPES:
        raise ValueError(f"unknown action type '{t}'")
    out = {"type": t}
    if t in ("click", "double_click", "right_click", "move"):
        out["x"], out["y"] = _num(a.get("x"), "x"), _num(a.get("y"), "y")
    elif t == "drag":
        out["x"], out["y"] = _num(a.get("x"), "x"), _num(a.get("y"), "y")
        out["x2"], out["y2"] = _num(a.get("x2"), "x2"), _num(a.get("y2"), "y2")
    elif t == "type":
        if "text" not in a:
            raise ValueError("type action needs 'text'")
        out["text"] = str(a["text"])
        out["enter"] = bool(a.get("enter", False))
    elif t == "key":
        keys = a.get("keys", a.get("key"))
        if isinstance(keys, (list, tuple)):
            keys = "+".join(str(k) for k in keys)
        if not keys:
            raise ValueError("key action needs 'keys'")
        out["keys"] = str(keys)
    elif t == "scroll":
        amt = a.get("amount", -3)
        out["amount"] = _num(amt, "amount")
        if "x" in a and "y" in a and a["x"] is not None and a["y"] is not None:
            out["x"], out["y"] = _num(a["x"], "x"), _num(a["y"], "y")
    elif t == "wait":
        try:
            out["seconds"] = max(0.2, min(30.0, float(a.get("seconds", 2))))
        except (TypeError, ValueError):
            out["seconds"] = 2.0
    elif t == "ask_user":
        out["question"] = str(a.get("question") or a.get("text") or "I need your input to continue.")
    elif t == "done":
        out["summary"] = str(a.get("summary") or "Task completed.")
    elif t == "fail":
        out["reason"] = str(a.get("reason") or "The task cannot be completed.")
    return out


def parse_step(obj: dict) -> dict:
    if isinstance(obj.get("actions"), list) and obj["actions"] and "action" not in obj:
        obj["action"] = obj["actions"][0]
    if "action" not in obj:
        raise ValueError("reply has no 'action'")
    return {
        "observation": str(obj.get("observation") or ""),
        "reasoning": str(obj.get("reasoning") or ""),
        "say": str(obj.get("say") or ""),
        "action": normalize_action(obj["action"]),
        "expected_result": str(obj.get("expected_result") or ""),
        "risky": bool(obj.get("risky", False)),
    }


def parse_verify(obj: dict) -> dict:
    if "verified" not in obj:
        raise ValueError("reply has no 'verified'")
    v = obj["verified"]
    if isinstance(v, str):
        v = v.strip().lower() in ("true", "yes", "1")
    return {"verified": bool(v), "observation": str(obj.get("observation") or ""),
            "problem": str(obj.get("problem") or ""), "suggestion": str(obj.get("suggestion") or "")}


def describe_action(a: dict) -> str:
    t = a["type"]
    if t in ("click", "double_click", "right_click"):
        return f"{t.replace('_', ' ')} at ({a['x']}, {a['y']})"
    if t == "move":
        return f"move mouse to ({a['x']}, {a['y']})"
    if t == "drag":
        return f"drag ({a['x']}, {a['y']}) → ({a['x2']}, {a['y2']})"
    if t == "type":
        txt = a["text"] if len(a["text"]) <= 60 else a["text"][:57] + "..."
        return f'type "{txt}"' + (" + Enter" if a.get("enter") else "")
    if t == "key":
        return f"press {a['keys']}"
    if t == "scroll":
        return f"scroll {'up' if a['amount'] > 0 else 'down'} {abs(a['amount'])}"
    if t == "wait":
        return f"wait {a['seconds']:g}s"
    if t == "ask_user":
        return "ask you a question"
    return t
