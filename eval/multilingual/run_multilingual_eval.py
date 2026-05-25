"""
Multilingual Evaluation Runner
Evaluates AdaCraft across 6 languages under two scenarios:

  FNL  (Full Native Language):   topic in lang X → feedback in lang X → output in lang X
  NFEO (Native Feedback, English Output): topic in English → feedback in lang X → output in English

Providers: GPT-5-nano + DeepSeek (all 6 langs) + Sarvam (Indic only: hi/ta/bn)
Secondary judge: 20% subsample on judge_example() — no secondary judge on FCR calls.

Results saved to: eval/results/multilingual/<provider>/<scenario>/
  scores_<scenario>_<user_id>_<lang>_<topic_slug>.json

Usage:
  python eval/multilingual/run_multilingual_eval.py \\
      --scenario fnl nfeo \\
      --providers gpt5nano deepseek \\
      --langs hi ta bn de ar zh \\
      --delay 1.5 \\
      --judge-delay 1.0

  # Analysis only (no new runs):
  python eval/multilingual/run_multilingual_eval.py --analyze-only --provider gpt5nano
"""

import sys
import os
import json
import time
import argparse
import re
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from eval.multilingual.ml_synthetic_profiles import (
    ML_PROFILES,
    TOPICS_EN,
    TOPIC_TRANSLATIONS,
    LANG_NAMES,
    INDIC_LANGS,
    FOREIGN_LANGS,
    ALL_LANGS,
    get_ml_feedback_for_round,
    get_ml_expected_decision,
    get_ml_profile_by_id,
    seed_ml_warm_users,
    ML_FEEDBACK,
)
from eval.ablation.baseline_runners import reset_manager, _ensure_profile_exists, _get_manager
from eval.llm_judge import judge_example, judge_feedback_compliance
from core.language_utils import detect_language

# ── Results Directory ─────────────────────────────────────────────────────────

_BASE_DIR = os.path.join(os.path.dirname(__file__), "results")

# Maps provider tag → workflow provider string (what WorkflowManager.start_feedback_workflow expects)
PROVIDER_WORKFLOW_MAP = {
    "gpt5nano": "openai",
    "deepseek": "openrouter",
    "sarvam": "sarvam",
}

# Primary judge model for each provider run (always GPT-4.1-nano)
PROVIDER_MODEL_MAP = {
    "gpt5nano": "gpt-4.1-nano",
    "deepseek": "gpt-4.1-nano",
    "sarvam": "gpt-4.1-nano",
}

NUM_FEEDBACK_ROUNDS = 3  # R1 critique + R2 accept + R3 flag_pattern


# ── Path Helpers ──────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _results_dir(provider_tag: str, scenario: str) -> str:
    path = os.path.join(_BASE_DIR, provider_tag, scenario)
    os.makedirs(path, exist_ok=True)
    return path


def _score_path(provider_tag: str, scenario: str, user_id: str, lang: str, topic: str) -> str:
    d = _results_dir(provider_tag, scenario)
    return os.path.join(d, f"scores_{scenario}_{user_id}_{lang}_{_slug(topic)}.json")


def _checkpoint_path(provider_tag: str, scenario: str) -> str:
    d = _results_dir(provider_tag, scenario)
    return os.path.join(d, "checkpoint.json")


def _load_checkpoint(provider_tag: str, scenario: str) -> set:
    p = _checkpoint_path(provider_tag, scenario)
    if os.path.exists(p):
        with open(p) as f:
            return set(json.load(f).get("completed", []))
    return set()


def _save_checkpoint(provider_tag: str, scenario: str, completed: set) -> None:
    p = _checkpoint_path(provider_tag, scenario)
    with open(p, "w") as f:
        json.dump({"completed": sorted(completed), "updated_at": datetime.now().isoformat()}, f, indent=2)


def _cell_key(user_id: str, lang: str, topic: str) -> str:
    return f"{user_id}__{lang}__{_slug(topic)}"


# ── Tier Runner (T3 full system) ──────────────────────────────────────────────

