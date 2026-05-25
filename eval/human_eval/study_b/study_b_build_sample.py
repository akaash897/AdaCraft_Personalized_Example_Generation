"""
Study B — Build Sample Manifest
================================
Extracts the 30 pre-specified examples (T0 baseline + T3 final + feedback
history) from the ablation results, following the stratification table:

    user_01: NS=DS  CB=GPT  CI=DS  PT=GPT   (cold · student    · Berlin)
    user_02: NS=GPT CB=DS   CI=GPT PT=DS    (cold · nurse      · Lagos)
    user_03: NS=DS  CB=GPT  CI=DS  PT=GPT   (cold · researcher · São Paulo)
    user_04: NS=GPT CB=DS   CI=GPT PT=DS    (cold · engineer   · Tokyo)
    user_05: NS=DS  CB=GPT  CI=DS  PT=GPT   (warm · student    · Berlin)
    user_06: NS=GPT CB=DS   CI=GPT PT=DS    (warm · nurse      · Lagos)
    user_07: NS=DS  CB=GPT  CI=—   PT=DS    (warm · researcher · São Paulo, CI dropped)
    user_08: NS=GPT CB=DS   CI=—   PT=GPT   (warm · engineer   · Tokyo, CI dropped)

Run:
    python eval/human_eval/study_b_build_sample.py

Outputs:
    eval/human_eval/results/study_b/sample_manifest.json
"""

import json
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent.parent.parent
RESULTS_DIR = ROOT / "eval" / "ablation" / "results"
OUT_DIR     = ROOT / "eval" / "human_eval" / "study_b" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AXES = ["PF", "CC", "CA", "PC", "DA"]

# Fixed stratification table: (user_id, topic_slug, provider)
SAMPLE_CELLS = [
    ("eval_user_01", "natural_selection",  "deepseek"),
    ("eval_user_01", "cognitive_bias",     "gpt5nano"),
    ("eval_user_01", "compound_interest",  "deepseek"),
    ("eval_user_01", "plate_tectonics",    "gpt5nano"),

    ("eval_user_02", "natural_selection",  "gpt5nano"),
    ("eval_user_02", "cognitive_bias",     "deepseek"),
    ("eval_user_02", "compound_interest",  "gpt5nano"),
    ("eval_user_02", "plate_tectonics",    "deepseek"),

    ("eval_user_03", "natural_selection",  "deepseek"),
    ("eval_user_03", "cognitive_bias",     "gpt5nano"),
    ("eval_user_03", "compound_interest",  "deepseek"),
    ("eval_user_03", "plate_tectonics",    "gpt5nano"),

    ("eval_user_04", "natural_selection",  "gpt5nano"),
    ("eval_user_04", "cognitive_bias",     "deepseek"),
    ("eval_user_04", "compound_interest",  "gpt5nano"),
    ("eval_user_04", "plate_tectonics",    "deepseek"),

    ("eval_user_05", "natural_selection",  "deepseek"),
    ("eval_user_05", "cognitive_bias",     "gpt5nano"),
    ("eval_user_05", "compound_interest",  "deepseek"),
    ("eval_user_05", "plate_tectonics",    "gpt5nano"),

    ("eval_user_06", "natural_selection",  "gpt5nano"),
    ("eval_user_06", "cognitive_bias",     "deepseek"),
    ("eval_user_06", "compound_interest",  "gpt5nano"),
    ("eval_user_06", "plate_tectonics",    "deepseek"),

    # user_07: CI dropped (missing FCR data)
    ("eval_user_07", "natural_selection",  "deepseek"),
    ("eval_user_07", "cognitive_bias",     "gpt5nano"),
    ("eval_user_07", "plate_tectonics",    "deepseek"),

    # user_08: CI dropped (missing FCR data)
    ("eval_user_08", "natural_selection",  "gpt5nano"),
    ("eval_user_08", "cognitive_bias",     "deepseek"),
    ("eval_user_08", "plate_tectonics",    "gpt5nano"),
]

TOPIC_LABEL = {
    "natural_selection": "Natural Selection",
    "cognitive_bias":    "Cognitive Bias",
    "compound_interest": "Compound Interest",
    "plate_tectonics":   "Plate Tectonics",
}


# ─────────────────────────────────────────────────────────────────────────────
def load_scores(provider: str, tier: str, user_id: str, topic_slug: str) -> dict | None:
    fname = f"scores_{tier}__{user_id}__{topic_slug}.json"
    path  = RESULTS_DIR / provider / fname
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_feedback_rounds(t3_run: dict) -> list[dict]:
    """
    Return rounds where the learner gave non-null, non-accept feedback.
    Each entry: {"round": int, "feedback": str, "agent_action": str}
    """
    rounds = []
    for r in t3_run.get("rounds", []):
        fb = r.get("feedback_given")
        if not fb:
            continue
        rounds.append({
            "round":        r["round"],
            "feedback":     fb,
            "agent_action": r.get("agent_action", ""),
        })
    return rounds


