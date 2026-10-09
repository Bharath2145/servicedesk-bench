"""Public / held-out splits + prompt-mutation generator (anti-overfitting).

- Deterministic 75/25 split by task-id hash: 18 public, 6 held-out.
  Report on public, confirm on held-out. Prevents tuning to the test set.
- mutate(task, seed): paraphrase-only variant (prompt prefix rotation).
  Ticket ids and verifiers are untouched, so variants stay solvable and
  fairly graded — run with --split mutated for a robustness check.
"""
from __future__ import annotations

import hashlib

PREFIXES = [
    "URGENT — please handle: ",
    "Follow-up request: ",
    "Ticket update needed — ",
    "On behalf of the requester: ",
]


def split_of(task_id: str) -> str:
    h = int(hashlib.sha256(task_id.encode()).hexdigest(), 16)
    return "heldout" if h % 4 == 0 else "public"


def get_split(tasks, split="all"):
    assert split in ("all", "public", "heldout", "mutated")
    if split == "all":
        return list(tasks)
    if split == "mutated":
        return [mutate(t, i) for i, t in enumerate(tasks)]
    return [t for t in tasks if split_of(t["id"]) == split]


def mutate(task, seed: int) -> dict:
    t = dict(task)
    t["id"] = f"{task['id']}+m{seed % len(PREFIXES)}"
    t["prompt"] = PREFIXES[seed % len(PREFIXES)] + task["prompt"]
    return t


def describe(tasks) -> dict:
    counts = {"public": 0, "heldout": 0}
    for t in tasks:
        counts[split_of(t["id"])] += 1
    return counts
