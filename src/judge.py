"""Note-quality judge: scores the *record* left on the ticket (0–2).

Deterministic state verifiers check that a note EXISTS; this judge checks
whether the note is USEFUL — the forward-looking rubric for handoffs.

  2 = specific + policy-grounded (mentions verification, SOP, team, or evidence)
  1 = generic ("done", "handled") — present but not auditable
  0 = no note recorded

With OPENAI_API_KEY set, an LLM re-scores with the same rubric (method="llm");
otherwise the heuristic applies (method="heuristic"). Scores from the heuristic
and LLM agree on obvious cases by construction; report both methods.
"""
from __future__ import annotations

import json

from .llm import get_client, chat

DETAIL_MARKERS = ("mfa", "verif", "sop", "kb", "escalat", "netops", "secops",
                  "it-admin", "manager", "approv", "policy", "refus", "latency",
                  "degraded", "healthy", "wipe", "revok", "pool", "encrypt")


def _notes_from_trajectory(trajectory) -> list[str]:
    notes = []
    for s in trajectory:
        if s["tool"] in ("update_ticket", "escalate_ticket") and s["ok"]:
            try:
                out = eval(s["output"]) if isinstance(s["output"], str) else s["output"]
            except Exception:
                out = {}
            if isinstance(out, dict):
                for key in ("ticket",):
                    t = out.get(key)
                    if isinstance(t, dict):
                        notes.extend(t.get("notes", []))
                if s["tool"] == "escalate_ticket":
                    notes.append(str(s["args"]))
    # fall back: parse note args directly
    for s in trajectory:
        if s["tool"] == "update_ticket" and isinstance(s.get("args"), dict) and s["args"].get("note"):
            notes.append(s["args"]["note"])
    return notes


def heuristic_score(notes: list[str]) -> tuple[int, str]:
    if not notes:
        return 0, "no note recorded on ticket"
    blob = " ".join(notes).lower()
    if len(blob) < 12:
        return 1, "note present but too short to audit"
    if any(m in blob for m in DETAIL_MARKERS):
        return 2, "note references verification/evidence/routing"
    return 1, "generic note, no policy detail"


def score_from_trajectory(task, trajectory) -> dict:
    notes = _notes_from_trajectory(trajectory)
    score, rationale = heuristic_score(notes)
    result = {"score": score, "max": 2, "method": "heuristic",
              "rationale": rationale, "notes": notes[:4]}
    client = get_client()
    if client is not None:
        try:
            text = chat(client, [
                {"role": "system", "content": "Score this service-desk ticket note 0-2. 2=specific+policy-grounded, 1=generic, 0=absent. Reply JSON {\"score\": n, \"rationale\": \"...\"}."},
                {"role": "user", "content": f"Task: {task['title']}\nNotes: {json.dumps(notes[:4])}"}])
            parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
            result = {"score": int(parsed.get("score", score)), "max": 2,
                      "method": "llm", "rationale": str(parsed.get("rationale", ""))[:200],
                      "notes": notes[:4]}
        except Exception:
            pass  # keep heuristic on LLM failure
    return result
