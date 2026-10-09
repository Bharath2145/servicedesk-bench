"""CLI: python -m src.run_eval --agent all --split all --judge --output results/

Extensions (v2):
  --agent llm      LLM-backed ReAct (needs OPENAI_API_KEY; else offline fallback)
  --split          all | public | heldout | mutated  (anti-overfitting)
  --judge          score ticket-note quality 0-2 per task (heuristic, or LLM w/ key)
  CIs + $/task are always reported (bootstrap, seed-fixed, reproducible).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents import AGENTS
from src.llm_agent import LLMAgent
from src.harness import run_benchmark
from src.metrics import summarize, leaderboard_text
from src.splits import get_split, describe
from src.stats import bootstrap_ci, pareto_row
from src.judge import score_from_trajectory
from src.tasks import TASKS

AGENTS["llm"] = LLMAgent


def main():
    ap = argparse.ArgumentParser(description="ServiceDeskBench eval runner")
    ap.add_argument("--agent", default="all", choices=[*AGENTS, "all"])
    ap.add_argument("--split", default="all", choices=["all", "public", "heldout", "mutated"])
    ap.add_argument("--judge", action="store_true", help="score note quality 0-2")
    ap.add_argument("--output", default="results")
    args = ap.parse_args()

    tasks = get_split(TASKS, args.split)
    print(f"split={args.split} n={len(tasks)} ({describe(TASKS)})")
    os.makedirs(args.output, exist_ok=True)
    names = list(AGENTS) if args.agent == "all" else [args.agent]
    summaries = []
    for n in names:
        print(f"\n=== {n} ===")
        bench = run_benchmark(AGENTS[n](), task_list=tasks)
        if args.judge:
            for r, t in zip(bench["results"], tasks):
                r["note_quality"] = score_from_trajectory(t, r["trajectory"])
            avg = sum(r["note_quality"]["score"] for r in bench["results"]) / max(len(bench["results"]), 1)
            bench["note_quality_avg"] = round(avg, 3)
        lo, hi, _ = bootstrap_ci([r["passed"] for r in bench["results"]])
        bench["pass_ci95"] = [lo, hi]
        bench["split"] = args.split
        summ = summarize(bench)
        summ["pass_ci95"] = [lo, hi]
        summ["usd_per_task"] = pareto_row(summ)["usd_per_task"]
        if args.judge:
            summ["note_quality_avg"] = bench["note_quality_avg"]
        summaries.append(summ)
        tag = f"{n}_{args.split}" if args.split != "all" else n
        with open(os.path.join(args.output, f"{tag}.json"), "w") as f:
            json.dump(bench, f, indent=2, default=str)
        extra = f" ci95=[{lo*100:.0f}%,{hi*100:.0f}%] ${summ['usd_per_task']}/task"
        if args.judge:
            extra += f" notes={summ['note_quality_avg']}/2"
        print(f"pass_rate={summ['pass_rate']*100:.1f}% "
              f"({summ['passed']}/{summ['total']}) eff={summ['mean_step_efficiency']} "
              f"cost=${summ['total_cost_usd']}" + extra)
    print("\n=== LEADERBOARD ===")
    print(leaderboard_text(summaries))
    with open(os.path.join(args.output, "leaderboard.md"), "w") as f:
        f.write("# ServiceDeskBench Leaderboard\n\n" + leaderboard_text(summaries) + "\n")


if __name__ == "__main__":
    main()
