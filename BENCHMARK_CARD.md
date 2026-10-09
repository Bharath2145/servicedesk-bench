# Benchmark Card: ServiceDeskBench v1.0

## Objective
Measure whether autonomous agents can resolve enterprise service-desk requests
end-to-end across identity, devices, network, security, infra, and escalation.

## Construct
Task success = (world state correct) AND (ticket/records complete) AND (no policy violation).
Capabilities tested: tool discovery, precondition verification, multi-step execution,
refusal under adversarial pressure, correct escalation routing.

## Environment
In-memory mock of 5 systems: 6 users, 5 devices, 40 tickets, 6 KB articles, 3 network zones.
Deterministic seed; per-task setup mutations (e.g. empty device pool). Full audit log.

## Tasks
24 tasks: 6 categories × 4 each; difficulty L1 (7) / L2 (10) / L3 (7).
8 trap/refusal tasks (correct action = refuse or escalate, not execute).
Gold step counts recorded for step-efficiency.

## Evaluation
Protocol: agent gets prompt + `call_tool(name, args)`; max 12 steps; all calls logged.
Grading: pure Python state verifiers (no LLM judge in v1).
Metrics: pass@1 overall / per-category / per-difficulty, step efficiency
(gold/actual), est. tokens + cost, failure taxonomy distribution.

## Validity (ABC checklist mapping)
- Outcome validity: state checks + negative tests + side-effect completeness; oracle hits 100%.
- Task validity: solvable (oracle), non-trivial (heuristic 45.8%), isolated per-task env clones.
- Reporting: open harness, versioned tasks, trajectories + leaderboard committed in `results/`.

## Fairness
Same seed + tool list for every agent. Security traps punish shortcut-taking.
Difficulty calibration table in README. No hidden network or time dependence.

## Limitations
Mock scale (not 1,800 tables); offline baselines (LLM plug-in left as extension);
note-quality judged only by presence, not content (LLM rubric = future work).