def compute_llm_fcr(fcr_results: list[dict]) -> float | None:
    """
    Mean compliance_score across all feedback rounds (1-5 scale).
    Returns None if no FCR data is available.
    """
    scores = [
        r["compliance"]["compliance_score"]
        for r in fcr_results
        if isinstance(r.get("compliance"), dict)
        and r["compliance"].get("compliance_score") is not None
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


def extract_llm_scores(judgment: dict | None) -> dict | None:
    """Extract {PF, CC, CA, PC, DA} as floats from a judgment block."""
    if not judgment or not judgment.get("scores"):
        return None
    raw = judgment["scores"]
    scores = {ax: max(1.0, min(5.0, float(raw[ax]))) for ax in AXES if ax in raw}
    if len(scores) < 5:
        return None
    return scores


# ─────────────────────────────────────────────────────────────────────────────
def build_manifest() -> list[dict]:
    manifest = []
    missing  = []

    for idx, (user_id, topic_slug, provider) in enumerate(SAMPLE_CELLS, start=1):
        ex_id = f"EX{idx:02d}"
        topic = TOPIC_LABEL[topic_slug]

        t0 = load_scores(provider, "t0", user_id, topic_slug)
        t3 = load_scores(provider, "t3", user_id, topic_slug)

        if t0 is None or t3 is None:
            missing.append(ex_id)
            print(f"  MISSING: {ex_id} — {provider}/{user_id}/{topic_slug}")
            continue

        t3_run = t3.get("run", {})
        t0_run = t0.get("run", {})

        baseline_example = t0_run.get("initial_example", "")
        final_example    = t3_run.get("final_example", "")
        feedback_rounds  = extract_feedback_rounds(t3_run)

        llm_t0_scores = extract_llm_scores(t0.get("initial_judgment"))
        llm_t3_scores = extract_llm_scores(t3.get("final_judgment") or t3.get("initial_judgment"))
        llm_fcr       = compute_llm_fcr(t3.get("fcr_results", []))

        profile = t3.get("profile", t0.get("profile", {}))

        entry = {
            "example_id":       ex_id,
            "user_id":          user_id,
            "topic":            topic,
            "provider":         provider,

            # Learner profile
            "profile": {
                "name":               profile.get("name", ""),
                "role":               profile.get("role", ""),
                "location":           profile.get("location", ""),
                "learning_style":     profile.get("learning_style", ""),
                "complexity":         profile.get("complexity", ""),
                "start_mode":         profile.get("start_mode", ""),
                "cultural_background": profile.get("cultural_background", ""),
            },

            # Example texts
            "baseline_example":  baseline_example,
            "final_example":     final_example,
            "feedback_rounds":   feedback_rounds,

            # LLM judge scores (for human vs LLM agreement analysis)
            "llm_t0_scores":    llm_t0_scores,
            "llm_t3_scores":    llm_t3_scores,

            # Automated FCR for cross-validation against human FC
            "llm_fcr_mean":     llm_fcr,
            "llm_fcr_n_rounds": len(t3.get("fcr_results", [])),
        }

        manifest.append(entry)

    if missing:
        print(f"\nWARNING: {len(missing)} examples could not be loaded: {missing}")
    else:
        print(f"All {len(manifest)} examples loaded successfully.")

    return manifest


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("Building Study B sample manifest...")
    manifest = build_manifest()

    out_path = OUT_DIR / "sample_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nManifest written -> {out_path}")
    print(f"  {len(manifest)} examples")

    # Quick summary
    cold = sum(1 for e in manifest if e["profile"]["start_mode"] == "cold")
    warm = sum(1 for e in manifest if e["profile"]["start_mode"] == "warm")
    ds   = sum(1 for e in manifest if e["provider"] == "deepseek")
    gpt  = sum(1 for e in manifest if e["provider"] == "gpt5nano")
    print(f"  Cold: {cold}  Warm: {warm}  DeepSeek: {ds}  GPT-5-nano: {gpt}")

    missing_fcr = [e["example_id"] for e in manifest if e["llm_fcr_mean"] is None]
    if missing_fcr:
        print(f"  WARNING: No FCR data for: {missing_fcr}")

    missing_baseline = [e["example_id"] for e in manifest if not e["baseline_example"]]
    missing_final    = [e["example_id"] for e in manifest if not e["final_example"]]
    if missing_baseline:
        print(f"  WARNING: Missing baseline text for: {missing_baseline}")
    if missing_final:
        print(f"  WARNING: Missing final text for: {missing_final}")


if __name__ == "__main__":
    main()