def _run_session(
    profile: Dict[str, Any],
    topic: str,
    lang: str,
    scenario: str,
    provider_tag: str,
    delay: float,
) -> Dict[str, Any]:
    """
    Run a single T3 session for a given user/topic/lang/scenario.

    scenario='fnl'  → topic_str = translated topic, feedback in native lang
    scenario='nfeo' → topic_str = English topic, feedback in native lang, expect English output
    """
    manager = _get_manager()
    user_id = profile["user_id"]

    # Build topic string for this scenario
    if scenario == "fnl":
        topic_str = TOPIC_TRANSLATIONS.get(topic, {}).get(lang, topic)
    else:
        topic_str = topic  # English topic

    # Ensure profile on disk
    try:
        _ensure_profile_exists(profile)
    except Exception as e:
        return {"error": f"Profile setup failed: {e}", "rounds": [], "topic_str": topic_str}

    # Start workflow (full T3 — no eval_mode gate)
    workflow_provider = PROVIDER_WORKFLOW_MAP.get(provider_tag, provider_tag)
    try:
        start_result = manager.start_feedback_workflow(
            user_id=user_id,
            topic=topic_str,
            provider=workflow_provider,
            eval_mode=None,
        )
    except Exception as e:
        return {"error": f"start_feedback_workflow failed: {e}", "rounds": [], "topic_str": topic_str}

    if not start_result.get("success"):
        return {
            "error": start_result.get("error") or start_result.get("error_message"),
            "rounds": [],
            "topic_str": topic_str,
        }

    thread_id = start_result["thread_id"]
    initial_example = start_result.get("generated_example", "")
    rounds = [{
        "round": 0,
        "example": initial_example,
        "example_id": start_result.get("example_id"),
        "feedback_given": None,
        "loop_count": 0,
        "status": "awaiting_feedback",
    }]

    for r in range(1, NUM_FEEDBACK_ROUNDS + 1):
        feedback_text = get_ml_feedback_for_round(user_id, r, lang)
        time.sleep(delay)

        try:
            resume_result = manager.resume_feedback_workflow(
                thread_id=thread_id,
                user_feedback_text=feedback_text,
            )
        except Exception as e:
            rounds.append({"round": r, "error": str(e), "feedback_given": feedback_text})
            break

        round_data = {
            "round": r,
            "feedback_given": feedback_text,
            "status": resume_result.get("status"),
            "loop_count": resume_result.get("loop_count", 0),
            "agent_action": resume_result.get("last_agent_action"),
        }
        if resume_result.get("status") == "awaiting_feedback":
            round_data["example"] = resume_result.get("generated_example", "")
            round_data["example_id"] = resume_result.get("example_id")
        else:
            round_data["feedback_processed"] = resume_result.get("feedback_processed")

        rounds.append(round_data)

        if resume_result.get("status") == "completed":
            if r < NUM_FEEDBACK_ROUNDS:
                # Restart thread for remaining scripted rounds
                try:
                    fresh = manager.start_feedback_workflow(
                        user_id=user_id, topic=topic_str, provider=workflow_provider, eval_mode=None
                    )
                    if fresh.get("success"):
                        thread_id = fresh["thread_id"]
                    else:
                        break
                except Exception:
                    break
            else:
                break

    final = next((r["example"] for r in reversed(rounds) if r.get("example")), initial_example)
    return {
        "user_id": user_id,
        "lang": lang,
        "scenario": scenario,
        "topic": topic,
        "topic_str": topic_str,
        "thread_id": thread_id,
        "initial_example": initial_example,
        "final_example": final,
        "rounds": rounds,
        "error": None,
    }


# ── Language Match Scoring ────────────────────────────────────────────────────

# Latin-script languages where Unicode block detection is not applicable.
# detect_language() returns "en" for all Latin text (langdetect disabled to avoid
# false positives on short phrases). LangMatch is skipped for these langs in FNL.
_LATIN_SCRIPT_LANGS = {"de"}


