"""
Study B — Contextual Full-Rubric Analysis
==========================================
Reads completed human annotation scores and the sample manifest, then runs
the full analysis plan:

  1. ICC(2,1) — PF, CC, CA, PC, DA, FC, IS  (7 axes, 5 raters, n=30)
  2. Pearson r — human mean vs LLM judge     (PF–DA axes)
  3. Pearson r — human FC vs LLM FCR         (example-level cross-validation)
  4. Binomial test — IP preference (T3 vs T0, need ≥22/30 for significance)
  5. t-test IS vs null=3                     (human-measured improvement delta)
  6. Cold vs warm breakdown                  (mean PF, IS)
  7. Profile breakdown                       (mean PF by role)

Input files:
    eval/human_eval/results/study_b/sample_manifest.json
    eval/human_eval/results/study_b/annotator_scores.json

  annotator_scores.json format:
    {
      "B1": [{"example_id": "EX01", "PF": 4, "CC": 4, ..., "IP": "T3"}, ...],
      "B2": [...],
      ...  (B1–B5)
    }

  Alternatively, load from CSV: scores_template.csv (filled in by annotators).

Run:
    python eval/human_eval/study_b_analysis.py [--from-csv]

Outputs:
    eval/human_eval/results/study_b/study_b_results.json
    eval/human_eval/results/study_b/study_b_report.md
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

ROOT    = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = ROOT / "eval" / "human_eval" / "study_b" / "results"

AXES_7  = ["PF", "CC", "CA", "PC", "DA", "FC", "IS"]
AXES_5  = ["PF", "CC", "CA", "PC", "DA"]
ANN_IDS = ["B1", "B2", "B3", "B4", "B5"]


# ─────────────────────────────────────────────────────────────────────────────
# ICC(2,1) — two-way mixed, single measures, consistency
# ─────────────────────────────────────────────────────────────────────────────
def icc_two_way_mixed(data: np.ndarray) -> dict:
    """
    data shape: (n_subjects, n_raters)
    Returns icc, F, df1, df2, p, ci_lower, ci_upper, interpretation.
    """
    n, k  = data.shape
    grand = data.mean()
    row_m = data.mean(axis=1)
    col_m = data.mean(axis=0)

    SSR = k * ((row_m - grand) ** 2).sum()
    SSC = n * ((col_m - grand) ** 2).sum()
    SST = ((data - grand) ** 2).sum()
    SSE = SST - SSR - SSC

    MSR = SSR / (n - 1)
    MSE = SSE / ((n - 1) * (k - 1))

    icc_val = (MSR - MSE) / (MSR + (k - 1) * MSE)

    F   = MSR / MSE
    df1 = n - 1
    df2 = (n - 1) * (k - 1)
    p   = float(1 - stats.f.cdf(F, df1, df2))

    alpha = 0.05
    FL    = (F / stats.f.ppf(1 - alpha / 2, df1, df2) - 1) / \
            (F / stats.f.ppf(1 - alpha / 2, df1, df2) + k - 1)
    FU    = (F * stats.f.ppf(1 - alpha / 2, df2, df1) - 1) / \
            (F * stats.f.ppf(1 - alpha / 2, df2, df1) + k - 1)

    icc_val = float(icc_val)
    if icc_val >= 0.90:
        interp = "Excellent"
    elif icc_val >= 0.75:
        interp = "Good"
    elif icc_val >= 0.50:
        interp = "Moderate"
    else:
        interp = "Poor"

    return {
        "icc":            round(icc_val, 4),
        "F":              round(float(F), 3),
        "df1":            int(df1),
        "df2":            int(df2),
        "p":              p,
        "ci_lower":       round(max(0.0, float(FL)), 4),
        "ci_upper":       round(min(1.0, float(FU)), 4),
        "interpretation": interp,
    }


def weighted_kappa(rater_a: list[int], rater_b: list[int],
                   categories=range(1, 6)) -> float:
    cats = list(categories)
    k    = len(cats)
    n    = len(rater_a)
    mat  = np.zeros((k, k))
    for a, b in zip(rater_a, rater_b):
        i, j = cats.index(a), cats.index(b)
        mat[i, j] += 1
    mat /= n
    weights = np.array([[1 - abs(i - j) / (k - 1) for j in range(k)] for i in range(k)])
    po = (weights * mat).sum()
    pe = (weights * np.outer(mat.sum(axis=1), mat.sum(axis=0))).sum()
    return round(float((po - pe) / (1 - pe)), 4) if (1 - pe) != 0 else 1.0


def pct_exact_agree(rater_a: list[int], rater_b: list[int]) -> float:
    return sum(a == b for a, b in zip(rater_a, rater_b)) / len(rater_a)


# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────
def load_scores_from_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_scores_from_csv(path: Path) -> dict:
    """
    Reads a filled-in scores_template.csv.
    Returns dict keyed by annotator_id → list of score rows (ordered by example).
    """
    scores: dict[str, dict[str, dict]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ann_id  = row["annotator_id"].strip()
            ex_id   = row["example_id"].strip()
            if ann_id not in scores:
                scores[ann_id] = {}
            entry = {}
            for ax in AXES_7:
                val = row.get(ax, "").strip()
                entry[ax] = int(val) if val.isdigit() else None
            ip_val = row.get("IP", "").strip().upper()
            entry["IP"] = ip_val if ip_val in ("T0", "T3") else None
            scores[ann_id][ex_id] = entry

    # Convert to ordered lists matching manifest order
    result: dict[str, list[dict]] = {}
    for ann_id, ex_map in scores.items():
        result[ann_id] = [{"example_id": k, **v} for k, v in ex_map.items()]
    return result


def validate_scores(scores: dict, manifest: list[dict]) -> list[str]:
    """Return list of warning strings."""
    warnings = []
    ex_ids = [e["example_id"] for e in manifest]

    for ann_id in ANN_IDS:
        if ann_id not in scores:
            warnings.append(f"Missing annotator: {ann_id}")
            continue
        rows = scores[ann_id]
        if len(rows) != len(manifest):
            warnings.append(f"{ann_id}: expected {len(manifest)} rows, got {len(rows)}")
        for row in rows:
            ex_id = row.get("example_id", "?")
            if ex_id not in ex_ids:
                warnings.append(f"{ann_id}/{ex_id}: example_id not in manifest")
            for ax in AXES_7:
                v = row.get(ax)
                if v is None:
                    warnings.append(f"{ann_id}/{ex_id}: missing {ax}")
                elif not (1 <= v <= 5):
                    warnings.append(f"{ann_id}/{ex_id}: {ax}={v} out of range [1,5]")
            ip = row.get("IP")
            if ip not in ("T0", "T3"):
                warnings.append(f"{ann_id}/{ex_id}: IP='{ip}' must be T0 or T3")
    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────────────────────
def sig_stars(p: float) -> str:
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


def run_analysis(manifest: list[dict], scores: dict) -> dict:
    n = len(manifest)

    # Build numpy arrays: h[ann_id][ax] = array length n
    h: dict[str, dict[str, np.ndarray]] = {}
    for ann_id in ANN_IDS:
        rows    = {r["example_id"]: r for r in scores[ann_id]}
        ordered = [rows[e["example_id"]] for e in manifest]
        h[ann_id] = {
            ax: np.array([r[ax] for r in ordered], dtype=float)
            for ax in AXES_7
        }
        h[ann_id]["IP"] = np.array(
            [1 if r["IP"] == "T3" else 0 for r in ordered], dtype=int
        )

    # Mean human scores per axis across annotators
    h_mean = {ax: np.mean([h[a][ax] for a in ANN_IDS], axis=0) for ax in AXES_7}

    # ── 1. ICC(2,1) per axis (5 raters, n=30) ────────────────────────────────
    per_axis_icc = {}
    for ax in AXES_7:
        mat = np.column_stack([h[a][ax] for a in ANN_IDS])
        per_axis_icc[ax] = icc_two_way_mixed(mat)

    # ── 2. Pearson r: human mean vs LLM judge (PF–DA) ────────────────────────
    llm_t3 = {
        ax: np.array([
            e["llm_t3_scores"][ax] if e["llm_t3_scores"] else float("nan")
            for e in manifest
        ])
        for ax in AXES_5
    }
    per_axis_pearson_llm: dict[str, dict] = {}
    for ax in AXES_5:
        mask = ~np.isnan(llm_t3[ax])
        if mask.sum() < 3:
            per_axis_pearson_llm[ax] = {"r": None, "p": None, "n": int(mask.sum())}
            continue
        r, p = stats.pearsonr(h_mean[ax][mask], llm_t3[ax][mask])
        per_axis_pearson_llm[ax] = {
            "r": round(float(r), 4),
            "p": float(p),
            "n": int(mask.sum()),
        }

    # Overall composite
    composite_weights = {"PF": 0.20, "CC": 0.20, "CA": 0.30, "PC": 0.20, "DA": 0.10}
    h_composite  = sum(composite_weights[ax] * h_mean[ax] for ax in AXES_5)
    llm_composite = np.array([
        sum(composite_weights[ax] * (e["llm_t3_scores"][ax] if e["llm_t3_scores"] else 0)
            for ax in AXES_5)
        for e in manifest
    ])
    mask_comp = np.array([e["llm_t3_scores"] is not None for e in manifest])
    if mask_comp.sum() >= 3:
        r_c, p_c = stats.pearsonr(h_composite[mask_comp], llm_composite[mask_comp])
    else:
        r_c, p_c = float("nan"), float("nan")

    composite_pearson = {
        "r": round(float(r_c), 4), "p": float(p_c),
        "n": int(mask_comp.sum()),
        "interpretation": "Strong" if r_c >= 0.80 else ("Moderate" if r_c >= 0.60 else "Weak"),
    }

    # ── 3. Pearson r: human FC vs LLM FCR (example-level) ────────────────────
    llm_fcr = np.array([
        e["llm_fcr_mean"] if e["llm_fcr_mean"] is not None else float("nan")
        for e in manifest
    ])
    mask_fcr = ~np.isnan(llm_fcr)
    if mask_fcr.sum() >= 3:
        r_fc, p_fc = stats.pearsonr(h_mean["FC"][mask_fcr], llm_fcr[mask_fcr])
        fc_pearson = {
            "r": round(float(r_fc), 4), "p": float(p_fc),
            "n": int(mask_fcr.sum()),
        }
    else:
        fc_pearson = {"r": None, "p": None, "n": int(mask_fcr.sum())}

    # ── 4. Binomial test: IP preference ──────────────────────────────────────
    # Majority vote per example (T3=1, T0=0); winner is 1 if ≥3 annotators chose T3
    ip_matrix = np.column_stack([h[a]["IP"] for a in ANN_IDS])  # (30, 5)
    t3_votes  = ip_matrix.sum(axis=1)                           # 0-5 per example
    t3_wins   = int((t3_votes >= 3).sum())                      # majority T3
    t0_wins   = n - t3_wins

    # Exact binomial: H0 p=0.5
    binom_result = stats.binomtest(t3_wins, n, p=0.5, alternative="greater")
    informed_preference = {
        "n_examples":        n,
        "t3_wins":           t3_wins,
        "t0_wins":           t0_wins,
        "p_value":           float(binom_result.pvalue),
        "significant":       bool(binom_result.pvalue < 0.05),
        "threshold_22_30":   bool(t3_wins >= 22),
        "mean_t3_vote_share": round(float(ip_matrix.mean()), 3),
        # Also: fraction of individual votes for T3
        "individual_t3_rate": round(float(ip_matrix.mean()), 3),
    }

    # ── 5. IS t-test vs null=3 ────────────────────────────────────────────────
    is_scores  = h_mean["IS"]
    t_stat, p_is = stats.ttest_1samp(is_scores, popmean=3.0)
    is_analysis = {
        "n":             n,
        "mean_IS":       round(float(is_scores.mean()), 3),
        "sd_IS":         round(float(is_scores.std(ddof=1)), 3),
        "t_stat":        round(float(t_stat), 3),
        "df":            n - 1,
        "p_value":       float(p_is),
        "significant":   bool(p_is < 0.05),
        "direction":     "above null" if float(is_scores.mean()) > 3 else "below null",
    }

    # ── 6. Cold vs warm breakdown ─────────────────────────────────────────────
    cold_idx = [i for i, e in enumerate(manifest) if e["profile"]["start_mode"] == "cold"]
    warm_idx = [i for i, e in enumerate(manifest) if e["profile"]["start_mode"] == "warm"]

    def mode_stats(idxs, ax):
        vals = h_mean[ax][idxs]
        return {"n": len(idxs), "mean": round(float(vals.mean()), 3),
                "sd": round(float(vals.std(ddof=1)), 3)}

    cold_warm = {}
    for ax in ["PF", "IS"]:
        c = mode_stats(cold_idx, ax)
        w = mode_stats(warm_idx, ax)
        diff = round(w["mean"] - c["mean"], 3)
        cold_warm[ax] = {"cold": c, "warm": w, "warm_minus_cold": diff}

    # ── 7. Profile breakdown: mean PF by role ────────────────────────────────
    roles = sorted({e["profile"]["role"] for e in manifest})
    profile_breakdown = {}
    for role in roles:
        idxs = [i for i, e in enumerate(manifest) if e["profile"]["role"] == role]
        vals = h_mean["PF"][idxs]
        profile_breakdown[role] = {
            "n":    len(idxs),
            "mean_PF": round(float(vals.mean()), 3),
            "sd_PF":   round(float(vals.std(ddof=1)), 3) if len(idxs) > 1 else None,
        }

    # ── 8. Per-axis weighted kappa (pairwise mean, 5 annotators) ─────────────
    kappa_mean: dict[str, float] = {}
    pct_agree_mean: dict[str, float] = {}
    for ax in AXES_7:
        kvals, pvals = [], []
        for i, ai in enumerate(ANN_IDS):
            for j, aj in enumerate(ANN_IDS):
                if j <= i:
                    continue
                ra = list(h[ai][ax].astype(int))
                rb = list(h[aj][ax].astype(int))
                kvals.append(weighted_kappa(ra, rb))
                pvals.append(pct_exact_agree(ra, rb))
        kappa_mean[ax]     = round(float(np.mean(kvals)), 4)
        pct_agree_mean[ax] = round(float(np.mean(pvals)), 4)

    # ── Descriptive summary ───────────────────────────────────────────────────
    descriptive = {
        ax: {
            "mean": round(float(h_mean[ax].mean()), 3),
            "sd":   round(float(h_mean[ax].std(ddof=1)), 3),
            "min":  round(float(h_mean[ax].min()), 3),
            "max":  round(float(h_mean[ax].max()), 3),
        }
        for ax in AXES_7
    }

    return {
        "n_examples":           n,
        "n_annotators":         len(ANN_IDS),
        "per_axis_icc":         per_axis_icc,
        "per_axis_pearson_llm": per_axis_pearson_llm,
        "composite_pearson":    composite_pearson,
        "fc_pearson_fcr":       fc_pearson,
        "informed_preference":  informed_preference,
        "is_analysis":          is_analysis,
        "cold_warm_breakdown":  cold_warm,
        "profile_breakdown":    profile_breakdown,
        "kappa_mean_by_axis":   kappa_mean,
        "pct_exact_agree":      pct_agree_mean,
        "descriptive":          descriptive,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────
def write_report(results: dict, out_path: Path):
    r  = results
    ip = r["informed_preference"]
    ia = r["is_analysis"]
    cw = r["cold_warm_breakdown"]
    pb = r["profile_breakdown"]
    cp = r["composite_pearson"]
    fp = r["fc_pearson_fcr"]
    de = r["descriptive"]

    def fmt_icc(d: dict) -> str:
        return (f"ICC={d['icc']} [{d['ci_lower']}, {d['ci_upper']}], "
                f"F({d['df1']},{d['df2']})={d['F']}, p{sig_stars(d['p'])} — **{d['interpretation']}**")

    lines = [
        "# Study B — Contextual Full-Rubric Evaluation Report",
        "",
        "**Sample:** 30 examples · 5 annotators · 8 scores per example  ",
        "**Annotators:** B1 (STEM), B2 (Social sci.), B3 (Life sci.), "
        "B4 (Instructional design), B5 (Generalist educator)  ",
        "",
        "---",
        "",
        "## 1. Descriptive Statistics (Human Mean Scores)",
        "",
        "| Axis | Mean | SD | Min | Max |",
        "|------|------|----|-----|-----|",
    ]
    for ax in AXES_7:
        d = de[ax]
        lines.append(f"| {ax} | {d['mean']} | {d['sd']} | {d['min']} | {d['max']} |")

    lines += [
        "",
        "---",
        "",
        "## 2. Inter-Rater Reliability — ICC(2,1), 5 raters, n=30",
        "",
        "| Axis | ICC | 95% CI | F | p | Interpretation |",
        "|------|-----|--------|---|---|----------------|",
    ]
    for ax in AXES_7:
        d = r["per_axis_icc"][ax]
        lines.append(
            f"| {ax} | {d['icc']} | [{d['ci_lower']}, {d['ci_upper']}] | "
            f"{d['F']} | {sig_stars(d['p'])} | **{d['interpretation']}** |"
        )

    lines += [
        "",
        "| Axis | Mean κ (weighted) | % Exact Agreement |",
        "|------|-------------------|-------------------|",
    ]
    for ax in AXES_7:
        k  = r["kappa_mean_by_axis"][ax]
        pa = r["pct_exact_agree"][ax]
        lines.append(f"| {ax} | {k} | {pa:.1%} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Human vs LLM Judge Agreement (PF–DA, Pearson r)",
        "",
        f"**Composite:** r = {cp['r']} (n={cp['n']}, p{sig_stars(cp['p'])}) — "
        f"**{cp['interpretation']}**",
        "",
        "| Axis | r | p |",
        "|------|---|---|",
    ]
    for ax in AXES_5:
        d = r["per_axis_pearson_llm"][ax]
        r_str = str(d["r"]) if d["r"] is not None else "n/a"
        p_str = sig_stars(d["p"]) if d["p"] is not None else "—"
        lines.append(f"| {ax} | {r_str} | {p_str} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Human FC vs LLM FCR Cross-Validation",
        "",
    ]
    if fp["r"] is not None:
        lines.append(
            f"Pearson r = **{fp['r']}** (n={fp['n']}, p{sig_stars(fp['p'])}).  "
        )
        lines.append(
            "Human Feedback Compliance scores are correlated with the automated FCR "
            "metric, cross-validating the LLM-judge-based FCR computation."
        )
    else:
        lines.append("*(insufficient data for FC–FCR correlation)*")

    lines += [
        "",
        "---",
        "",
        "## 5. Informed Preference (IP) — Binomial Test",
        "",
        f"T3 wins (majority vote): **{ip['t3_wins']} / {ip['n_examples']}**  ",
        f"T0 wins: {ip['t0_wins']}  ",
        f"Individual T3 vote rate: {ip['individual_t3_rate']:.1%}  ",
        f"Binomial test (H₀: p=0.5): p = {ip['p_value']:.4f} {sig_stars(ip['p_value'])}  ",
        f"Threshold ≥22/30: {'**MET**' if ip['threshold_22_30'] else 'not met'}  ",
        f"Result: T3 is {'**significantly preferred**' if ip['significant'] else 'not significantly preferred'} over T0.",
        "",
        "---",
        "",
        "## 6. Improvement Score (IS) — t-test vs null = 3",
        "",
        f"Mean IS = **{ia['mean_IS']}** (SD={ia['sd_IS']}, n={ia['n']})  ",
        f"t({ia['df']}) = {ia['t_stat']}, p = {ia['p_value']:.4f} {sig_stars(ia['p_value'])}  ",
        f"Direction: {ia['direction']}  ",
        (f"Human annotators rate improvement as **significantly above neutral** "
         f"(IS > 3)." if ia["significant"] and ia["mean_IS"] > 3
         else "Improvement is not statistically distinguishable from neutral (IS=3)."),
        "",
        "---",
        "",
        "## 7. Cold vs Warm Start Breakdown",
        "",
        "| Start mode | n | Mean PF | Mean IS |",
        "|------------|---|---------|---------|",
    ]
    c_pf = cw["PF"]["cold"]
    w_pf = cw["PF"]["warm"]
    c_is = cw["IS"]["cold"]
    w_is = cw["IS"]["warm"]
    lines.append(f"| Cold | {c_pf['n']} | {c_pf['mean']} | {c_is['mean']} |")
    lines.append(f"| Warm | {w_pf['n']} | {w_pf['mean']} | {w_is['mean']} |")
    lines.append(f"| Δ (warm − cold) | — | **{cw['PF']['warm_minus_cold']:+.3f}** "
                 f"| **{cw['IS']['warm_minus_cold']:+.3f}** |")

    lines += [
        "",
        "---",
        "",
        "## 8. Profile Breakdown — Mean PF by Role",
        "",
        "| Role | n | Mean PF | SD |",
        "|------|---|---------|-----|",
    ]
    for role, d in sorted(pb.items(), key=lambda x: -x[1]["mean_PF"]):
        sd_str = str(d["sd_PF"]) if d["sd_PF"] is not None else "—"
        lines.append(f"| {role} | {d['n']} | {d['mean_PF']} | {sd_str} |")

    lines += ["", "---", ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Study B analysis")
    parser.add_argument("--from-csv", action="store_true",
                        help="Load scores from scores_template.csv instead of annotator_scores.json")
    args = parser.parse_args()

    # Load manifest
    manifest_path = OUT_DIR / "sample_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"sample_manifest.json not found — run study_b_build_sample.py first")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    print(f"Loaded manifest: {len(manifest)} examples")

    # Load scores
    if args.from_csv:
        csv_path = OUT_DIR / "scores_template.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"scores_template.csv not found at {csv_path}")
        scores = load_scores_from_csv(csv_path)
        print(f"Loaded scores from CSV: {csv_path.name}")
    else:
        scores_path = OUT_DIR / "annotator_scores.json"
        if not scores_path.exists():
            raise FileNotFoundError(
                f"annotator_scores.json not found at {scores_path}\n"
                "Either collect scores and write this file, or run with --from-csv"
            )
        scores = load_scores_from_json(scores_path)
        print(f"Loaded scores from JSON: {scores_path.name}")

    # Validate
    warnings = validate_scores(scores, manifest)
    if warnings:
        print(f"\n{len(warnings)} validation warnings:")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print("Scores validated — no warnings.")

    print("\nRunning analysis...")
    results = run_analysis(manifest, scores)

    # Write JSON
    json_path = OUT_DIR / "study_b_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results -> {json_path}")

    # Write report
    report_path = OUT_DIR / "study_b_report.md"
    write_report(results, report_path)
    print(f"Report  -> {report_path}")

    # Quick summary
    print("\n-- Quick Summary ------------------------------------------")
    ip = results["informed_preference"]
    ia = results["is_analysis"]
    cp = results["composite_pearson"]
    fc = results["fc_pearson_fcr"]
    print(f"  IP: T3 wins {ip['t3_wins']}/30 (p={ip['p_value']:.4f} {sig_stars(ip['p_value'])})")
    print(f"  IS: mean={ia['mean_IS']} (t={ia['t_stat']}, p={ia['p_value']:.4f} {sig_stars(ia['p_value'])})")
    print(f"  Human×LLM composite: r={cp['r']} ({cp['interpretation']})")
    print(f"  Human FC × LLM FCR:  r={fc['r']}")
    for ax in AXES_7:
        d = results["per_axis_icc"][ax]
        print(f"  ICC [{ax}]: {d['icc']} ({d['interpretation']})")


if __name__ == "__main__":
    main()
