"""Bridge between a local LLM and the simulation agents.

Asks an Ollama-compatible endpoint for a tactical plan and validates the answer
before it reaches the simulator. If the model is unreachable or returns
something invalid, a deterministic rule-based plan is used instead, and the
result says which source produced it ("llm" or "fallback").

Uses only the Python standard library.
"""
import json
import urllib.error
import urllib.request

ALLOWED_ACTIONS = {"reposition_swarm", "hold_position", "return_to_base"}


class LLMAgentBridge:
    def __init__(self, model_endpoint="http://localhost:11434", model="llama3.2", timeout=10.0):
        self.endpoint = model_endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _build_prompt(self, state):
        return (
            "You control a robot swarm. Current state as JSON: "
            f"{json.dumps(state)}. Reply with JSON only, in the form "
            '{"action": "<reposition_swarm|hold_position|return_to_base>", '
            '"target": [x, y]}.'
        )

    def _query_model(self, prompt):
        body = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))["response"]

    @staticmethod
    def _validate(plan):
        if not isinstance(plan, dict) or plan.get("action") not in ALLOWED_ACTIONS:
            return None
        target = plan.get("target")
        if (
            not isinstance(target, list)
            or len(target) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in target)
        ):
            return None
        return {"action": plan["action"], "target": [float(target[0]), float(target[1])]}

    @staticmethod
    def _fallback_plan(state):
        return {
            "action": "reposition_swarm",
            "target": [state.get("x", 0) + 1.0, state.get("y", 0)],
            "source": "fallback",
        }

    def generate_tactical_plan(self, current_state):
        try:
            raw = self._query_model(self._build_prompt(current_state))
            plan = self._validate(json.loads(raw))
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            plan = None
        if plan is None:
            return self._fallback_plan(current_state)
        plan["source"] = "llm"
        return plan