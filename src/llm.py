"""Minimal OpenAI-compatible chat client on stdlib only (urllib).

Env vars:
  OPENAI_API_KEY   — if absent, client is disabled (offline mode)
  OPENAI_BASE_URL  — default https://api.openai.com/v1
  EVAL_MODEL       — default gpt-4o-mini

Returns None when no key is set so agents/judge can fall back to
deterministic offline logic. No third-party deps required.
"""
from __future__ import annotations

import json
import os
import urllib.request


def get_client():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("EVAL_MODEL", "gpt-4o-mini"),
    }


def chat(client, messages, max_tokens=400, temperature=0.0, timeout=30) -> str:
    """One chat completion, returns assistant text (raises on HTTP error)."""
    url = f"{client['base_url']}/chat/completions"
    payload = json.dumps({"model": client["model"], "messages": messages,
                          "max_tokens": max_tokens, "temperature": temperature}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {client['api_key']}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]
