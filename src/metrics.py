"""Metrics + failure taxonomy + fairness/difficulty reporting.

Failure modes (inspired by ITSMBench findings):
  success | early_stop | incomplete_side_effect | permission_violation |
  wrong_team | no_tool_called | max_steps_exceeded | hallucinated_tool |
  state_not_fixed | agent_crash
"""
from __future__ import annotations

from collections import Counter


def classify_failure(passed, trajectory, errors, env, task_def) -> str:
    if passed:
        return "success"
    joined_err = " ".join(errors).lower()
    tool_names = [s["tool"] for s in trajectory]
    if any("agent_crash" in e for e in errors):
        return "agent_crash"
    if any("unknown tool" in e for e in errors):
        return "hallucinated_tool"
    if any("mfa" in e or "confirmed" in e or "approval" in e or "permission" in joined_err for e in [joined_err]):
        # permission error AND task still failed -> agent didn't recover
        return "permission_violation"
    if not trajectory:
        return "no_tool_called"
    if len(trajectory) >= 12:
        return "max_steps_exceeded"
    checks = task_def["verify"](env, trajectory)[1]
    # state fixed but ticket/records incomplete -> classic ITSM failure
    state_keys = [k for k in checks if k not in ("ticket_done",)]
    if state_keys and all(checks.get(k) for k in state_keys) and not checks.get("ticket_done", True):
        return "incomplete_side_effect"
    # ticket closed but world not fixed -> stopped after plausible answer
    tid = task_def["ticket_id"]
    try:
        closed = env.tickets[tid]["status"] in ("resolved", "closed")
    except KeyError:
        closed = False
    if closed:
        return "early_stop"
    if any("escalat" in t for t in tool_names):
        return "wrong_team"
    return "state_not_fixed"


def summarize(bench: dict) -> dict:
    results = bench["results"]
    by_cat, by_diff, by_fail = {}, {}, Counter()
    for r in results:
        by_cat.setdefault(r["category"], []).append(r["passed"])
        by_diff.setdefault(str(r["difficulty"]), []).append(r["passed"])
        by_fail[r["failure_mode"]] += 1
    eff = [r["gold_steps"] / max(r["steps"], 1) for r in results if r["passed"]]
    return {
        "agent": bench["agent"],
        "pass_rate": bench["pass_rate"],
        "passed": bench["passed"], "total": bench["total"],
        "by_category": {k: round(sum(v) / len(v), 3) for k, v in by_cat.items()},
        "by_difficulty": {k: round(sum(v) / len(v), 3) for k, v in by_diff.items()},
        "failures": dict(by_fail),
        "mean_step_efficiency": round(sum(eff) / max(len(eff), 1), 3),
        "total_cost_usd": round(sum(r["cost_est_usd"] for r in results), 4),
        "total_tokens_est": sum(r["tokens_est"] for r in results),
    }


def leaderboard_text(summaries: list[dict]) -> str:
    lines = ["agent | pass_rate | L1 | L2 | L3 | eff | cost($) | top_failure",
             "---|---|---|---|---|---|---|---"]
    for s in sorted(summaries, key=lambda x: -x["pass_rate"]):
        bd = s["by_difficulty"]
        fails = sorted(s["failures"].items(), key=lambda x: -x[1])
        top = fails[0][0] if fails and fails[0][0] != "success" else "-"
        if fails and fails[0][0] == "success" and len(fails) > 1:
            top = fails[1][0]
        lines.append(f"{s['agent']} | {s['pass_rate']*100:.1f}% | "
                     f"{bd.get('1',0)*100:.0f}% | {bd.get('2',0)*100:.0f}% | {bd.get('3',0)*100:.0f}% | "
                     f"{s['mean_step_efficiency']} | {s['total_cost_usd']} | {top}")
    return "\n".join(lines)