def _score_lang_match(text: str, expected_lang: str) -> Dict[str, Any]:
    """
    Detect the language of `text` and compare to `expected_lang`.
    Returns {detected_lang, detected_name, expected_lang, match: bool, score: 0|1|None}.

    For Latin-script languages (e.g. German), Unicode block detection is unreliable
    (always returns "en"). In that case match=None and score=None — these cells are
    excluded from LangMatch aggregation.
    """
    if expected_lang in _LATIN_SCRIPT_LANGS:
        # Cannot distinguish German from English via Unicode blocks
        return {
            "detected_lang": None,
            "detected_name": None,
            "expected_lang": expected_lang,
            "match": None,
            "score": None,
            "note": "Latin-script lang — Unicode detection not applicable",
        }
    detected_code, detected_name = detect_language(text)
    match = detected_code == expected_lang
    return {
        "detected_lang": detected_code,
        "detected_name": detected_name,
        "expected_lang": expected_lang,
        "match": match,
        "score": 1.0 if match else 0.0,
    }


def _score_en_retention(text: str) -> Dict[str, Any]:
    """For NFEO: check that the output is in English."""
    return _score_lang_match(text, "en")


# ── FCR Computation ───────────────────────────────────────────────────────────

def _compute_fcr(
    run_result: Dict[str, Any],
    judge_model: str,
    judge_api_key: str,
    delay: float,
) -> List[Dict[str, Any]]:
    rounds = run_result.get("rounds", [])
    fcr_results = []
    prev_example = run_result.get("initial_example", "")
    topic = run_result.get("topic_str") or run_result.get("topic", "")

    for r in rounds:
        if r.get("round", 0) == 0:
            continue
        feedback = r.get("feedback_given", "")
        new_example = r.get("example", "")
        if not new_example or not prev_example:
            continue
        time.sleep(delay)
        compliance = judge_feedback_compliance(
            original_example=prev_example,
            regenerated_example=new_example,
            feedback_given=feedback,
            topic=topic,
            model=judge_model,
            api_key=judge_api_key,
        )
        fcr_results.append({
            "round": r["round"],
            "feedback_given": feedback,
            "compliance": compliance,
        })
        prev_example = new_example
    return fcr_results


# ── Decision Accuracy ─────────────────────────────────────────────────────────

def _compute_decision_accuracy(rounds: list, user_id: str) -> Dict[str, Any]:
    correct = 0
    total = 0
    details = []
    for r in rounds:
        round_num = r.get("round", 0)
        if round_num == 0:
            continue
        expected = get_ml_expected_decision(user_id, round_num)
        if expected is None:
            continue
        actual = r.get("agent_action")
        is_correct = actual == expected
        if is_correct:
            correct += 1
        total += 1
        details.append({
            "round": round_num,
            "expected": expected,
            "actual": actual,
            "correct": is_correct,
        })
    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total > 0 else None,
        "details": details,
    }


# ── Main Eval Cell ────────────────────────────────────────────────────────────

