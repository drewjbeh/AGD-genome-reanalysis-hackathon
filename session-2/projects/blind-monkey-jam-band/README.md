# Blind Monkey Jam Band — Challenge 4: Reanalysis triage

**Question:** a laboratory has hundreds of unresolved genomes after a reanalysis cycle. Which cases should a scientist review first, and why?

**Answer:** a transparent, hand-weighted triage that ranks all 300 cases, assigns each a tier and a plain-language reason, and — evaluated blind — puts **13 solved cases in its top 20** (oldest-first baseline: 3; random: ~2).

## Who opens this, and when

A clinical scientist on the morning after the automated reanalysis cycle completes, with time to look at perhaps 20 cases before the MDT. They open `triage_view.html`, filter to *Review now*, and read the reason column.

## The blind protocol (how we kept it honest)

The challenge ships `synthetic_reanalysis_outcomes.tsv` for evaluation only. Our first inspection of the data accidentally printed a few aggregate numbers from it. To make the result trustworthy we:

1. sealed the outcomes file in a zip and deleted the plain-text copy;
2. had a **separate agent in a fresh context** — which received only the case table, the data dictionary and the challenge text — design and freeze the ranking;
3. opened the outcomes only after `triage_ranking.csv` was saved.

The exact leakage and its scope are recorded in `evaluation.md`. The ranking agent saw none of it.

## How the scheme works (weights stated up front, details in `triage_method.md`)

| Signal | Points | Why |
|---|---:|---|
| ClinVar upgrade to P/LP | 40 per variant (cap 2) | closest to actionable |
| New high-priority candidate | 25 (cap 2) | Talos itself promoted it |
| Strengthened gene–disease evidence | 12 (cap 3) | |
| New HPO term | 6 (cap 5) | phenotype may now match |
| Other ClinVar reclassification | 5 (cap 4) | |
| Raw new candidate | 3 (cap 4) | *volume is not quality* |
| Note event (trio now available, Matchmaker match, second family, second sibling, biopsy/RNA, deep phenotyping, clinician request) | 10–30 | found only in free text |
| Prior analysis incomplete | 10 + 5–10 by flag | |
| Time since last analysis | 4 / year, cap 20 | age alone cannot outrank evidence |
| Recency dampener on evidence | ×0.2 <3 mo, ×0.5 <6 mo, ×0.8 <1 y | a recent analysis already saw it |

Already-solved cases score 0 and are tiered *Skip*. No rows dropped: missing evidence counts → 0 and flagged in the reason; missing `prior_analysis_complete` → unknown (+5), not complete.

## Result (see `evaluation.md`)

| Top k | Triage solved | Oldest-first solved |
|---:|---:|---:|
| 10 | 9 | 1 |
| 20 | **13** | 3 |
| 50 | 24 | 8 |

Tier calibration: *Review now* (46 cases) holds 21 of 29 solved; *Defer* (170) holds 2.

**What it got wrong:** a solved case whose only signal was a "second affected sibling" note sank to rank 108; two solved cases analysed 9–11 months earlier were over-dampened (ranks 75, 117). Both are single weight adjustments.

## Run it

```bash
python triage.py ../../data/synthetic_reanalysis_cases.tsv .        # -> triage_ranking.csv, baseline_oldest_first.csv
python make_html_view.py triage_ranking.csv triage_view.html        # -> the review page
```

## Files

- `triage.py` — the ranking, reproducible from the case table
- `triage_method.md` — weights, missing-value rules, note handling, tie-break
- `triage_ranking.csv` — frozen output, 300 cases with tier, score, reason
- `baseline_oldest_first.csv` — the comparison ranking
- `make_html_view.py`, `triage_view.html`, `screenshot_triage_view.png` — the review page
- `evaluation.md`, `top20_evaluated.csv` — scoring against outcomes, with leakage disclosure
- `presentation.pdf` — the five-slide deck

## Working with Claude

The agent-built ranking is a hand-weighted scheme, not a model fitted to outcomes. Things caught in review: an earlier inspection cell leaked outcome aggregates (fixed by the blind protocol above); the sub-agent's `years_since_last` and note weights were checked against the source rows before the evaluation was accepted.

All data is synthetic and must not be presented as clinical evidence.
