"""LLM-backed ReAct agent with offline fallback.

- With OPENAI_API_KEY set: real ReAct loop against any OpenAI-compatible
  endpoint (OpenAI, Azure, local vLLM/Ollama via OPENAI_BASE_URL).
  Model emits one JSON tool call per turn: {"tool": ..., "args": {...}}
  or {"final": "summary note"} which is recorded on the ticket.
- Without a key (default): delegates to ReActAgent so evals always run
  offline and reproducibly. Trajectory-identical to react-mock in fallback.

Register as AGENTS["llm"] in run_eval.
"""
from __future__ import annotations

import json

from .agents import ReActAgent
from .llm import get_client, chat
from .tools import TOOL_SPECS

SYSTEM = """You are an enterprise service-desk agent. You have tools.
Each turn reply with EXACTLY one JSON object, no other text:
  {"tool": "<name>", "args": {...}}  to call a tool, or
  {"final": "<short summary>"} when the task is fully done (state fixed AND ticket updated).
Rules: verify MFA/policy before writes; never invent tools; if a write fails, read KB/ticket and recover or escalate.
Available tools: """ + ", ".join(t["name"] for t in TOOL_SPECS)


def _parse(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object")
    return json.loads(text[start:end + 1])


class LLMAgent:
    name = "llm-react"
    max_steps = 12

    def __init__(self, max_steps=12):
        self.max_steps = max_steps
        self.used_fallback = False

    def run(self, task, call):
        client = get_client()
        if client is None:  # offline: reproducible fallback
            self.used_fallback = True
            ReActAgent().run(task, call)
            return
        tid = task["ticket_id"]
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Ticket {tid}: {task['prompt']}"}]
        for _ in range(self.max_steps):
            try:
                text = chat(client, messages)
            except Exception:
                self.used_fallback = True
                ReActAgent().run(task, call)  # recover: finish deterministically
                return
            try:
                action = _parse(text)
            except ValueError:
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": "Reply with exactly one JSON object."})
                continue
            if "final" in action:
                call("update_ticket", {"ticket_id": tid, "status": "resolved",
                                       "note": str(action["final"])[:300]})
                return
            tool, args = action.get("tool", ""), action.get("args", {}) or {}
            out = call(tool, args if isinstance(args, dict) else {})
            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": f"Tool result: {json.dumps(out)[:800]}"})
        call("update_ticket", {"ticket_id": tid, "status": "resolved",
                               "note": "LLM agent hit step budget; partial handling recorded."})
