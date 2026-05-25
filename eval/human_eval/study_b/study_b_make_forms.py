"""
Study B — Make Annotation Package
===================================
Reads sample_manifest.json and generates:

  results/study_b/
    annotation_package/
      rubric_b.md                  — full rubric with all 8 axes
      example_EX01.md … EX30.md   — one formatted card per example
    scores_template_B1.json        — blank score sheet per annotator (B1–B5)
    all_scores_template.json       — merged blank template (all 5 annotators)
    scores_template.csv            — flat CSV for manual entry

Run:
    python eval/human_eval/study_b_make_forms.py

Requires sample_manifest.json to exist (run study_b_build_sample.py first).
"""

import csv
import json
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = ROOT / "eval" / "human_eval" / "study_b" / "results"
PKG_DIR = OUT_DIR / "annotation_package"
PKG_DIR.mkdir(parents=True, exist_ok=True)

ANNOTATORS = [
    {"id": "B1", "background": "STEM (engineering / CS / physics)"},
    {"id": "B2", "background": "Social sciences / humanities"},
    {"id": "B3", "background": "Life sciences / medicine"},
    {"id": "B4", "background": "Instructional design / edtech"},
    {"id": "B5", "background": "Any field — generalist educator"},
]

AXES_7    = ["PF", "CC", "CA", "PC", "DA", "FC", "IS"]   # 1-5 integer axes
AXES_IP   = "IP"                                           # T0 / T3 binary


