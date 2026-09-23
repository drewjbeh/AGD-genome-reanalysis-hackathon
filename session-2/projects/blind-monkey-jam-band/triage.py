#!/usr/bin/env python3
"""triage.py — transparent reanalysis triage for Challenge 4 (blind: uses ONLY the case table).

Usage: python triage.py <synthetic_reanalysis_cases.tsv> [outdir]
Writes triage_ranking.csv and baseline_oldest_first.csv to outdir (default '.').
"""
import sys, os
import pandas as pd
import numpy as np

# ----------------------------------------------------------------------------
# WEIGHTS (points). Stated up front; justification in triage_method.md
# ----------------------------------------------------------------------------
W = {
    "clinvar_plp_upgrade":      40,   # per variant reclassified to P/LP (cap 2)  -> strongest, near-actionable
    "new_high_priority":        25,   # per candidate newly in high-confidence tier (cap 2)
    "new_gene_evidence":        12,   # per candidate whose gene-disease association strengthened (cap 3)
    "other_clinvar_reclass":     5,   # per ClinVar reclassification that is NOT to P/LP (cap 4)
    "phenotype_change":          6,   # per new HPO term since last analysis (cap 5)
    "new_candidate":             3,   # per new (non-promoted) candidate (cap 4) -- weak: volume, not quality
    "time_per_year":             4,   # per year since last analysis (cap 5 y)  -> max 20
    "incomplete_prior_base":    10,   # prior analysis did not complete
    "flag_partial_panel":       10,   # genes were never examined
    "flag_pipeline_error":      10,   # output unreliable / absent
    "flag_qc_fail":              5,   # data quality questionable (may need re-sequencing rather than reanalysis)
    "flag_no_parental_data":     5,   # inheritance filtering impossible at the time
    "prior_complete_unknown":    5,   # prior_analysis_complete is NA: completeness not demonstrated
    "trio":                      4,   # de novo / inheritance filtering possible -> higher reanalysis yield
    "duo":                       2,
    "genome":                    3,   # re-annotation gains (SV / non-coding knowledge) accrue mainly to genomes
}
# Free-text note events that carry information present in no structured column.
NOTE_EVENTS = {
    "parents now consented and sequenced; trio data available": ("trio data now available (was singleton)", 30),
    "matchmaker exchange match reported by external centre":    ("Matchmaker Exchange match", 30),
    "research collaboration reported a second family with a variant in the same gene": ("second family with variant in same gene", 30),
    "second affected sibling now presenting with overlapping features": ("second affected sibling (segregation possible)", 25),
    "skin fibroblast RNA study completed":                       ("functional RNA study available", 20),
    "muscle biopsy results now available":                       ("muscle biopsy results available", 15),
    "deep phenotyping completed at specialist clinic":           ("deep phenotyping completed", 15),
    "clinician requested review following new MRI findings":    ("clinician request: new MRI findings", 15),
    "clinician requested review ahead of family planning":       ("clinician request: family planning (time-sensitive)", 15),
    "new consanguinity information provided by family":          ("new consanguinity information", 10),
}
# Recency dampener applied to EVIDENCE points (interaction: new evidence only matters if the
# previous analysis is old enough to have missed it / the case has had time to accrue change).
def recency_multiplier(years):
    if years < 0.25:  return 0.20   # analysed within ~3 months: unlikely to benefit
    if years < 0.50:  return 0.50
    if years < 1.00:  return 0.80
    return 1.00

CAPS = {"clinvar_upgrades_to_plp": 2, "new_high_priority_candidates": 2, "new_gene_evidence": 3,
        "other_clinvar": 4, "phenotype_changes": 5, "new_candidates": 4}

def to_num(s):
    """'NA' -> NaN, else int."""
    return pd.to_numeric(s.replace("NA", np.nan), errors="coerce")

