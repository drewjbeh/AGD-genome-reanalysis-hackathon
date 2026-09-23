# Challenge 4 — Reanalysis triage: method (frozen)

Built under a blind protocol: only `synthetic_reanalysis_cases.tsv` and the data dictionary were used.
The outcomes file was never opened. Reproduce with `python triage.py <cases.tsv> <outdir>`.

## 1. Question and design principle
"Which cases should we review first, and why?" — a weighted-signal scheme, hand-built from clinical reasoning,
where every point is attributable to a named signal that is echoed back in the per-case `reason` string.

    score = recency_multiplier × (evidence points + incomplete-prior points) + time points + context points
    (× 0.9 if partially_solved; set to 0 and tier "Skip" if solved at cycle start)

## 2. Signals and weights (points)

| Signal | Weight | Cap | Clinical justification |
|---|---|---|---|
| `clinvar_upgrades_to_plp` | **40 / variant** | 2 | A variant already in the case reclassified to P/LP is close to actionable; the single strongest predictor of a solve on review. |
| `new_high_priority_candidates` | **25 / candidate** | 2 | Candidate now in a high-confidence tier (new or promoted): one analyst look may resolve it. |
| `new_gene_evidence` | 12 / candidate | 3 | Strengthened gene–disease association (e.g. new GenCC/ClinGen validity) turns a VUS-in-candidate-gene into a reportable finding more often than not. |
| other ClinVar reclassification (`new_clinvar_evidence` − `clinvar_upgrades_to_plp`) | 5 / variant | 4 | "Any reclassification" includes downgrades and VUS shuffles — worth a look, rarely decisive. |
| `phenotype_changes` (new HPO terms) | 6 / term | 5 | New phenotype re-ranks candidate genes; several new terms can flip the prioritisation. |
| `new_candidates` | 3 / candidate | 4 | The most obvious column, deliberately weak: raw candidate volume is mostly pipeline noise unless a candidate is also high-priority or has new evidence. |
| Note events (see §4) | 10–30 | — | Information found in no structured column. |
| `prior_analysis_complete = 0` | 10 base + flag | — | An analysis that never finished cannot have exhausted the data. |
| flag `partial_panel` / `pipeline_error` | +10 each | — | Genes never examined / unreliable output → high chance of a missed finding. |
| flag `qc_fail` / `no_parental_data` | +5 each | — | QC failures may need re-sequencing rather than reanalysis; missing parents is now often corrected (see notes). |
| `prior_analysis_complete = NA` | +5 | — | Completeness not demonstrated; do not assume it was complete. |
| time since `last_analysis` | 4 / year | 5 y (20 pts) | Annotation, ClinVar and gene-disease knowledge accrue over time; a modest additive term, so time alone cannot outrank real evidence. |
| `family_structure` trio / duo | +4 / +2 | — | Inheritance-aware filtering raises reanalysis yield. |
| `sequencing_type` genome | +3 | — | Re-annotation gains (SV, non-coding, mitochondrial) accrue mainly to genomes. |

Not scored: `hpo_term_count` (phenotype depth is not a change signal), `candidate_count` (volume, not quality),
`first_analysis` (196/300 cases have `first_analysis == last_analysis`; adds nothing beyond `last_analysis`).

## 3. Interaction: recency dampener
New evidence only matters if the previous analysis is old enough to have missed it, and a case reviewed weeks ago
is unlikely to benefit regardless of its numbers. Evidence and incomplete-prior points are multiplied by:

| years since last analysis | multiplier |
|---|---|
| < 0.25 (≈ 3 months) | 0.20 |
| 0.25 – 0.5 | 0.50 |
| 0.5 – 1.0 | 0.80 |
| ≥ 1.0 | 1.00 |

Consequence (documented, deliberate): CASE_106 (second affected sibling, new high-priority candidate, 4 new HPO terms,
but analysed 0.04 y ago) lands in Defer. Cases with a clinical-event note but a very recent analysis should be
handled by a clinician-directed manual check, not consume an automated reanalysis slot.