# ─────────────────────────────────────────────────────────────────────────────
RUBRIC_TEXT = """\
# Study B — Contextual Full-Rubric Evaluation
## Annotator Rubric

You will score **30 educational examples** on **8 dimensions**.

For each example you will see:
- **PROFILE** — the learner's name, role, location, learning style, complexity level
- **TOPIC** — the concept being taught
- **BASELINE EXAMPLE (T0)** — a generic example generated *without* any personalisation
- **FEEDBACK HISTORY** — the learner's natural-language feedback given between rounds
- **FINAL EXAMPLE (T3)** — the example after the system processed all feedback

Score each axis **independently** (do not let one axis influence another).
You are **blind** to which AI system generated the examples.

---

## Axes (PF · CC · CA · PC · DA)
*Same five axes as the automated judge — score the **FINAL EXAMPLE**.*

### PF — Personalization Fidelity
*Does the final example feel genuinely tailored to this specific learner?*

| Score | Meaning |
|-------|---------|
| 1 | Completely generic — no trace of the learner's profile |
| 2 | Weak — one surface element (e.g. name only), feels templated |
| 3 | Partial — references background or role, but misses learning style or complexity |
| 4 | Good — clearly adapted to role, background, and complexity; minor gaps |
| 5 | Excellent — every profile dimension naturally woven in |

---

### CC — Complexity Calibration
*Is the depth and vocabulary appropriate for the learner's stated complexity level?*

| Score | Meaning |
|-------|---------|
| 1 | Wildly mismatched |
| 2 | Notably off — too dense or too simplistic |
| 3 | Roughly appropriate, some terms miss the mark |
| 4 | Well-matched — vocabulary and depth suit the learner |
| 5 | Perfect calibration — written precisely for this level |

---

### CA — Conceptual Accuracy
*Is the factual content correct?*

| Score | Meaning |
|-------|---------|
| 1 | Major factual errors that would mislead the learner |
| 2 | Significant inaccuracies or misleading simplifications |
| 3 | Mostly correct, minor error or imprecise statement |
| 4 | Accurate with very minor oversimplification (acceptable) |
| 5 | Completely accurate — no factual errors |

---

### PC — Pedagogical Clarity
*Is the example easy to follow and structured to support learning?*

| Score | Meaning |
|-------|---------|
| 1 | Confusing or incoherent |
| 2 | Hard to follow — jumps around or buries the key insight |
| 3 | Readable but key insight not clearly highlighted |
| 4 | Clear structure, key insight emerges naturally |
| 5 | Exemplary — logical flow, key insight explicit |

---

### DA — Domain Appropriateness
*Are the analogies and framing right for this subject area?*

| Score | Meaning |
|-------|---------|
| 1 | Analogies off-topic or actively misleading |
| 2 | Weak fit — generic analogies that could belong to any topic |
| 3 | Adequate — standard textbook choices |
| 4 | Good — domain-appropriate and engaging |
| 5 | Excellent — well-chosen, domain-specific, concept-reinforcing |

---

## Additional Axes (FC · IS · IP)
*These axes require comparing baseline -> final, using the feedback history.*

### FC — Feedback Compliance
*How well does the final example address the learner's feedback?*

Read the feedback history carefully. Score the **degree to which the final example
reflects the changes the learner requested across all rounds.**

| Score | Meaning |
|-------|---------|
| 1 | Final example ignores the feedback entirely |
| 2 | Minimal acknowledgement — one small surface change |
| 3 | Partial — addresses some requests but misses key ones |
| 4 | Good — most feedback addressed; minor omissions |
| 5 | Excellent — all feedback incorporated naturally and faithfully |

---

### IS — Improvement Score
*How much did the example improve from baseline to final?*

Compare the BASELINE EXAMPLE directly against the FINAL EXAMPLE.
Score the **magnitude of pedagogical improvement** you observe.

| Score | Meaning |
|-------|---------|
| 1 | Final is worse or identical to baseline |
| 2 | Marginal improvement — barely distinguishable |
| 3 | Moderate improvement — noticeably better in one or two dimensions |
| 4 | Substantial improvement — clearly better for this learner |
| 5 | Transformative improvement — the final is dramatically more suitable |

---

### IP — Informed Preference
*Which example better helps this learner understand the concept?*

After reading both examples **with the learner's profile in mind**, choose:

- **T3** — the final example is better for this learner
- **T0** — the baseline example is better (or they are equivalent)

Note: Because the feedback history reveals the ordering, this choice is not blind.
That limitation is noted in the study design.

---

## Anchor Examples

**Anchor A** — PF=5, IS=5, IP=T3
> A learner profile says: Nurse, Lagos, Nigeria; complexity=high; style=analogy-based.
> Baseline: A generic explanation of exponential growth using population statistics.
> Final (after "use medical examples"): An ICU example about antibiotic-resistant bacteria
> doubling every 20 min, with nursing-specific implications for dosage timing.
> — Every profile dimension used; dramatic improvement; clear T3 preference.

**Anchor B** — PF=2, IS=2, IP=T0
> A learner profile says: Engineer, Tokyo; complexity=medium; style=step-by-step.
> Baseline: A clear numbered list explaining how natural selection works in moths.
> Final (after "relate to engineering"): An awkward paragraph vaguely comparing selection
> to "quality control" with no concrete steps.
> — Profile barely used; final is less clear than baseline; T0 preferred.

---

## Notes
- Score PF on the **final** example only — the baseline is intentionally generic.
- FC requires you to read all feedback rounds before scoring.
- If the learner gave no feedback (only one round), score FC = 5 only if the final
  example is also excellent on PF; otherwise score FC = N/A -> leave as 3 (neutral).
- CA does not require domain expertise; flag obvious errors from context.
"""


# ─────────────────────────────────────────────────────────────────────────────
def format_profile(profile: dict) -> str:
    parts = [
        f"Name: **{profile.get('name', '?')}**",
        f"Role: {profile.get('role', '?')}",
        f"Location: {profile.get('location', '?')}",
        f"Background: {profile.get('cultural_background', '?')}",
        f"Learning style: {profile.get('learning_style', '?')}",
        f"Complexity: {profile.get('complexity', '?')}",
        f"Start mode: {profile.get('start_mode', '?')}",
    ]
    return "  \n".join(parts)


