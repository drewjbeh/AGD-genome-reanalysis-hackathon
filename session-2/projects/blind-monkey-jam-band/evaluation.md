# Reanalysis triage — blind evaluation

**Protocol.** The ranking was built by a sub-agent in a fresh context that received only the 300-case table, the data dictionary and the challenge brief. It never had access to the outcomes file. The ranking was frozen (`triage_ranking.csv`) before the outcomes zip was opened by the evaluator. The sub-agent declared no deviations from its brief.

**Leakage disclosure (evaluator side only).** Before the blind protocol was adopted, the evaluating agent had already printed from the outcomes file: the outcome distribution (29 solved / 41 follow-up / 216 no change / 14 already solved), the first three rows (CASE_001 no_change; CASE_002 candidate_for_followup; CASE_003 solved, RYR1), and solved rates split by `clinvar_upgrades_to_plp > 0` (65% vs 6%) and `new_high_priority_candidates > 0` (38% vs 5%). None of this was passed to the sub-agent that built the ranking.

## Headline result

| Top k | Triage: solved / follow-up / already-solved | Oldest-first baseline: solved / follow-up / already-solved |
|---:|---|---|
| 10 | **9** / 1 / 0 | 1 / 2 / 2 |
| 20 | **13** / 4 / 0 | 3 / 4 / 2 |
| 30 | **17** / 4 / 0 | 4 / 5 / 3 |
| 50 | **24** / 8 / 0 | 8 / 8 / 3 |
| 100 | **26** / 12 / 0 | 17 / 13 / 7 |

29 of 300 cases were solved in total; random expectation in a top-20 is 1.9. The baseline wastes 2 of its first 20 slots on cases already solved at cycle start; the triage skips all 14 of those.

## Tier calibration

| Tier | n | solved | follow-up | no change | already solved |
|---|---:|---:|---:|---:|---:|
| Review now | 46 | 21 | 9 | 16 | 0 |
| Review this cycle | 70 | 6 | 4 | 60 | 0 |
| Defer | 170 | 2 | 28 | 140 | 0 |
| Skip – already solved | 14 | 0 | 0 | 0 | 14 |

## Misses worth noting

False positives in the top 20 (all `no_change`): CASE_256 (rank 12; strengthened gene evidence ×2, 5 new HPO terms, 5.4 y), CASE_134 (rank 16; 1 ClinVar P/LP upgrade, 6.2 y), CASE_064 (rank 18; 2 new high-priority candidates, 4.2 y). These are exactly the profiles a lab would want to look at; the scheme is not wrong to surface them.

Solved cases ranked deepest: CASE_183 (rank 108, CHD8) — only signal was the note "second affected sibling", scored 25 but not enough to reach the top without structured evidence. CASE_122 (rank 117, ANKRD11) and CASE_200 (rank 75, TTN) were dampened by the recency multiplier (last analysed <1 y). CASE_031 (rank 153, NEB) had only one strengthened gene-evidence signal and was `partially_solved`. Possible refinements: raise the weight of the sibling/segregation note, and soften the recency dampener between 0.5–1 y when structured evidence is present.

## Files
- triage_ranking.csv — frozen 300-case ranking with tier, score, reason
- triage_method.md — weights, missing-value and note-handling rules, tie-break
- triage.py — reproduces the ranking
- baseline_oldest_first.csv — comparison ranking
- top20_evaluated.csv — top 20 joined to outcomes
