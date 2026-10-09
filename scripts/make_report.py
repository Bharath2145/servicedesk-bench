"""Static HTML report — zero dependencies, just double-click results/report.html."""
import json
import glob
import os
import html

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, "results")


def load():
    benches = []
    for f in sorted(glob.glob(os.path.join(RES, "*.json"))):
        with open(f) as fh:
            benches.append((os.path.basename(f), json.load(fh)))
    return benches


def card(r):
    icon = "✅" if r["passed"] else "❌"
    nq = r.get("note_quality")
    nq_str = f" · notes {nq['score']}/2 ({nq['method']})" if nq else ""
    traj = "".join(
        f"<li><code>{html.escape(s['tool'])}({html.escape(str(s['args']))})</code> → ok={s['ok']} <span class=lat>{s['latency_ms']}ms</span><br><span class=out>{html.escape(s['output'][:300])}</span></li>"
        for s in r["trajectory"]
    )
    errs = "".join(f"<li>{html.escape(e)}</li>" for e in r["errors"]) or "<li>none</li>"
    checks = "".join(f"<li>{html.escape(k)}: <b>{v}</b></li>" for k, v in r["checks"].items())
    return f"""
<details class="{'pass' if r['passed'] else 'fail'}">
<summary>{icon} <b>{html.escape(r['task_id'])}</b> — {html.escape(r['title'])}
<span class=tag>{html.escape(r['category'])} · L{r['difficulty']} · {html.escape(r['failure_mode'])} · {r['steps']} steps · ${r['cost_est_usd']}{html.escape(nq_str)}</span></summary>
<div class=cols><div><h4>Verifier checks</h4><ul>{checks}</ul><h4>Errors</h4><ul>{errs}</ul></div>
<div><h4>Trajectory</h4><ol>{traj}</ol></div></div>
</details>"""


def main():
    benches = load()
    assert benches, "no results/*.json — run: python -m src.run_eval --agent all"
    sections = []
    rows = []
    for fname, b in benches:
        pr = sum(1 for r in b["results"] if r["passed"]) / len(b["results"]) * 100
        rows.append(f"<tr><td>{html.escape(b['agent'])}</td><td>{pr:.1f}%</td><td>{sum(1 for r in b['results'] if r['passed'])}/{len(b['results'])}</td><td>{html.escape(fname)}</td></tr>")
    for fname, b in benches:
        pr = sum(1 for r in b["results"] if r["passed"]) / len(b["results"]) * 100
        ci = b.get("pass_ci95")
        ci_str = f" · 95% CI [{ci[0]*100:.0f}–{ci[1]*100:.0f}%]" if ci else ""
        nqa = b.get("note_quality_avg")
        nq_str = f" · notes {nqa}/2" if nqa is not None else ""
        split = b.get("split", "?")
        fails = {}
        for r in b["results"]:
            fails[r["failure_mode"]] = fails.get(r["failure_mode"], 0) + 1
        failstr = ", ".join(f"{k}: {v}" for k, v in sorted(fails.items(), key=lambda x: -x[1]))
        sections.append(f"<h2>Agent: {html.escape(b['agent'])} — {pr:.1f}% <span class=tag>{html.escape(fname)} · split={html.escape(str(split))}{html.escape(ci_str)}{html.escape(nq_str)} · failures: {html.escape(failstr)}</span></h2>")
        sections.extend(card(r) for r in b["results"])
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>ServiceDeskBench Report</title>
<style>body{{font-family:Segoe UI,Arial;margin:32px;max-width:1100px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:8px}}th{{background:#f0f0f0}}details{{border:1px solid #ddd;border-radius:8px;margin:8px 0;padding:8px}}details.pass{{border-left:6px solid #2da44e}}details.fail{{border-left:6px solid #cf222e}}.tag{{color:#666;font-size:12px}}.cols{{display:grid;grid-template-columns:1fr 2fr;gap:16px}}code{{background:#f6f8fa;padding:2px 4px}}.lat{{color:#888;font-size:11px}}.out{{color:#555;font-size:12px}}h1 small{{color:#666}}</style>
</head><body>
<h1>ServiceDeskBench Report <small>— open this file, no server needed</small></h1>
<p>24 deterministic tasks · 5 mocked enterprise systems · state-based verifiers. Regenerate: <code>python -m src.run_eval --agent all</code> then <code>python scripts/make_report.py</code></p>
<h2>Leaderboard</h2><table><tr><th>agent</th><th>pass rate</th><th>score</th><th>file</th></tr>{''.join(rows)}</table>
{''.join(sections)}
</body></html>"""
    out = os.path.join(RES, "report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