def triage(cases_path):
    df = pd.read_csv(cases_path, sep="\t", keep_default_na=False, dtype=str)
    cur = pd.to_datetime(df["current_analysis"].iloc[0])
    df["last_dt"] = pd.to_datetime(df["last_analysis"])
    df["years_since_last"] = ((cur - df["last_dt"]).dt.days / 365.25).round(2)

    # ---------------- missing-value rules (documented in triage_method.md) ----------------
    num_cols = ["hpo_term_count", "phenotype_changes", "candidate_count", "new_candidates",
                "new_high_priority_candidates", "new_gene_evidence", "new_clinvar_evidence",
                "clinvar_upgrades_to_plp", "prior_analysis_complete"]
    for c in num_cols:
        df[c + "_raw"] = df[c]
        df[c] = to_num(df[c])
    # evidence counts NA -> 0 (absence of evidence, not evidence of absence; flagged in reason)
    for c in ["phenotype_changes", "new_gene_evidence", "new_candidates", "new_high_priority_candidates",
              "new_clinvar_evidence", "clinvar_upgrades_to_plp"]:
        df[c + "_na"] = df[c].isna()
        df[c] = df[c].fillna(0)
    # prior_analysis_complete NA -> treated as "unknown" (small bonus), NOT as complete
    df["prior_complete_na"] = df["prior_analysis_complete"].isna()
    # hpo_term_count is not scored; NA left as is.

    rows = []
    for _, r in df.iterrows():
        ev = 0.0; parts = []; missing = []
        # --- evidence signals ---
        k = min(r.clinvar_upgrades_to_plp, CAPS["clinvar_upgrades_to_plp"])
        if k: ev += W["clinvar_plp_upgrade"] * k; parts.append(f"{int(r.clinvar_upgrades_to_plp)} ClinVar upgrade(s) to P/LP")
        k = min(r.new_high_priority_candidates, CAPS["new_high_priority_candidates"])
        if k: ev += W["new_high_priority"] * k; parts.append(f"{int(r.new_high_priority_candidates)} new high-priority candidate(s)")
        k = min(r.new_gene_evidence, CAPS["new_gene_evidence"])
        if k: ev += W["new_gene_evidence"] * k; parts.append(f"{int(r.new_gene_evidence)} candidate(s) with strengthened gene-disease evidence")
        other_cv = max(r.new_clinvar_evidence - r.clinvar_upgrades_to_plp, 0)
        k = min(other_cv, CAPS["other_clinvar"])
        if k: ev += W["other_clinvar_reclass"] * k; parts.append(f"{int(other_cv)} other ClinVar reclassification(s)")
        k = min(r.phenotype_changes, CAPS["phenotype_changes"])
        if k: ev += W["phenotype_change"] * k; parts.append(f"{int(r.phenotype_changes)} new HPO term(s)")
        k = min(r.new_candidates, CAPS["new_candidates"])
        if k: ev += W["new_candidate"] * k; parts.append(f"{int(r.new_candidates)} new candidate(s)")
        # --- note events ---
        note_pts = 0; note_label = ""
        if r.note in NOTE_EVENTS:
            note_label, note_pts = NOTE_EVENTS[r.note]
            ev += note_pts; parts.append(f"note: {note_label}")
        # --- incomplete prior analysis ---
        inc = 0.0
        if r.prior_analysis_complete == 0:
            inc += W["incomplete_prior_base"]
            fl = r.prior_analysis_flag
            inc += W.get("flag_" + fl, 0)
            # no_parental_data + trio now available is fully covered by the note bonus; avoid double counting
            parts.append(f"prior analysis incomplete ({fl or 'unspecified'})")
        elif r.prior_complete_na:
            inc += W["prior_complete_unknown"]; parts.append("prior analysis completeness unknown (NA)")
        # --- time ---
        yrs = r.years_since_last
        tpts = W["time_per_year"] * min(yrs, 5.0)
        mult = recency_multiplier(yrs)
        # --- context ---
        ctx = W.get(r.family_structure, 0) + (W["genome"] if r.sequencing_type == "genome" else 0)
        # --- missing flags ---
        for c in ["phenotype_changes", "new_gene_evidence"]:
            if r[c + "_na"]: missing.append(f"{c}=NA treated as 0")
        if r.hpo_term_count_raw == "NA": missing.append("hpo_term_count=NA (not scored)")

        evidence_pts = ev + inc
        score = mult * evidence_pts + tpts + ctx
        if r.case_status == "partially_solved":
            score *= 0.9
        # --- assemble reason ---
        time_str = f"last analysed {yrs:.1f} y ago"
        if mult < 1: time_str += f" (recency dampener x{mult:.2f} on evidence)"
        if not parts:
            reason = f"no new evidence; {time_str}; deprioritised"
        else:
            reason = "; ".join(parts) + f"; {time_str}"
        if r.case_status == "partially_solved": reason += "; partially solved (x0.9)"
        if missing: reason += "; " + ", ".join(missing)
        if r.case_status == "solved":
            reason = "already solved at cycle start -> skip (would-be score " + f"{score:.1f}); " + reason
            score_final = 0.0
        else:
            score_final = score
        rows.append(dict(case_id=r.case_id, score=round(score_final, 1), would_be_score=round(score, 1),
                         evidence_points=round(evidence_pts, 1), recency_multiplier=mult,
                         time_points=round(tpts, 1), context_points=ctx, note_points=note_pts, reason=reason))
    out = pd.DataFrame(rows)
    df = df.merge(out, on="case_id")

    # ---------------- tiers ----------------
    def tier(r):
        if r.case_status == "solved": return "Skip - already solved"
        strong = (r.clinvar_upgrades_to_plp >= 1 or r.new_high_priority_candidates >= 1 or r.note_points >= 25)
        if r.score >= 50 and strong and r.years_since_last >= 0.5: return "Review now"
        if r.score >= 30: return "Review this cycle"
        return "Defer"
    df["tier"] = df.apply(tier, axis=1)

    # ---------------- ranking & tie-break ----------------
    # score desc, then years since last analysis desc, then case_id asc. Solved cases sink to the bottom,
    # ordered among themselves by would-be score.
    df["_solved"] = (df.case_status == "solved").astype(int)
    df = df.sort_values(["_solved", "score", "would_be_score", "years_since_last", "case_id"],
                        ascending=[True, False, False, False, True]).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    keep = ["rank", "case_id", "tier", "score", "reason", "case_status", "years_since_last", "last_analysis",
            "sequencing_type", "family_structure", "hpo_term_count_raw", "phenotype_changes_raw",
            "candidate_count_raw", "new_candidates_raw", "new_high_priority_candidates_raw",
            "new_gene_evidence_raw", "new_clinvar_evidence_raw", "clinvar_upgrades_to_plp_raw",
            "prior_analysis_complete_raw", "prior_analysis_flag", "note",
            "evidence_points", "recency_multiplier", "time_points", "context_points", "note_points"]
    res = df[keep].rename(columns={c: c.replace("_raw", "") for c in keep})
    return res

def baseline(cases_path):
    df = pd.read_csv(cases_path, sep="\t", keep_default_na=False, dtype=str)
    df["last_dt"] = pd.to_datetime(df["last_analysis"])
    df = df.sort_values(["last_dt", "case_id"], ascending=[True, True]).reset_index(drop=True)
    df["rank"] = np.arange(1, len(df) + 1)
    return df[["rank", "case_id", "last_analysis", "case_status"]]

if __name__ == "__main__":
    cases = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(outdir, exist_ok=True)
    triage(cases).to_csv(os.path.join(outdir, "triage_ranking.csv"), index=False)
    baseline(cases).to_csv(os.path.join(outdir, "baseline_oldest_first.csv"), index=False)
    print("written", outdir)