def format_example_card(entry: dict) -> str:
    ex_id   = entry["example_id"]
    topic   = entry["topic"]
    profile = entry["profile"]
    fb_rds  = entry.get("feedback_rounds", [])

    lines = [
        f"# {ex_id} — {topic}",
        "",
        "---",
        "",
        "## PROFILE",
        "",
        format_profile(profile),
        "",
        "---",
        "",
        "## TOPIC",
        "",
        topic,
        "",
        "---",
        "",
        "## BASELINE EXAMPLE  *(T0 — no personalisation)*",
        "",
    ]

    baseline = entry.get("baseline_example", "").strip()
    lines.append(baseline if baseline else "*(not available)*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## FEEDBACK HISTORY")
    lines.append("")

    if fb_rds:
        for r in fb_rds:
            lines.append(f"**Round {r['round']}:** \"{r['feedback']}\"")
            lines.append("")
    else:
        lines.append("*(no feedback rounds — learner accepted the initial example)*")
        lines.append("")

    lines += [
        "---",
        "",
        "## FINAL EXAMPLE  *(T3 — after feedback loop)*",
        "",
    ]

    final = entry.get("final_example", "").strip()
    lines.append(final if final else "*(not available)*")
    lines.append("")
    lines += [
        "---",
        "",
        "## SCORE SHEET",
        "",
        f"**Example ID:** {ex_id}",
        "",
        "| Axis | Question | Your Score |",
        "|------|----------|------------|",
        "| PF   | Does the final example feel tailored to this learner? | ___ |",
        "| CC   | Is the complexity appropriate for their level? | ___ |",
        "| CA   | Is the content factually accurate? | ___ |",
        "| PC   | Is it pedagogically clear and well-structured? | ___ |",
        "| DA   | Are the analogies appropriate for this domain? | ___ |",
        "| FC   | How well does the final example address the feedback given? | ___ |",
        "| IS   | How much did the example improve from baseline to final? | ___ |",
        "| IP   | Which better helps this learner — Baseline (T0) or Final (T3)? | T0 / T3 |",
        "",
        "*Scores PF–IS: integer 1–5. IP: circle T0 or T3.*",
        "",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
def make_blank_scores(annotator_id: str, manifest: list[dict]) -> dict:
    return {
        "annotator_id": annotator_id,
        "scores": [
            {
                "example_id": e["example_id"],
                "PF": None, "CC": None, "CA": None, "PC": None, "DA": None,
                "FC": None, "IS": None, "IP": None,
            }
            for e in manifest
        ],
    }


def make_csv_template(manifest: list[dict]) -> list[list]:
    header = ["annotator_id", "example_id", "user_id", "topic",
              "provider", "start_mode", "PF", "CC", "CA", "PC", "DA", "FC", "IS", "IP"]
    rows   = [header]
    for ann in ANNOTATORS:
        for e in manifest:
            rows.append([
                ann["id"],
                e["example_id"],
                e["user_id"],
                e["topic"],
                e["provider"],
                e["profile"].get("start_mode", ""),
                "", "", "", "", "", "", "", "",
            ])
    return rows


# ─────────────────────────────────────────────────────────────────────────────
def main():
    manifest_path = OUT_DIR / "sample_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"sample_manifest.json not found at {manifest_path}\n"
            "Run study_b_build_sample.py first."
        )

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Loaded {len(manifest)} examples from manifest.")

    # 1. Write rubric
    rubric_path = PKG_DIR / "rubric_b.md"
    rubric_path.write_text(RUBRIC_TEXT, encoding="utf-8")
    print(f"  Written: {rubric_path.name}")

    # 2. Write per-example annotation cards
    for entry in manifest:
        card = format_example_card(entry)
        card_path = PKG_DIR / f"example_{entry['example_id']}.md"
        card_path.write_text(card, encoding="utf-8")
    print(f"  Written: {len(manifest)} example cards -> {PKG_DIR.name}/")

    # 3. Per-annotator blank score sheets (JSON)
    for ann in ANNOTATORS:
        sheet      = make_blank_scores(ann["id"], manifest)
        sheet_path = OUT_DIR / f"scores_template_{ann['id']}.json"
        with open(sheet_path, "w", encoding="utf-8") as f:
            json.dump(sheet, f, indent=2)
    print(f"  Written: {len(ANNOTATORS)} per-annotator score templates (B1–B5).")

    # 4. Merged all-annotators template
    all_template = {ann["id"]: make_blank_scores(ann["id"], manifest)["scores"]
                    for ann in ANNOTATORS}
    merged_path = OUT_DIR / "all_scores_template.json"
    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(all_template, f, indent=2)
    print(f"  Written: {merged_path.name}")

    # 5. CSV template
    csv_rows  = make_csv_template(manifest)
    csv_path  = OUT_DIR / "scores_template.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"  Written: {csv_path.name}  ({len(csv_rows)-1} data rows)")

    print(f"\nAnnotation package ready -> {PKG_DIR}")
    print(f"Score templates -> {OUT_DIR}")


if __name__ == "__main__":
    main()
