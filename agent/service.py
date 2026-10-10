"""ServiceAgent: plan -> act -> screenshot -> verify loop."""
from __future__ import annotations

import time

from .errors import Cancelled, ControllerError, LLMError
from .llm import Message, extract_json
from .platform_utils import get_foreground, modifier_key, os_label, restore_foreground
from .prompts import (NO_VERIFY, describe_action, parse_step, parse_verify, planner_system,
                      planner_user, verifier_system, verifier_user)


class ServiceAgent:
    """`events` must provide: log(level,text) set_state(state,detail) set_step(i,n) say(text)
    ask_user(q,cancel)->str confirm(q,cancel)->bool drain_inbox()->list[str] finish(ok,msg)."""

    def __init__(self, cfg, client, capture, controller, events):
        self.cfg, self.client, self.capture, self.ctl, self.ev = cfg, client, capture, controller, events
        self.ac = cfg.data["agent"]
        self.lang = cfg.data["language"]

    # ------------------------------------------------------------ plumbing
    @staticmethod
    def _check(cancel):
        if cancel.is_set():
            raise Cancelled()

    def _sleep(self, secs, cancel):
        end = time.time() + secs
        while time.time() < end:
            self._check(cancel)
            time.sleep(min(0.1, max(0.0, end - time.time())))

    def _grab(self, cancel):
        self._check(cancel)
        self.ev.set_state("capturing", "Taking screenshot")
        shot = self.capture.grab()
        self.ev.log("capture", f"Screenshot taken ({shot.width}×{shot.height}) – assistant windows hidden")
        return shot

    def _ask_model(self, system, text, shot, cancel, parse):
        last_err = None
        for _ in range(2):
            self._check(cancel)
            raw = self.client.complete(system, [Message("user", text, [shot.jpeg])], json_mode=True, max_tokens=1500)
            self._check(cancel)
            try:
                return parse(extract_json(raw))
            except ValueError as e:
                last_err = e
                self.ev.log("warn", f"Model reply was malformed ({e}); asking again")
                text += "\n\nYour previous reply was not valid JSON in the required format. Reply with ONLY the JSON object."
        raise LLMError(f"Model kept returning malformed replies ({last_err})")

    def _ask_user(self, question, cancel):
        fg = get_foreground()
        self.ev.set_state("waiting", "Waiting for your reply")
        self.ev.log("user", f"Asking you: {question}")
        answer = self.ev.ask_user(question, cancel)
        self.ev.log("user", f"You answered: {answer}")
        if fg:
            time.sleep(0.5)
            restore_foreground(fg)
            time.sleep(0.3)
        return answer

    # ----------------------------------------------------------------- run
    def run(self, command: str, cancel) -> None:
        ev, ac = self.ev, self.ac
        ev.log("user", f"Task: {command}")
        history: list[str] = []
        retries = stuck_asks = 0
        shot = self._grab(cancel)

        for step in range(1, int(ac["max_steps"]) + 1):
            self._check(cancel)
            for note in ev.drain_inbox():
                history.append(f"User said (mid-task): {note}")
                ev.log("user", f"You said: {note}")
            ev.set_step(step, int(ac["max_steps"]))
            ev.set_state("thinking", f"Step {step}: asking {self.client.provider} for the next action")
            system = planner_system(os_label(), shot.width, shot.height, self.lang, modifier_key())
            plan = self._ask_model(system, planner_user(command, history), shot, cancel, parse_step)
            action, t = plan["action"], plan["action"]["type"]
            if plan["observation"]:
                ev.log("llm", f"Sees: {plan['observation']}")
            if plan["say"]:
                ev.say(plan["say"])

            if t == "done":
                ev.log("ok", f"Task complete: {action['summary']}")
                ev.finish(True, action["summary"])
                return
            if t == "fail":
                ev.log("error", f"Cannot complete: {action['reason']}")
                ev.finish(False, action["reason"])
                return
            if t == "ask_user":
                answer = self._ask_user(action["question"], cancel)
                history.append(f"Asked user: {action['question']} -> User answered: {answer}")
                shot = self._grab(cancel)
                continue

            desc = describe_action(action)
            ev.log("llm", f"Plan: {desc}" + (f"  ({plan['reasoning']})" if plan["reasoning"] else ""))

            if plan["risky"] and ac["confirm_risky"]:
                ev.set_state("waiting", "Waiting for your approval")
                if not ev.confirm(f"The assistant wants to: {desc}\nReason: {plan['reasoning'] or plan['observation']}", cancel):
                    ev.log("warn", "You denied the action")
                    history.append(f"Step {step}: {desc} -> DENIED by user, choose another way or ask the user")
                    continue

            ev.set_state("acting", desc.capitalize())
            ev.log("action", desc)
            try:
                self.ctl.execute(action, shot, cancel)
            except ControllerError as e:
                ev.log("error", f"Action failed: {e}")
                history.append(f"Step {step}: {desc} -> ERROR: {e}")
                retries += 1
                shot = self._grab(cancel)
                if retries > int(ac["max_retries"]):
                    retries, stuck_asks = 0, stuck_asks + 1
                    if stuck_asks > 3:
                        ev.finish(False, "Stuck after several failed attempts.")
                        return
                    ans = self._ask_user(f"An action keeps failing ({e}). How should I proceed?", cancel)
                    history.append(f"Asked user for help -> {ans}")
                continue

            self._sleep(float(ac["post_action_delay"]), cancel)
            shot = self._grab(cancel)

            if t in NO_VERIFY or not ac["verify_each_step"]:
                history.append(f"Step {step}: {desc} (done, not separately verified)")
                continue

            ev.set_state("verifying", "Checking the result on screen")
            v = self._ask_model(verifier_system(self.lang), verifier_user(command, desc, plan["expected_result"]),
                                shot, cancel, parse_verify)
            if v["verified"]:
                retries = 0
                ev.log("verify", f"Verified: {v['observation']}")
                history.append(f"Step {step}: {desc} -> verified: {v['observation']}")
            else:
                retries += 1
                ev.log("warn", f"Not verified: {v['problem'] or v['observation']}")
                history.append(f"Step {step}: {desc} -> NOT VERIFIED: {v['problem'] or v['observation']}"
                               + (f" Suggestion: {v['suggestion']}" if v["suggestion"] else ""))
                if retries > int(ac["max_retries"]):
                    stuck_asks += 1
                    if stuck_asks > 3:
                        ev.finish(False, "Stuck: the screen did not respond as expected.")
                        return
                    ans = self._ask_user(f"I'm stuck: {v['problem'] or v['observation']}. How should I proceed?", cancel)
                    history.append(f"Asked user for help -> {ans}")
                    retries = 0

        ev.finish(False, f"Stopped after {ac['max_steps']} steps without finishing.")
