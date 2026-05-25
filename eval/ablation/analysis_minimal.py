#!/usr/bin/env python3
"""
Minimal Analysis: Ablation + Convergence Metrics (FCR, LUR, PPU) + Statistical Significance

Loads scores_*.json and computes:
  - Ablation Results: Mean ± SD scores by tier (T0-T3)
  - Statistical Significance: Friedman test + pairwise Wilcoxon + rank-biserial r
  - FCR: Feedback Compliance Rate (T3 only)
  - LUR: Loop Utilization Rate (T3 only)
  - PPU: Pattern Persistence Utilization (warm vs cold start)

Usage:
  python eval/analysis_minimal.py [--results-dir eval/results/deepseek] [--provider deepseek]
"""

import sys
import os
import json
import glob
import argparse
import math
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from eval.ablation.synthetic_profiles import get_feedback_battery_type

TIERS = ["t0", "t1", "t2", "t3"]
TIER_LABELS = {"t0": "T0 Generic", "t1": "T1 +Profile", "t2": "T2 +Context", "t3": "T3 Full"}
AXES = ["PF", "CC", "CA", "PC", "DA"]
AXIS_WEIGHTS = {"PF": 0.20, "CC": 0.20, "CA": 0.30, "PC": 0.20, "DA": 0.10}


# ── Load Results ──────────────────────────────────────────────────────────────

def load_results(results_dir: str) -> List[Dict[str, Any]]:
    """Load all scores_*.json files from results_dir."""
    pattern = os.path.join(results_dir, "scores_*.json")
    files = glob.glob(pattern)
    records = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            try:
                records.append(json.load(f))
            except Exception as e:
                print(f"  Skipping {path}: {e}")
    print(f"[OK] Loaded {len(records)} score records from {results_dir}")
    return records


def _get_composite(record: Dict, judgment_key: str = "initial_judgment") -> Optional[float]:
    j = record.get(judgment_key, {})
    return j.get("composite")


def _get_scores(record: Dict, judgment_key: str = "initial_judgment") -> Optional[Dict]:
    j = record.get(judgment_key, {})
    return j.get("scores")


# ── Ablation Results ──────────────────────────────────────────────────────────

def compute_ablation(records: List[Dict]) -> Dict[str, Dict[str, float]]:
    """
    Compute mean scores by tier.

    Returns: {
        "t0": {"PF": float, "CC": float, "CA": float, "PC": float, "DA": float, "composite": float},
        ...
    }
    """
    tier_scores = {t: {ax: [] for ax in AXES} for t in TIERS}
    tier_composites = {t: [] for t in TIERS}

    for r in records:
        tier = r.get("tier")
        if tier not in TIERS:
            continue

        scores = _get_scores(r, "initial_judgment")
        composite = _get_composite(r, "initial_judgment")

        if scores:
            for ax in AXES:
                if ax in scores:
                    tier_scores[tier][ax].append(scores[ax])

        if composite is not None:
            tier_composites[tier].append(composite)

    # Compute means + SD
    result = {}
    for tier in TIERS:
        result[tier] = {}
        for ax in AXES:
            vals = tier_scores[tier][ax]
            result[tier][ax] = round(sum(vals) / len(vals), 2) if vals else None

        comp_vals = tier_composites[tier]
        if comp_vals:
            mean = sum(comp_vals) / len(comp_vals)
            variance = sum((x - mean) ** 2 for x in comp_vals) / len(comp_vals)
            result[tier]["composite"] = round(mean, 3)
            result[tier]["sd"] = round(math.sqrt(variance), 3)
        else:
            result[tier]["composite"] = None
            result[tier]["sd"] = None
        result[tier]["n"] = len(comp_vals)
        result[tier]["_raw"] = comp_vals  # kept for significance tests, stripped before JSON save

    return result


# ── Statistical Significance ──────────────────────────────────────────────────

def _rank_biserial_r(wilcoxon_stat: float, n: int) -> float:
    """
    Rank-biserial correlation from Wilcoxon signed-rank statistic W.
    Formula: r = 1 - (2 * W) / (n * (n + 1) / 2)
    Range [0, 1]: r = 1.0 means all n pairs moved in the same direction.
    This is the natural non-parametric effect size for Wilcoxon signed-rank.
    """
    if n < 1 or math.isnan(wilcoxon_stat):
        return float("nan")
    max_w = n * (n + 1) / 2
    return round(1.0 - (2.0 * wilcoxon_stat) / max_w, 3)


