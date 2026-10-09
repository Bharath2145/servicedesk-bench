"""Failure explorer dashboard: streamlit run dashboard/app.py"""
import json
import glob
import os

import streamlit as st

st.set_page_config(page_title="ServiceDeskBench Explorer", layout="wide")
st.title("ServiceDeskBench — failure explorer")
st.caption("Trajectories, verifiers & failure taxonomy for every run in results/*.json")

files = sorted(glob.glob("results/*.json"))
if not files:
    st.warning("No results yet. Run: python -m src.run_eval --agent all")
    st.stop()

agent = st.sidebar.selectbox("Agent", files)
with open(agent) as f:
    bench = json.load(f)

results = bench["results"]
pass_rate = sum(1 for r in results if r["passed"]) / len(results)
st.metric("Pass rate", f"{pass_rate*100:.1f}%", f"{sum(1 for r in results if r['passed'])}/{len(results)}")

fails = {}
for r in results:
    fails[r["failure_mode"]] = fails.get(r["failure_mode"], 0) + 1
st.bar_chart(fails)

flt = st.sidebar.selectbox("Filter", ["all", "passed", "failed"])
cat = st.sidebar.selectbox("Category", ["all"] + sorted({r["category"] for r in results}))
for r in results:
    if flt == "passed" and not r["passed"]:
        continue
    if flt == "failed" and r["passed"]:
        continue
    if cat != "all" and r["category"] != cat:
        continue
    icon = "✅" if r["passed"] else "❌"
    with st.expander(f"{icon} {r['task_id']} — {r['title']} [{r['failure_mode']}]"):
        st.write(f"Category: {r['category']} | Difficulty: L{r['difficulty']} | "
                 f"Steps: {r['steps']}/{r['gold_steps']} gold | Cost: ${r['cost_est_usd']}")
        st.json({"checks": r["checks"], "errors": r["errors"]})
        st.code("\n".join(f"{i+1}. {s['tool']}({s['args']}) -> ok={s['ok']}" for i, s in enumerate(r["trajectory"])))