def _run_cell(
    profile: Dict[str, Any],
    topic: str,
    scenario: str,
    provider_tag: str,
    judge_model: str,
    judge_api_key: str,
    secondary_model: str,
    secondary_api_key: str,
    delay: float,
    judge_delay: float,
    dry_run: bool,
) -> Dict[str, Any]:
    """Run, judge, and score one (user, topic, scenario) cell."""
    lang = profile["lang"]
    user_id = profile["user_id"]

    if dry_run:
        return {"dry_run": True, "user_id": user_id, "lang": lang, "topic": topic, "scenario": scenario}

    # Run session
    run = _run_session(profile, topic, lang, scenario, provider_tag, delay)
    if run.get("error"):
        return {"error": run["error"], "user_id": user_id, "lang": lang, "topic": topic, "scenario": scenario}

    final_example = run["final_example"]
    initial_example = run["initial_example"]

    # Judge final example
    time.sleep(judge_delay)
    use_secondary = secondary_model and random.random() < 0.20
    judgment = judge_example(
        example_text=final_example,
        user_profile=profile,
        topic=run.get("topic_str", topic),
        model=judge_model,
        api_key=judge_api_key,
        secondary_model=secondary_model if use_secondary else None,
        secondary_api_key=secondary_api_key if use_secondary else None,
    )

    # Language match
    if scenario == "fnl":
        lang_check = _score_lang_match(final_example, lang)
        # Also check initial example
        lang_check_initial = _score_lang_match(initial_example, lang) if initial_example else None
    else:  # nfeo
        lang_check = _score_en_retention(final_example)
        lang_check_initial = _score_en_retention(initial_example) if initial_example else None

    # FCR
    time.sleep(judge_delay)
    fcr = _compute_fcr(run, judge_model, judge_api_key, judge_delay)

    # Decision accuracy
    dec_acc = _compute_decision_accuracy(run["rounds"], user_id)

    # LUR (loop utilization — did R1 trigger a loop?)
    r1 = next((r for r in run["rounds"] if r.get("round") == 1), None)
    lur_triggered = r1 is not None and r1.get("loop_count", 0) > 0

    record = {
        "scenario": scenario,
        "user_id": user_id,
        "lang": lang,
        "lang_name": LANG_NAMES[lang],
        "topic": topic,
        "topic_str": run.get("topic_str", topic),
        "provider": provider_tag,
        "start_mode": profile["start_mode"],
        "judgment": judgment,
        "lang_check": lang_check,
        "lang_check_initial": lang_check_initial,
        "fcr": fcr,
        "decision_accuracy": dec_acc,
        "lur_triggered": lur_triggered,
        "run": {
            "initial_example": initial_example,
            "final_example": final_example,
            "rounds": run["rounds"],
        },
        "timestamp": datetime.now().isoformat(),
    }
    return record


# ── Scenario Runner ───────────────────────────────────────────────────────────

def run_scenario(
    scenario: str,
    provider_tag: str,
    langs: List[str],
    judge_model: str,
    judge_api_key: str,
    secondary_model: Optional[str],
    secondary_api_key: Optional[str],
    delay: float = 1.5,
    judge_delay: float = 1.0,
    dry_run: bool = False,
) -> None:
    """
    Run all cells for a given scenario and provider.
    scenario: 'fnl' | 'nfeo'
    """
    profiles = [p for p in ML_PROFILES if p["lang"] in langs]
    topics = TOPICS_EN

    completed = _load_checkpoint(provider_tag, scenario)
    total_cells = len(profiles) * len(topics)

    print(f"\n{'='*65}")
    print(f"Scenario: {scenario.upper()} | Provider: {provider_tag} | Langs: {langs}")
    print(f"Profiles: {len(profiles)} | Topics: {len(topics)} | Cells: {total_cells}")
    print(f"{'='*65}\n")

    reset_manager()
    done = 0
    errors = 0

    for profile in profiles:
        for topic in topics:
            lang = profile["lang"]
            user_id = profile["user_id"]
            cell_key = _cell_key(user_id, lang, topic)

            if cell_key in completed:
                print(f"  [SKIP] {user_id} | {lang} | {topic[:35]}")
                done += 1
                continue

            out_path = _score_path(provider_tag, scenario, user_id, lang, topic)
            print(f"  [{done+1}/{total_cells}] {user_id} | {lang} | {scenario} | {topic[:35]} ...", flush=True)

            record = _run_cell(
                profile=profile,
                topic=topic,
                scenario=scenario,
                provider_tag=provider_tag,
                judge_model=judge_model,
                judge_api_key=judge_api_key,
                secondary_model=secondary_model,
                secondary_api_key=secondary_api_key,
                delay=delay,
                judge_delay=judge_delay,
                dry_run=dry_run,
            )

            if not dry_run:
                if record.get("error"):
                    print(f"    [ERROR] {record['error']}")
                    errors += 1
                else:
                    composite = record.get("judgment", {}).get("composite")
                    lm = record.get("lang_check", {}).get("match")
                    comp_str = f"{composite:.3f}" if composite is not None else "N/A"
                    print(f"    Composite={comp_str}  LangMatch={lm}  DA={record.get('decision_accuracy', {}).get('accuracy')}")
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(record, f, indent=2, ensure_ascii=False)
                    completed.add(cell_key)
                    _save_checkpoint(provider_tag, scenario, completed)

            done += 1

    print(f"\n{scenario.upper()} complete: {done - errors} ok, {errors} errors.")