def _effect_label(r: float) -> str:
    """Effect size label for rank-biserial r (Cohen 1988 thresholds for r)."""
    r = abs(r)
    if r >= 0.5:
        return "large"
    if r >= 0.3:
        return "medium"
    if r >= 0.1:
        return "small"
    return "negligible"


def _holm_bonferroni(p_values: List[float]) -> List[float]:
    """
    Holm-Bonferroni adjusted p-values (Holm 1979).
    Uniformly more powerful than Bonferroni; controls FWER without assuming
    independence. Steps: sort ascending, multiply by (m - rank), enforce
    monotone non-decrease by taking cumulative max.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = min(p_values[idx] * (m - rank), 1.0)
        running_max = max(running_max, adj)
        adjusted[idx] = running_max
    return adjusted


def compute_significance(records: List[Dict]) -> Dict:
    """
    Statistical significance of tier differences using existing data only.

    - Friedman test across all 4 tiers (omnibus)
    - Pairwise Wilcoxon signed-rank tests (paired by user+topic)
    - Rank-biserial r effect sizes
    - Holm-Bonferroni correction across 6 pairwise comparisons
      (more powerful than Bonferroni; does not assume test independence)
    - Analysis is run independently per provider; no cross-provider correction applied
      (providers are treated as separate populations, not simultaneous hypotheses)
    """
    try:
        from scipy import stats as sp_stats
    except ImportError:
        return {"error": "scipy not installed — run: pip install scipy"}

    # Build paired data: {(user_id, topic): {tier: composite}}
    cell_map: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
    for r in records:
        tier = r.get("tier")
        user_id = r.get("user_id")
        topic = r.get("topic")
        composite = _get_composite(r, "initial_judgment")
        if tier in TIERS and user_id and topic and composite is not None:
            cell_map[(user_id, topic)][tier] = composite

    # Only keep cells that have all 4 tiers (needed for Friedman + paired Wilcoxon)
    complete_cells = {k: v for k, v in cell_map.items() if all(t in v for t in TIERS)}
    n_complete = len(complete_cells)

    if n_complete < 3:
        return {"error": f"Too few complete cells ({n_complete}) for significance tests"}

    # Tier vectors (aligned by cell)
    tier_vecs: Dict[str, List[float]] = {t: [] for t in TIERS}
    for cell_scores in complete_cells.values():
        for t in TIERS:
            tier_vecs[t].append(cell_scores[t])

    # Friedman test
    friedman_stat, friedman_p = sp_stats.friedmanchisquare(*[tier_vecs[t] for t in TIERS])
    friedman_p = max(friedman_p, sys.float_info.min)

    # Pairwise Wilcoxon — collect all raw p-values first, then apply Holm-Bonferroni
    pairs = [
        ("t0", "t1"), ("t0", "t2"), ("t0", "t3"),
        ("t1", "t2"), ("t1", "t3"), ("t2", "t3"),
    ]
    n_comparisons = len(pairs)

    raw_results = []
    for ta, tb in pairs:
        a, b = tier_vecs[ta], tier_vecs[tb]
        try:
            stat, p_raw = sp_stats.wilcoxon(a, b, alternative="two-sided")
        except ValueError:
            stat, p_raw = float("nan"), 1.0
        p_raw = max(p_raw, sys.float_info.min)  # clamp float underflow
        r = _rank_biserial_r(stat, len(a))
        raw_results.append({
            "pair": f"{ta}_vs_{tb}",
            "mean_diff": round(sum(b) / len(b) - sum(a) / len(a), 3),
            "rank_biserial_r": r,
            "effect": _effect_label(r),
            "wilcoxon_stat": round(stat, 3),
            "p_raw": p_raw,
        })

    # Apply Holm-Bonferroni across all 6 p-values together
    p_raws = [res["p_raw"] for res in raw_results]
    p_holm = _holm_bonferroni(p_raws)

    pairwise = {}
    for res, p_adj in zip(raw_results, p_holm):
        key = res.pop("pair")
        res["p_holm"] = p_adj
        res["significant"] = bool(p_adj < 0.05)
        pairwise[key] = res

    return {
        "n_paired_cells": n_complete,
        "n_comparisons": n_comparisons,
        "correction": "Holm-Bonferroni",
        "analysis_scope": "per-provider (providers treated as independent populations)",
        "friedman": {
            "statistic": round(friedman_stat, 3),
            "p_value": friedman_p,
            "significant": bool(friedman_p < 0.05),
        },
        "pairwise": pairwise,
    }


def _strip_raw(ablation: Dict) -> Dict:
    """Remove _raw lists before JSON serialisation."""
    cleaned = {}
    for tier, vals in ablation.items():
        cleaned[tier] = {k: v for k, v in vals.items() if k != "_raw"}
    return cleaned


# ── Convergence Metrics ───────────────────────────────────────────────────────

def compute_fcr(records: List[Dict]) -> Dict:
    """
    Feedback Compliance Rate: Proportion of regenerations with compliance_score >= 3/4.
    Only uses T3 records with fcr_results.
    """
    t3 = [r for r in records if r.get("tier") == "t3"]

    buckets = {"easy": [], "adversarial": [], "all": []}
    for r in t3:
        for fc in r.get("fcr_results", []):
            score = fc.get("compliance", {}).get("compliance_score")
            if score is None:
                continue
            battery = get_feedback_battery_type(fc.get("feedback_given", ""))
            buckets[battery].append(score)
            buckets["all"].append(score)

    def summarise(scores: List[int]) -> Dict:
        if not scores:
            return {"n": 0, "fcr_3": None, "fcr_4": None, "mean": None}
        return {
            "n": len(scores),
            "fcr_3": round(sum(1 for s in scores if s >= 3) / len(scores), 3),
            "fcr_4": round(sum(1 for s in scores if s >= 4) / len(scores), 3),
            "mean": round(sum(scores) / len(scores), 3),
        }

    return {
        "easy": summarise(buckets["easy"]),
        "adversarial": summarise(buckets["adversarial"]),
        "overall": summarise(buckets["all"]),
    }


def compute_lur(records: List[Dict]) -> Dict:
    """
    Loop Utilization Rate: Fraction of T3 sessions that triggered >= 1 regeneration.
    """
    t3 = [r for r in records if r.get("tier") == "t3"]
    if not t3:
        return {"n": 0, "lur": None}

    def _had_regen(r: Dict) -> bool:
        return any(
            rd.get("status") == "awaiting_feedback"
            for rd in r.get("run", {}).get("rounds", [])
            if rd.get("round", 0) > 0
        )

    def _battery(r: Dict) -> str:
        return "adversarial" if r.get("profile", {}).get("start_mode") == "warm" else "easy"

    buckets = {"easy": [], "adversarial": [], "all": []}
    for r in t3:
        regen = _had_regen(r)
        b = _battery(r)
        buckets[b].append(regen)
        buckets["all"].append(regen)

    def summarise(vals: List[bool]) -> Dict:
        if not vals:
            return {"n": 0, "triggered": 0, "lur": None}
        return {
            "n": len(vals),
            "triggered": sum(vals),
            "lur": round(sum(vals) / len(vals), 3),
        }

    return {
        "easy": summarise(buckets["easy"]),
        "adversarial": summarise(buckets["adversarial"]),
        "overall": summarise(buckets["all"]),
    }


def compute_ppu(records: List[Dict]) -> Dict:
    """
    Pattern Persistence Utilization: PF delta between warm T3 and warm T1 initial examples.
    Measures whether stored patterns improve personalization at generation time.
    """
    warm_t3 = [r for r in records if r.get("tier") == "t3" and r.get("profile", {}).get("start_mode") == "warm"]
    warm_t1 = [r for r in records if r.get("tier") == "t1" and r.get("profile", {}).get("start_mode") == "warm"]
    cold_t3 = [r for r in records if r.get("tier") == "t3" and r.get("profile", {}).get("start_mode") == "cold"]

    def _mean_pf(recs: List[Dict]) -> Optional[float]:
        scores = [
            _get_scores(r, "initial_judgment").get("PF")
            for r in recs
            if _get_scores(r, "initial_judgment")
        ]
        scores = [s for s in scores if s is not None]
        return round(sum(scores) / len(scores), 3) if scores else None

    warm_t3_pf = _mean_pf(warm_t3)
    warm_t1_pf = _mean_pf(warm_t1)
    cold_t3_pf = _mean_pf(cold_t3)

    delta = round(warm_t3_pf - warm_t1_pf, 3) if (warm_t3_pf is not None and warm_t1_pf is not None) else None

    return {
        "n_warm_t3": len(warm_t3),
        "n_warm_t1": len(warm_t1),
        "n_cold_t3": len(cold_t3),
        "warm_t3_pf": warm_t3_pf,
        "warm_t1_pf": warm_t1_pf,
        "cold_t3_pf": cold_t3_pf,
        "delta_pf": delta,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main(results_dir: str, provider: str) -> None:
    """Load results, compute metrics, and print to console + JSON."""

    print(f"\n{'='*70}")
    print(f"ANALYSIS: {provider.upper()}")
    print(f"{'='*70}\n")

    records = load_results(results_dir)

    # Ablation
    print("\n[1] Ablation Results (Tier Means ± SD)")
    print("-" * 70)
    ablation = compute_ablation(records)

    for tier in TIERS:
        result = ablation[tier]
        pf = result.get("PF")
        cc = result.get("CC")
        ca = result.get("CA")
        pc = result.get("PC")
        da = result.get("DA")
        comp = result.get("composite")
        sd = result.get("sd")
        n = result.get("n")
        print(f"{TIER_LABELS[tier]:<16} PF={pf:>5} CC={cc:>5} CA={ca:>5} PC={pc:>5} DA={da:>5} | Composite={comp:>6} ± {sd:<5} (n={n})")

    # Compute deltas
    print("\nTier Deltas (Delta from T0):")
    if ablation["t0"]["composite"]:
        for tier in TIERS[1:]:
            delta = round(ablation[tier]["composite"] - ablation["t0"]["composite"], 3)
            print(f"  T0 -> {tier}: +{delta}")

    # Statistical Significance
    print("\n[2] Statistical Significance")
    print("-" * 70)
    sig = compute_significance(records)
    if "error" in sig:
        print(f"  ERROR: {sig['error']}")
    else:
        fr = sig["friedman"]
        print(f"Friedman test (all 4 tiers, n={sig['n_paired_cells']} paired cells):")
        print(f"  chi2={fr['statistic']}, p={fr['p_value']:.3e}  {'*** SIGNIFICANT' if fr['significant'] else 'not significant'}")
        print(f"\nPairwise Wilcoxon (Holm-Bonferroni corrected, {sig['n_comparisons']} comparisons — per-provider, independent):")
        print(f"  {'Pair':<12} {'Mean Diff':>10} {'r_rb':>7} {'Effect':>10} {'p_raw':>12} {'p_holm':>12} {'Sig':>5}")
        print(f"  {'-'*70}")
        for pair_key, pw in sig["pairwise"].items():
            label = pair_key.replace("_vs_", " vs ").upper()
            sig_marker = "***" if pw["p_holm"] < 0.001 else ("**" if pw["p_holm"] < 0.01 else ("*" if pw["significant"] else "ns"))
            print(f"  {label:<12} {pw['mean_diff']:>+10.3f} {pw['rank_biserial_r']:>+7.3f} {pw['effect']:>10} {pw['p_raw']:>12.3e} {pw['p_holm']:>12.3e} {sig_marker:>5}")

    # FCR
    print("\n[3] Feedback Compliance Rate (T3)")
    print("-" * 70)
    fcr = compute_fcr(records)
    for battery_type in ["easy", "adversarial", "overall"]:
        result = fcr[battery_type]
        print(f"{battery_type:<12} FCR@3={result.get('fcr_3')} FCR@4={result.get('fcr_4')} (n={result.get('n')})")

    # LUR
    print("\n[4] Loop Utilization Rate (T3)")
    print("-" * 70)
    lur = compute_lur(records)
    for battery_type in ["easy", "adversarial", "overall"]:
        result = lur[battery_type]
        print(f"{battery_type:<12} LUR={result.get('lur')} (triggered={result.get('triggered')}/{result.get('n')})")

    # PPU
    print("\n[5] Pattern Persistence Utilization")
    print("-" * 70)
    ppu = compute_ppu(records)
    print(f"Warm T3 initial PF (n={ppu['n_warm_t3']}):  {ppu['warm_t3_pf']}")
    print(f"Warm T1 initial PF (n={ppu['n_warm_t1']}):  {ppu['warm_t1_pf']}")
    print(f"Cold T3 initial PF (n={ppu['n_cold_t3']}):  {ppu['cold_t3_pf']}")
    print(f"Delta PF (Warm T3 - Warm T1): {ppu['delta_pf']}")

    # Save results
    output_file = os.path.join(results_dir, f"analysis_{provider}.json")
    save_sig = {k: v for k, v in sig.items()} if "error" not in sig else sig
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "provider": provider,
            "ablation": _strip_raw(ablation),
            "significance": save_sig,
            "fcr": fcr,
            "lur": lur,
            "ppu": ppu,
        }, f, indent=2)
    print(f"\n[OK] Results saved to {output_file}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal evaluation analysis")
    parser.add_argument("--results-dir", default="eval/ablation/results/deepseek", help="Results directory")
    parser.add_argument("--provider", default="deepseek", help="Provider name for output")
    args = parser.parse_args()

    main(args.results_dir, args.provider)
