# ServiceDeskBench — a domain-specific benchmark for autonomous service agents

A **fully working, offline, reproducible benchmark** that measures whether AI agents can
do real enterprise service-desk work: resolve tickets *by changing systems correctly*,
not by writing plausible text.

Built as a portfolio project for **eval-centric AI engineering roles**
(benchmark design + eval tooling + failure analysis).

> Inspired by ITSMBench (Atomicwork × New Measure, Aug 2026: 42 mocked systems,
> 89 L2/L3 tasks, best model ≈ 50.6%) and the NeurIPS 2025 Agentic Benchmark
> Checklist (ABC) for outcome/task validity.

---

## Why this maps to the role

| Job bullet | How this project demonstrates it |
|---|---|
| Help experts build realistic tasks & environments | 5 mocked enterprise systems (ticketing, identity, devices, KB, network) + 24 tasks across 6 categories × 3 difficulty levels, each with setup + deterministic state verifier |
| Tooling for running evals & investigating failures | `src/harness.py` eval runner (trajectory log, cost/latency, timeouts) + Streamlit failure explorer + failure taxonomy classifier |
| Research fair & difficult benchmarks | Negative/trap tasks (MFA bypass, rogue prod-db grant, wipe guards), contamination-safe task IDs, difficulty calibration (L1 71% → L3 43% for weak baseline), oracle upper-bound proves solvability |

## Quickstart (60 seconds, no API key)

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v        # 12 tests, stdlib only
python -m src.run_eval --agent all --split all --judge --output results
python scripts/make_report.py                  # rebuild results/report.html
# open results/report.html in your browser (no server needed)
# optional UI: python -m streamlit run dashboard/app.py
```

## v2 extensions (done)

- **LLM plug-in** (`src/llm.py`, `src/llm_agent.py`): `--agent llm` runs a real
  ReAct loop against any OpenAI-compatible endpoint
  (`OPENAI_API_KEY` / `OPENAI_BASE_URL` / `EVAL_MODEL`). Without a key it falls
  back to the deterministic policy, so evals stay reproducible offline.
- **Note-quality judge** (`src/judge.py`): `--judge` scores every ticket record
  0–2 (generic vs policy-grounded). Heuristic by default, LLM re-score when a
  key is set. React/oracle average 2.0/2; heuristic 1.0/2 on held-out.
- **Held-out + mutation splits** (`src/splits.py`): `--split public|heldout|mutated`.
  75/25 hash split + paraphrase variants (verifiers untouched). Heuristic holds
  at 45.8% on mutated (robust) with honest small-split variance on held-out
  (80%, 95% CI [40%,100%]).
- **Stats** (`src/stats.py`): seed-fixed bootstrap 95% CIs + $/task Pareto
  printed on every run (e.g. heuristic 45.8% CI [25%,67%], $0.0028/task).

## Results (reproduced on this machine)

```
agent | pass_rate | L1 | L2 | L3 | eff | cost($) | top_failure
react-mock | 100.0% | 100% | 100% | 100% | 0.614 | 0.1018 | -
oracle     | 100.0% | 100% | 100% | 100% | 0.614 | 0.1018 | -
heuristic  | 45.8%  | 71%  | 30%  | 43%  | 0.78  | 0.0664 | early_stop
```

Key finding (mirrors ITSMBench): the weak agent's dominant failure is **`early_stop`** —
closing the ticket after a plausible step while leaving systems/records incomplete.
Security guards (MFA, wipe-confirm, approval notes) catch bypass attempts as scored
`permission_violation`s instead of crashing the harness.

## Layout

```
src/env.py       mocked enterprise world (seed, audit log)
src/tools.py     13 tools, read/write split, precondition guards
src/tasks.py     24 tasks + state-based verifiers + per-task setup
src/harness.py   deterministic runner, trajectory/cost logging
src/agents.py    heuristic / react-mock / oracle baselines (offline)
src/metrics.py   pass@1, per-category/difficulty, step-efficiency, tool stats, failure taxonomy
src/run_eval.py  CLI
dashboard/app.py Streamlit trajectory + failure explorer
tests/           validity tests (guards, solvability, headroom)
results/         generated JSON + leaderboard
BENCHMARK_CARD.md  design card (ABC compliance, fairness, limitations)
```

## Fairness & rigor notes

- **State-based grading, never string match.** Verifiers inspect DB/ticket/audit state.
- **Side-effect completeness required.** Fixing state but not updating the ticket fails
  (`incomplete_side_effect`) — the exact ITSMBench failure pattern.
- **Trap tasks:** 8/24 are refusal/escalation tasks where the right answer is to *not act*.
- **Anti-contamination:** task prompts carry no answers; verifiers are hidden from agents;
  only tool outputs are visible.
- **Difficulty labels:** L1 = single-system lookup+record, L2 = multi-step with guard,
  L3 = ambiguous/adversarial needing triage + escalation.
- **Limitations (honest):** offline mock (no real LLM in baselines — plug yours via
  `BaseAgent.run`), 24 tasks (sample; harness scales to 100+), cost is estimated.

## Plug in your own LLM agent (interview extension)

```python
from src.agents import AGENTS
class MyLLMAgent:
    name = "my-llm"
    def run(self, task, call):
        # ReAct loop with your model; call(name, args) executes tools
        ...
# python -m src.run_eval --agent ...  (register in AGENTS)
```

## What I'd do next (roadmap for interview)

1. LLM-as-judge rubric for note *quality* alongside deterministic state checks.
2. Held-out private split + task mutation generator to fight overfitting.
3. Bootstrap CIs + cost-vs-accuracy Pareto frontier per model/harness.