# ── English Baseline (for Δ vs EN comparison) ─────────────────────────────────

def run_en_baseline(
    provider_tag: str,
    judge_model: str,
    judge_api_key: str,
    secondary_model: Optional[str],
    secondary_api_key: Optional[str],
    delay: float = 1.5,
    judge_delay: float = 1.0,
    dry_run: bool = False,
    langs: Optional[List[str]] = None,
) -> None:
    """
    Run T3 English baseline for ML profiles (topic in English, feedback in English F3/F2).
    Saves to eval/results/multilingual/<provider>/en_baseline/
    langs: if provided, only run profiles whose lang is in this list (used for Sarvam Indic-only).
    """
    from eval.multilingual.ml_synthetic_profiles import ML_FEEDBACK as _ML_FB

    scenario = "en_baseline"
    profiles = [p for p in ML_PROFILES if langs is None or p["lang"] in langs]
    topics = TOPICS_EN
    completed = _load_checkpoint(provider_tag, scenario)
    total_cells = len(profiles) * len(topics)

    print(f"\n{'='*65}")
    print(f"Scenario: EN_BASELINE | Provider: {provider_tag}")
    print(f"Profiles: {len(profiles)} | Topics: {len(topics)} | Cells: {total_cells}")
    print(f"{'='*65}\n")

    reset_manager()
    done = 0
    errors = 0

    for profile in profiles:
        for topic in topics:
            lang = profile["lang"]
            user_id = profile["user_id"]
            cell_key = _cell_key(user_id, lang, topic)

            if cell_key in completed:
                done += 1
                continue

            out_path = _score_path(provider_tag, scenario, user_id, lang, topic)
            print(f"  [{done+1}/{total_cells}] {user_id} | en_baseline | {topic[:35]} ...", flush=True)

            if dry_run:
                done += 1
                continue

            # Use English feedback for baseline
            run = _run_session(profile, topic, "en", scenario, provider_tag, delay)
            if run.get("error"):
                print(f"    [ERROR] {run['error']}")
                errors += 1
                done += 1
                continue

            final_example = run["final_example"]
            time.sleep(judge_delay)
            use_secondary = secondary_model and random.random() < 0.20
            judgment = judge_example(
                example_text=final_example,
                user_profile=profile,
                topic=topic,
                model=judge_model,
                api_key=judge_api_key,
                secondary_model=secondary_model if use_secondary else None,
                secondary_api_key=secondary_api_key if use_secondary else None,
            )

            record = {
                "scenario": scenario,
                "user_id": user_id,
                "lang": lang,
                "topic": topic,
                "provider": provider_tag,
                "start_mode": profile["start_mode"],
                "judgment": judgment,
                "run": {
                    "initial_example": run["initial_example"],
                    "final_example": final_example,
                    "rounds": run["rounds"],
                },
                "timestamp": datetime.now().isoformat(),
            }

            composite = judgment.get("composite")
            comp_str = f"{composite:.3f}" if composite is not None else "N/A"
            print(f"    Composite={comp_str}")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            completed.add(cell_key)
            _save_checkpoint(provider_tag, scenario, completed)
            done += 1

    print(f"\nEN_BASELINE complete: {done - errors} ok, {errors} errors.")


# ── Analysis ──────────────────────────────────────────────────────────────────

def _load_scores(provider_tag: str, scenario: str) -> List[Dict[str, Any]]:
    d = _results_dir(provider_tag, scenario)
    records = []
    for fn in os.listdir(d):
        if fn.startswith("scores_") and fn.endswith(".json"):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                records.append(json.load(f))
    return records