## 4. Free-text `note` handling
All 23 distinct note values were read. 13 are administrative (blank, "routine", "internal cohort", "reviewed at MDT",
"external referral", "referred from …", "consanguineous family", "no family history reported", "prenatal history
unremarkable", "annual review", "part of research cohort", "sample received from external lab") and score 0.
10 record real events absent from every structured column:

| note | points | why |
|---|---|---|
| parents now consented and sequenced; trio data available | 30 | All 4 such cases still read `family_structure = singleton` (structure is "at last analysis"). Singleton → trio is the largest single yield gain in reanalysis (de novo / inheritance filtering). |
| matchmaker exchange match reported by external centre | 30 | An independent patient with the same candidate gene is often the decisive evidence for a novel gene. |
| research collaboration reported a second family with a variant in the same gene | 30 | Same logic as MME match. |
| second affected sibling now presenting with overlapping features | 25 | Segregation analysis becomes possible; phenotype of sibling adds terms. |
| skin fibroblast RNA study completed | 20 | Functional (splicing/expression) evidence can reclassify a VUS. |
| muscle biopsy results now available | 15 | New tissue-level phenotype / functional evidence. |
| deep phenotyping completed at specialist clinic | 15 | Richer HPO profile re-ranks candidates (may not yet be reflected in `phenotype_changes`). |
| clinician requested review following new MRI findings | 15 | New imaging phenotype + explicit clinical demand. |
| clinician requested review ahead of family planning | 15 | Time-sensitive clinical need (reproductive decision). |
| new consanguinity information provided by family | 10 | Changes the inheritance model (favours homozygous recessive filtering). |

## 5. Missing-value rules (no row is dropped)
| column | NA count | rule |
|---|---|---|
| `hpo_term_count` | 5 | Not scored; left NA; noted in `reason`. |
| `phenotype_changes` | 7 | Treated as 0 (no demonstrated change); appended "phenotype_changes=NA treated as 0" to `reason`. |
| `new_gene_evidence` | 2 | Treated as 0; flagged in `reason`. |
| `prior_analysis_complete` | 4 | Treated as *unknown*, not complete: +5 points; flagged in `reason`. |
Evidence NA → 0 is conservative (absence of evidence), so an NA can never push a case up on its own; the flag in the reason
lets an analyst spot the gap.

## 6. Case status
* `solved` (14 cases): score set to 0, tier "Skip - already solved", ranked last (ordered by would-be score, which is shown
  in the reason for auditability). They must not consume review slots.
* `partially_solved` (25): kept in play (second diagnosis / unexplained phenotype) with a ×0.9 multiplier.
* `unsolved` (261): full score.

## 7. Tiers
* **Review now** — score ≥ 50 AND at least one strong signal (P/LP upgrade, new high-priority candidate, or a ≥25-point
  note event) AND last analysis ≥ 0.5 y ago. (46 cases)
* **Review this cycle** — score ≥ 30, otherwise. (70 cases)
* **Defer** — score < 30. (170 cases)
* **Skip - already solved** — case_status = solved. (14 cases)

## 8. Tie-break rule (exact)
Sort by: solved-flag ascending → `score` descending → would-be score descending (only distinguishes solved cases) →
`years_since_last` descending → `case_id` ascending. `rank` = 1..300 in that order.

## 9. Baseline
`baseline_oldest_first.csv`: all 300 cases sorted by `last_analysis` ascending, ties by `case_id` ascending, nothing excluded.

## 10. Output columns (`triage_ranking.csv`)
rank, case_id, tier, score, reason, case_status, years_since_last, last_analysis, sequencing_type, family_structure,
hpo_term_count, phenotype_changes, candidate_count, new_candidates, new_high_priority_candidates, new_gene_evidence,
new_clinvar_evidence, clinvar_upgrades_to_plp, prior_analysis_complete, prior_analysis_flag, note, plus the score
components (evidence_points, recency_multiplier, time_points, context_points, note_points).
