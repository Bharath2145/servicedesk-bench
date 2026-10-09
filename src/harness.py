"""Eval harness: runs an agent against tasks with full trajectory logging.

Usage:
    python -m src.run_eval --agent react --output results/react.json
    python -m src.run_eval --agent all

Each result row: task_id, passed, checks, steps, tool_names, errors,
tokens_est, cost_est_usd, failure_mode. Deterministic + reproducible:
same seed data every run (EnterpriseEnv.seed), per-task setup applied,
verifier is pure state check — no LLM-as-judge flakiness.
"""
from __future__ import annotations

import json
import time

from .env import EnterpriseEnv
from .tasks import TASKS, apply_setup
from .tools import call_tool
from .metrics import classify_failure

MAX_STEPS = 12
COST_PER_WRITE = 0.002  # fake $ accounting to demonstrate cost tracking
COST_PER_READ = 0.0002
READ_TOOLS = {"get_ticket", "search_kb", "get_user", "list_devices", "get_network_status"}


def run_task(agent, task_def) -> dict:
    env = apply_setup(EnterpriseEnv.seed(), task_def)
    trajectory = []
    errors = []

    def tool_caller(name: str, args: dict) -> dict:
        t0 = time.perf_counter()
        out = call_tool(env, name, dict(args or {}))
        dt_ms = (time.perf_counter() - t0) * 1000
        trajectory.append({"tool": name, "args": dict(args or {}),
                           "ok": out.get("ok"), "output": str(out)[:600],
                           "latency_ms": round(dt_ms, 2)})
        if not out.get("ok"):
            errors.append(f"{name}: {out.get('error')}")
        return out

    try:
        agent.run(task_def, tool_caller)
    except Exception as e:  # agent crash is a scored outcome, not a harness crash
        errors.append(f"agent_crash: {e}")

    passed, checks = task_def["verify"](env, trajectory)
    tool_names = [s["tool"] for s in trajectory]
    tokens_est = sum(len(f"{s['tool']}{s['args']}") // 4 + 40 for s in trajectory)
    cost = sum(COST_PER_WRITE if t not in READ_TOOLS else COST_PER_READ for t in tool_names)
    failure_mode = classify_failure(passed, trajectory, errors, env, task_def)

    return {"task_id": task_def["id"], "title": task_def["title"],
            "category": task_def["category"], "difficulty": task_def["difficulty"],
            "passed": bool(passed), "checks": checks, "steps": len(trajectory),
            "gold_steps": len(task_def["gold_steps"]), "tool_names": tool_names,
            "trajectory": trajectory, "errors": errors,
            "tokens_est": tokens_est, "cost_est_usd": round(cost, 5),
            "failure_mode": failure_mode}


def run_benchmark(agent, task_list=None, verbose=True) -> dict:
    task_list = task_list or TASKS
    results = []
    for t in task_list:
        r = run_task(agent, t)
        results.append(r)
        if verbose:
            mark = "PASS" if r["passed"] else f"FAIL({r['failure_mode']})"
            print(f"[{mark}] {r['task_id']} {r['title']} steps={r['steps']}")
    passed = sum(1 for r in results if r["passed"])
    return {"agent": getattr(agent, "name", type(agent).__name__),
            "pass_rate": round(passed / max(len(results), 1), 4),
            "passed": passed, "total": len(results), "results": results}