def _mean(values: List[float]) -> Optional[float]:
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def _group_stats(records: List[Dict], lang_group: List[str]) -> Dict[str, Any]:
    """Compute group-level metrics for a set of languages."""
    subset = [r for r in records if r.get("lang") in lang_group]
    composites = [r.get("judgment", {}).get("composite") for r in subset]
    # Exclude None scores (Latin-script langs where Unicode detection is inapplicable)
    lang_matches = [r.get("lang_check", {}).get("score") for r in subset
                    if r.get("lang_check", {}).get("score") is not None]
    fcr3_vals = []
    fcr4_vals = []
    lur_vals = []
    da_vals = []
    kappa_pairs = []

    for r in subset:
        fcr = r.get("fcr", [])
        # Multilingual FCR uses {compliant: bool, compliance_score: int} schema
        # FCR@3: compliance_score >= 3; FCR@4: compliance_score >= 4 (== compliant==True)
        compliant3 = [f for f in fcr if (f.get("compliance", {}).get("compliance_score") or 0) >= 3]
        compliant4 = [f for f in fcr if f.get("compliance", {}).get("compliant")]
        if fcr:
            fcr3_vals.append(len(compliant3) / len(fcr))
            fcr4_vals.append(len(compliant4) / len(fcr))
        lur_vals.append(1.0 if r.get("lur_triggered") else 0.0)
        da = r.get("decision_accuracy", {}).get("accuracy")
        if da is not None:
            da_vals.append(da)
        # Collect secondary judge scores for kappa
        sec = r.get("judgment", {}).get("secondary")
        if sec and sec.get("scores"):
            prim = r.get("judgment", {}).get("scores", {})
            kappa_pairs.append((prim, sec["scores"]))

    # Compute Cohen's kappa (PF axis — main per-use axis)
    kappa = None
    if len(kappa_pairs) >= 5:
        try:
            from sklearn.metrics import cohen_kappa_score
            pf_prim = [p.get("PF", 3) for p, _ in kappa_pairs]
            pf_sec = [s.get("PF", 3) for _, s in kappa_pairs]
            kappa = cohen_kappa_score(pf_prim, pf_sec)
        except Exception:
            pass

    return {
        "n": len(subset),
        "composite_mean": _mean(composites),
        "composite_values": composites,
        "lang_match_mean": _mean(lang_matches),
        "fcr3_mean": _mean(fcr3_vals),
        "fcr4_mean": _mean(fcr4_vals),
        "lur_mean": _mean(lur_vals),
        "decision_accuracy_mean": _mean(da_vals),
        "kappa_pf": kappa,
        "kappa_n": len(kappa_pairs),
    }


def _paired_composites(
    scenario_records: List[Dict],
    baseline_records: List[Dict],
    lang_group: List[str],
) -> List[Tuple[float, float]]:
    """
    Build properly matched (scenario, baseline) composite pairs keyed by (user_id, topic).
    This guarantees correct pairing regardless of os.listdir() ordering.
    """
    sc_map = {
        (r["user_id"], r["topic"]): r.get("judgment", {}).get("composite")
        for r in scenario_records if r.get("lang") in lang_group
    }
    en_map = {
        (r["user_id"], r["topic"]): r.get("judgment", {}).get("composite")
        for r in baseline_records if r.get("lang") in lang_group
    }
    pairs = []
    for key in sorted(sc_map):
        sc_val = sc_map.get(key)
        en_val = en_map.get(key)
        if sc_val is not None and en_val is not None:
            pairs.append((sc_val, en_val))
    return pairs


def _wilcoxon_group(pairs: List[Tuple[float, float]]) -> Dict[str, Any]:
    """Paired Wilcoxon signed-rank test on pre-matched (scenario, baseline) pairs."""
    try:
        from scipy.stats import wilcoxon
        import numpy as np
        if len(pairs) < 5:
            return {"n_pairs": len(pairs), "error": "insufficient data"}
        diffs = [a - b for a, b in pairs]
        stat, p = wilcoxon(diffs, alternative="two-sided")
        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs))
        d = mean_diff / std_diff if std_diff > 0 else 0.0
        return {
            "n_pairs": len(pairs),
            "mean_diff": mean_diff,
            "statistic": float(stat),
            "p_value": float(p),
            "cohens_d": d,
            "significant_p05": p < 0.05,
            "significant_p01": p < 0.01,
        }
    except Exception as e:
        return {"error": str(e)}


