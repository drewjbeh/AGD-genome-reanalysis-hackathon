#!/usr/bin/env python3
"""make_html_view.py — render triage_ranking.csv as a self-contained HTML triage view.
Usage: python make_html_view.py triage_ranking.csv triage_view.html
Presentation only: every value shown comes from triage_ranking.csv (produced by triage.py)."""
import sys, html
import pandas as pd

TIER_COLOR = {"Review now": "#b91c1c", "Review this cycle": "#b45309", "Defer": "#4b5563", "Skip - already solved": "#9ca3af"}

def main(inp, out):
    df = pd.read_csv(inp).sort_values("rank")
    counts = df["tier"].value_counts().to_dict()
    rows = []
    for _, r in df.iterrows():
        sig = []
        for col, lab in [("clinvar_upgrades_to_plp", "ClinVar P/LP"), ("new_high_priority_candidates", "new high-priority"),
                         ("new_gene_evidence", "gene evidence"), ("phenotype_changes", "new HPO"), ("new_candidates", "new cand.")]:
            v = r[col]
            if pd.notna(v) and v > 0:
                sig.append(f"<span class='chip'>{lab} {int(v)}</span>")
        if r["prior_analysis_complete"] != 1:
            sig.append(f"<span class='chip warn'>prior incomplete{'' if pd.isna(r['prior_analysis_flag']) else ': ' + html.escape(str(r['prior_analysis_flag']))}</span>")
        if r["note_points"] > 0:
            sig.append("<span class='chip note'>note event</span>")
        tier = r["tier"]; color = TIER_COLOR.get(tier, "#333")
        rows.append(f"<tr data-tier='{html.escape(tier)}'><td>{int(r['rank'])}</td><td class='id'>{r['case_id']}</td>"
                    f"<td><span class='tier' style='background:{color}'>{html.escape(tier)}</span></td>"
                    f"<td class='num'>{r['score']:.1f}</td><td class='num'>{r['years_since_last']:.1f}</td>"
                    f"<td>{' '.join(sig)}</td><td class='reason'>{html.escape(str(r['reason']))}</td></tr>")
    tier_buttons = "".join(f"<button onclick=\"filt('{html.escape(t)}')\">{html.escape(t)} ({counts.get(t,0)})</button>"
                           for t in ["Review now", "Review this cycle", "Defer", "Skip - already solved"])
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>Reanalysis triage — {len(df)} cases</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;margin:24px;color:#111}} h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:#555;font-size:13px;margin-bottom:12px}} button{{margin:0 6px 10px 0;padding:6px 10px;border:1px solid #bbb;background:#f6f6f6;border-radius:4px;cursor:pointer}}
button.on{{background:#111;color:#fff;border-color:#111}} input{{padding:6px;width:220px;margin-left:10px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid #e5e7eb;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f3f4f6;position:sticky;top:0}} td.num{{text-align:right;font-variant-numeric:tabular-nums}} td.id{{font-family:monospace}}
.tier{{color:#fff;padding:2px 7px;border-radius:10px;font-size:12px;white-space:nowrap}}
.chip{{display:inline-block;background:#e0e7ff;color:#1e3a8a;border-radius:4px;padding:1px 6px;font-size:11px;margin:1px 2px 1px 0;white-space:nowrap}}
.chip.warn{{background:#fef3c7;color:#92400e}} .chip.note{{background:#dcfce7;color:#14532d}} td.reason{{color:#333;max-width:520px}}
</style></head><body>
<h1>Reanalysis triage — which cases to review first, and why</h1>
<div class='sub'>{len(df)} cases from the cycle dated 2026-09-01. Ranking from <code>triage.py</code> (weights in <code>triage_method.md</code>). Cases already solved at cycle start are skipped. Synthetic data — not clinical evidence.</div>
<div><button class='on' onclick="filt('all')">All ({len(df)})</button>{tier_buttons}<input id='q' placeholder='search case id / reason' oninput='search()'></div>
<table><thead><tr><th>#</th><th>Case</th><th>Tier</th><th>Score</th><th>Years since last</th><th>Signals</th><th>Why this rank</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<script>
let cur='all';
function filt(t){{cur=t;document.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.textContent.startsWith(t==='all'?'All':t)));apply();}}
function search(){{apply();}}
function apply(){{const q=document.getElementById('q').value.toLowerCase();document.querySelectorAll('tbody tr').forEach(tr=>{{const ok=(cur==='all'||tr.dataset.tier===cur)&&(!q||tr.textContent.toLowerCase().includes(q));tr.style.display=ok?'':'none';}});}}
</script></body></html>"""
    open(out, "w").write(page)
    print(f"wrote {out}: {len(df)} rows, tiers {counts}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "triage_view.html")
