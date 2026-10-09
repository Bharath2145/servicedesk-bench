"""Bootstrap confidence intervals + cost/accuracy Pareto (stdlib only)."""
from __future__ import annotations

import random


def bootstrap_ci(passed: list[bool], n_boot=2000, ci=0.95, seed=7):
    """Percentile CI for a pass rate. Deterministic via fixed seed."""
    rng = random.Random(seed)
    n = len(passed)
    if n == 0:
        return (0.0, 0.0)
    base = sum(passed) / n
    dist = []
    for _ in range(n_boot):
        sample = [passed[rng.randrange(n)] for _ in range(n)]
        dist.append(sum(sample) / n)
    dist.sort()
    lo_q = (1 - ci) / 2
    lo = dist[int(lo_q * n_boot)]
    hi = dist[min(int((1 - lo_q) * n_boot), n_boot - 1)]
    return (round(lo, 4), round(hi, 4), round(base, 4))


def pareto_row(summary: dict) -> dict:
    return {"agent": summary["agent"], "pass_rate": summary["pass_rate"],
            "cost_usd": summary["total_cost_usd"],
            "tokens": summary["total_tokens_est"],
            "usd_per_task": round(summary["total_cost_usd"] / max(summary["total"], 1), 5)}