def analyze(provider_tag: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load all results for a provider and compute:
    - Per-scenario per-language-group metrics
    - FNL vs EN-baseline Wilcoxon (Indic group, Foreign group)
    - NFEO vs EN-baseline Wilcoxon
    - FCR, LUR, PPU, LangMatch, EN-Retention, κ
    """
    print(f"\nAnalyzing: {provider_tag}")

    fnl_records = _load_scores(provider_tag, "fnl")
    nfeo_records = _load_scores(provider_tag, "nfeo")
    en_records = _load_scores(provider_tag, "en_baseline")

    print(f"  FNL records: {len(fnl_records)}")
    print(f"  NFEO records: {len(nfeo_records)}")
    print(f"  EN baseline records: {len(en_records)}")

    results = {"provider": provider_tag, "generated_at": datetime.now().isoformat()}

    for scenario, records in [("fnl", fnl_records), ("nfeo", nfeo_records)]:
        s = {}
        for lang_group_name, lang_group in [("indic", INDIC_LANGS), ("foreign", FOREIGN_LANGS), ("all", ALL_LANGS)]:
            s[lang_group_name] = _group_stats(records, lang_group)

        # Per-language descriptive
        per_lang = {}
        for lang in ALL_LANGS:
            per_lang[lang] = _group_stats(records, [lang])
        s["per_language"] = per_lang

        # Wilcoxon vs EN baseline — paired by (user_id, topic), α'=0.025 (Bonferroni, 2 groups)
        pairs_indic = _paired_composites(records, en_records, INDIC_LANGS)
        pairs_foreign = _paired_composites(records, en_records, FOREIGN_LANGS)
        s["wilcoxon_vs_en_indic"] = _wilcoxon_group(pairs_indic)
        s["wilcoxon_vs_en_foreign"] = _wilcoxon_group(pairs_foreign)
        s["wilcoxon_bonferroni_alpha"] = 0.025  # Bonferroni for 2 group comparisons

        results[scenario] = s

    # EN baseline summary
    results["en_baseline"] = {
        "indic": _group_stats(en_records, INDIC_LANGS),
        "foreign": _group_stats(en_records, FOREIGN_LANGS),
        "all": _group_stats(en_records, ALL_LANGS),
    }

    # Save
    if output_path is None:
        d = _results_dir(provider_tag, "analysis")
        output_path = os.path.join(d, f"analysis_multilingual_{provider_tag}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            return super().default(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)
    print(f"  Analysis saved: {output_path}")

    # Print summary
    _print_summary(results)
    return results


def _print_summary(results: Dict[str, Any]) -> None:
    provider = results.get("provider", "?")
    print(f"\n{'='*65}")
    print(f"MULTILINGUAL ANALYSIS - {provider.upper()}")
    print(f"{'='*65}")
    for scenario in ["fnl", "nfeo"]:
        if scenario not in results:
            continue
        s = results[scenario]
        print(f"\n[{scenario.upper()}]")
        for group in ["indic", "foreign", "all"]:
            g = s.get(group, {})
            composite = g.get("composite_mean")
            lm = g.get("lang_match_mean")
            fcr3 = g.get("fcr3_mean")
            lur = g.get("lur_mean")
            n = g.get("n", 0)
            comp_s = f"{composite:.3f}" if composite is not None else "N/A"
            lm_s   = f"{lm:.3f}"        if lm        is not None else "N/A"
            fcr_s  = f"{fcr3:.3f}"      if fcr3      is not None else "N/A"
            lur_s  = f"{lur:.3f}"       if lur       is not None else "N/A"
            print(f"  {group:<10} n={n:<4} Composite={comp_s:<8} LangMatch={lm_s:<8} FCR@3={fcr_s:<8} LUR={lur_s}")
        wil_i = s.get("wilcoxon_vs_en_indic", {})
        wil_f = s.get("wilcoxon_vs_en_foreign", {})
        md_i = wil_i.get("mean_diff"); p_i = wil_i.get("p_value")
        md_f = wil_f.get("mean_diff"); p_f = wil_f.get("p_value")
        mdi_s = f"{md_i:.3f}" if md_i is not None else "N/A"
        pi_s  = f"{p_i:.4f}"  if p_i  is not None else "N/A"
        mdf_s = f"{md_f:.3f}" if md_f is not None else "N/A"
        pf_s  = f"{p_f:.4f}"  if p_f  is not None else "N/A"
        print(f"  Wilcoxon vs EN (Indic) : Delta={mdi_s}  p={pi_s}")
        print(f"  Wilcoxon vs EN (Foreign): Delta={mdf_s}  p={pf_s}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(description="AdaCraft Multilingual Evaluation Runner")
    parser.add_argument("--scenarios", nargs="+", default=["fnl", "nfeo", "en_baseline"],
                        choices=["fnl", "nfeo", "en_baseline"],
                        help="Scenarios to run")
    parser.add_argument("--providers", nargs="+", default=["gpt5nano"],
                        help="Provider tags: gpt5nano, deepseek, sarvam")
    parser.add_argument("--langs", nargs="+", default=ALL_LANGS,
                        choices=ALL_LANGS, help="Languages to include")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between API calls (seconds)")
    parser.add_argument("--judge-delay", type=float, default=1.0, help="Delay between judge calls")
    parser.add_argument("--judge-model", type=str, default=None, help="Override judge model")
    parser.add_argument("--judge-api-key", type=str, default=None, help="Judge API key")
    parser.add_argument("--secondary-model", type=str, default=None, help="Secondary judge model (OpenRouter)")
    parser.add_argument("--secondary-api-key", type=str, default=None, help="Secondary judge API key")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without making API calls")
    parser.add_argument("--seed-warm", action="store_true", help="Seed warm users before running")
    parser.add_argument("--analyze-only", action="store_true", help="Run analysis only, no new evals")
    parser.add_argument("--provider", type=str, default=None, help="Provider for --analyze-only")
    return parser.parse_args()


def main():
    args = _parse_args()

    # Load API keys from environment
    import dotenv
    dotenv.load_dotenv()
    judge_api_key = args.judge_api_key or os.environ.get("OPENAI_API_KEY")
    secondary_api_key = args.secondary_api_key or os.environ.get("OPENROUTER_JUDGE_API_KEY")
    secondary_model = args.secondary_model or "openrouter:meta-llama/llama-3.3-70b-instruct"

    if args.analyze_only:
        provider = args.provider or (args.providers[0] if args.providers else "gpt5nano")
        analyze(provider)
        return

    if args.seed_warm:
        seed_ml_warm_users()

    for provider_tag in args.providers:
        # Determine judge model
        judge_model = args.judge_model or PROVIDER_MODEL_MAP.get(provider_tag, "gpt-4.1-nano")

        # Determine langs (Sarvam only for Indic)
        if provider_tag == "sarvam":
            active_langs = [l for l in args.langs if l in INDIC_LANGS]
        else:
            active_langs = args.langs

        if not active_langs:
            print(f"[SKIP] {provider_tag} — no applicable languages in {args.langs}")
            continue

        for scenario in args.scenarios:
            if scenario == "en_baseline":
                run_en_baseline(
                    provider_tag=provider_tag,
                    judge_model=judge_model,
                    judge_api_key=judge_api_key,
                    secondary_model=secondary_model,
                    secondary_api_key=secondary_api_key,
                    delay=args.delay,
                    judge_delay=args.judge_delay,
                    dry_run=args.dry_run,
                    langs=active_langs,
                )
            else:
                run_scenario(
                    scenario=scenario,
                    provider_tag=provider_tag,
                    langs=active_langs,
                    judge_model=judge_model,
                    judge_api_key=judge_api_key,
                    secondary_model=secondary_model,
                    secondary_api_key=secondary_api_key,
                    delay=args.delay,
                    judge_delay=args.judge_delay,
                    dry_run=args.dry_run,
                )

        # Run analysis after each provider
        try:
            analyze(provider_tag)
        except Exception as e:
            print(f"[WARN] Analysis failed for {provider_tag}: {e}")


if __name__ == "__main__":
    main()
