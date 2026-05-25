#!/usr/bin/env python3
"""Generate combined Appendix PDF covering Human Evaluation, Multilingual, and Ablation studies."""

from fpdf import FPDF
import os, textwrap

# ── Configuration ──────────────────────────────────────────────────────────
FONT_DIR  = "C:\\Windows\\Fonts"
FONT_NAME = "Arial"  # Unicode-capable
OUTPUT    = "D:\\MTP\\Appendix_HumanEval_Multilingual_Ablation.pdf"

# ── Custom PDF class ───────────────────────────────────────────────────────
class AppendixPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("Arial", "", os.path.join(FONT_DIR, "arial.ttf"), uni=True)
        self.add_font("Arial", "B", os.path.join(FONT_DIR, "arialbd.ttf"), uni=True)
        self.add_font("Arial", "I", os.path.join(FONT_DIR, "ariali.ttf"), uni=True)
        self.add_font("Arial", "BI", os.path.join(FONT_DIR, "arialbi.ttf"), uni=True)
        self.set_auto_page_break(auto=True, margin=20)
        self.page_n = 0

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, "AdaCraft — Appendix: Human Evaluation, Multilingual & Ablation Studies", align="C")
        self.ln(1)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Arial", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no() - 1}", align="C")

    def chapter_title(self, title):
        self.set_x(self.l_margin)
        self.set_font("Arial", "B", 16)
        self.set_text_color(20, 60, 120)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section_title(self, title):
        self.set_x(self.l_margin)
        self.set_font("Arial", "B", 12)
        self.set_text_color(40, 80, 140)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def subsection_title(self, title):
        self.set_x(self.l_margin)
        self.set_font("Arial", "B", 10)
        self.set_text_color(60, 100, 160)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, txt):
        self.set_x(self.l_margin)
        self.set_font("Arial", "", 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.5, txt)
        self.ln(1)

    def italic_text(self, txt):
        self.set_x(self.l_margin)
        self.set_font("Arial", "I", 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 4.5, txt)
        self.ln(1)

    def bullet(self, txt, indent=15):
        self.set_x(self.l_margin)
        self.set_font("Arial", "", 9)
        self.set_text_color(30, 30, 30)
        x0 = self.l_margin + indent
        self.set_x(x0)
        bullet_w = self.get_string_width(chr(8226) + " ")
        self.cell(bullet_w, 4.5, chr(8226) + " ")
        self.multi_cell(self.w - self.r_margin - self.get_x(), 4.5, txt)

    def table_header(self, cols, widths):
        self.set_font("Arial", "B", 8)
        self.set_fill_color(20, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6, col, border=1, align="C", fill=True)
        self.ln()

    def table_row(self, cells, widths, fill=False):
        self.set_font("Arial", "", 8)
        self.set_text_color(30, 30, 30)
        if fill:
            self.set_fill_color(235, 240, 250)
        else:
            self.set_fill_color(255, 255, 255)
        for i, cell in enumerate(cells):
            self.cell(widths[i], 5.5, str(cell), border=1, align="C", fill=True)
        self.ln()

    def table_row_header(self, cells, widths):
        self.set_font("Arial", "B", 8)
        self.set_fill_color(200, 215, 240)
        self.set_text_color(20, 40, 80)
        for i, cell in enumerate(cells):
            self.cell(widths[i], 5.5, str(cell), border=1, align="C", fill=True)
        self.ln()
        self.set_text_color(30, 30, 30)

    def key_value(self, key, val, indent=0):
        self.set_font("Arial", "B", 9)
        self.set_text_color(30, 30, 30)
        x0 = self.l_margin + indent
        self.set_x(x0)
        kw = self.get_string_width(key) + 2
        remaining = self.w - self.r_margin - x0 - kw
        if remaining < 20:
            self.cell(0, 4.5, key + val, new_x="LMARGIN", new_y="NEXT")
        else:
            self.cell(kw, 4.5, key)
            self.set_font("Arial", "", 9)
            self.multi_cell(remaining, 4.5, val)

    def code_block(self, txt):
        self.set_font("Arial", "", 7.5)
        self.set_text_color(20, 20, 20)
        self.set_fill_color(240, 240, 245)
        self.set_draw_color(200, 200, 210)
        lines = txt.split("\n")
        block_h = len(lines) * 3.5 + 2
        if self.get_y() + block_h > 270:
            self.add_page()
        y_start = self.get_y()
        for i, line in enumerate(lines):
            x_start = self.get_x() + 2
            self.set_xy(x_start, y_start + i * 3.5)
            self.cell(0, 3.5, line, new_x="LMARGIN", new_y="NEXT")
        self.set_y(y_start + len(lines) * 3.5 + 2)
        self.ln(1)


# ══════════════════════════════════════════════════════════════════════════
# BUILD PDF
# ══════════════════════════════════════════════════════════════════════════
pdf = AppendixPDF()
pdf.set_margin(10)

# ── Title page ────────────────────────────────────────────────────────────
pdf.add_page()
pdf.ln(60)
pdf.set_font("Arial", "B", 26)
pdf.set_text_color(20, 60, 120)
pdf.cell(0, 14, "AdaCraft: Adaptive Educational Example Generation", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(6)
pdf.set_font("Arial", "B", 20)
pdf.set_text_color(40, 80, 140)
pdf.cell(0, 12, "Appendix", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.set_font("Arial", "", 14)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, "Human Evaluation A/B, Multilingual & Ablation Studies", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.set_font("Arial", "I", 10)
pdf.cell(0, 6, "Detailed Scenarios, Input/Output Examples, and Quantitative Results", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(30)
pdf.set_font("Arial", "", 9)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 5, "Generated: May 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 5, "Source code: https://github.com/anomalyco/AdaCraft", align="C", new_x="LMARGIN", new_y="NEXT")

# ══════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.chapter_title("Table of Contents")
pdf.ln(4)
toc = [
    ("Appendix A: Human Evaluation & Multilingual Studies", ""),
    ("  A.1  Study A — Learner Self-Evaluation", "rubric, design, 20 examples, 10 participants, 11-axis scoring"),
    ("  A.2  Study B — Contextual Full-Rubric Evaluation", "30 examples, 10 expert annotators, ICC, human-LLM correlation"),
    ("  A.3  Multilingual Evaluation", "6 languages, 3 scenarios, 3 providers, Wilcoxon tests"),
    ("", ""),
    ("Appendix B: Main Ablation Study", ""),
    ("  B.1  Experimental Design", "4-tier architecture, 8 users x 4 topics, metrics"),
    ("  B.2  Ablation Results", "composite scores, per-axis breakdown, cross-provider"),
    ("  B.3  Statistical Significance", "Friedman, Wilcoxon, Holm-Bonferroni, effect sizes"),
    ("  B.4  Convergence Metrics", "FCR, LUR, PPU"),
    ("  B.5  Detailed Scenarios", "T0 vs T3 walkthrough with input/output/rounds/judgments"),
    ("  B.6  Inter-Judge Agreement & Cross-Provider Summary", "kappa, summary comparison"),
]
for title, desc in toc:
    if title and not desc:
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(20, 60, 120)
        pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    elif desc:
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 5.5, f"  {title}  --  {desc}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.ln(2)

# ══════════════════════════════════════════════════════════════════════════
# APPENDIX A
# ══════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.chapter_title("Appendix A: Human Evaluation & Multilingual Studies")

# ── A.1 Study A ──────────────────────────────────────────────────────────
pdf.section_title("A.1  Study A: Learner Self-Evaluation")
pdf.body_text(
    "Study A is a within-participant, self-report evaluation where 10 learners from Kolkata, India "
    "(Bengali cultural background) rated their own personalized examples. Each participant received "
    "2 cold-start sessions (different topics), yielding 20 examples total. Participants scored the "
    "final (T3) example against 11 axes and compared baseline (T0) vs. final (T3) examples."
)

pdf.subsection_title("A.1.1  Evaluation Rubric (11 Axes)")
pdf.body_text("Learners scored each final example on 5 standard axes (shared with Study B), 3 feedback-improvement axes, "
              "2 self-report axes, and 1 bias axis:")
cols = ["Axis", "Name", "Scale", "What is measured"]
widths = [18, 42, 18, 92]
pdf.table_header(cols, widths)
rows = [
    ["PF", "Personalization Fidelity", "1-5", "Does the example feel tailored to me specifically?"],
    ["CC", "Complexity Calibration", "1-5", "Was the depth/vocabulary right for my level?"],
    ["CA", "Conceptual Accuracy", "1-5", "Is the factual content correct?"],
    ["PC", "Pedagogical Clarity", "1-5", "Is it structured for learning?"],
    ["DA", "Domain Appropriateness", "1-5", "Are analogies/framing correct for this domain?"],
    ["FC", "Feedback Compliance", "1-5", "Did the final example reflect changes I asked for?"],
    ["IS", "Improvement Score", "1-5", "How much did T0 -> T3 improve for me?"],
    ["IP", "Informed Preference", "T3/T0", "Which example better helps me understand?"],
    ["EU", "Educational Usefulness", "1-5", "Did the final example help me understand better?"],
    ["WU", "Would Use", "1-5", "Would I share this with a peer from my background?"],
    ["BF", "Bias & Fairness", "1-5", "Free of stereotyping / reductive assumptions?"],
]
for r in rows:
    pdf.table_row(r, widths)

pdf.subsection_title("A.1.2  Participants (10 Raters)")
pdf.body_text(
    "All participants are from Kolkata, India with Bengali cultural background. "
    "Each is both the learner (whose profile generated the example) AND the evaluator. "
    "Sessions are cold-start with no prior system interaction."
)
part_a = [
    "A1: Aritro Dutta (Engineering)     A2: Ankita Chowdhury (Social Sciences)",
    "A3: Amritangshu Manna (Medicine)    A4: Anindita Chatterjee (Education/B.Ed.)",
    "A5: Dr Subhobroto Dey (Educator/PhD)  A6: Aritra Das (Mathematics)",
    "A7: Shrestha Banerjee (Economics)   A8: Sreya Mondal (Nursing)",
    "A9: Sheila Chatterjee (BA)          A10: Sourav (Educator/PhD)",
]
for p in part_a:
    pdf.bullet(p, 12)

pdf.subsection_title("A.1.3  Detailed Scenario Walkthroughs")
pdf.body_text("Below are selected scenarios showing the full input/output/results pipeline for representative examples.")

# ── SCENARIO: EX01 (Aritro, Engineering, Natural Selection, DeepSeek) ──
pdf.add_page()
pdf.subsection_title("Scenario A.1.3a: EX01 -- Engineering Student, Natural Selection (DeepSeek)")
pdf.key_value("Participant: ", "Aritro Dutta (A1)  |  Role: Engineering Student  |  Location: Kolkata, India")
pdf.key_value("Topic: ", "Natural Selection  |  Provider: DeepSeek V3.2  |  Start Mode: Cold")
pdf.ln(2)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "BASELINE EXAMPLE (T0) -- Generic beetle analogy", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "Concept: Natural Selection\n"
    "\n"
    "Example:\n"
    "Consider a population of beetles living in a forest. Some beetles are brown,\n"
    "others are green. Birds (predators) hunt by sight. Green beetles blend into\n"
    "the leafy environment and are harder to spot, while brown beetles stand out\n"
    "against the green leaves and are eaten more frequently.\n"
    "\n"
    "Over several generations:\n"
    "1. Brown beetles are eaten more often and produce fewer offspring.\n"
    "2. Green beetles survive longer, reproduce more, and pass on the green-colour trait.\n"
    "3. Gradually, the beetle population shifts -- more and more beetles are green.\n"
    "\n"
    "Key Insight:\n"
    "Natural selection is not random. Traits that improve survival in a given\n"
    "environment become more common over time. The environment \"selects\" which\n"
    "traits persist -- not by intention, but by differential survival and reproduction."
)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "FEEDBACK ROUND 1 (Input):", new_x="LMARGIN", new_y="NEXT")
pdf.italic_text('"The example is okay but feels too abstract. Can you make it more relatable to '
                'engineering work, like algorithm design or system optimisation?"')
pdf.key_value("Agent Decision: ", "regenerate")

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "REGENERATED EXAMPLE (Round 1 output):", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "Concept: Natural Selection -- for an Engineering Student\n"
    "\n"
    "Example:\n"
    "Think of natural selection like an iterative optimisation algorithm -- similar\n"
    "to a genetic algorithm you might study in computational intelligence.\n"
    "\n"
    "Imagine you're designing a load-bearing truss. You start with a population of\n"
    "100 random designs. Each design is tested against the \"fitness function\":\n"
    "maximum load capacity at minimum material cost. The weakest designs (low\n"
    "fitness) are discarded. The strongest designs are selected, slightly mutated,\n"
    "and recombined to form the next generation.\n"
    "\n"
    "This maps directly to biology:\n"
    "| Algorithm         | Biology                         |\n"
    "| Random population | Genetic variation in a species |\n"
    "| Fitness function  | Environmental survival pressure  |\n"
    "| Selection         | Differential survival & reproduction |\n"
    "| Mutation+crossover| Genetic mutation and sex. reprod. |\n"
    "\n"
    "In Kolkata's engineering culture: Think of how IIT-JEE coaching institutes\n"
    "evolved. Only methods that produced results (high ranks) survived.\n"
    "\n"
    "Key Insight:\n"
    "Natural selection is nature's optimisation algorithm -- a massively\n"
    "parallelised search that has been running for billions of years."
)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "FEEDBACK ROUND 2 (Input):", new_x="LMARGIN", new_y="NEXT")
pdf.italic_text('"Yes this is much better -- the genetic algorithm parallel really clicked for me. '
                'Can you add a concrete local example?"')
pdf.key_value("Agent Decision: ", "regenerate")

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "REGENERATED EXAMPLE (Round 2 output -- includes Kolkata IIT-JEE analogy):", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "... (The Kolkata coaching institute example was woven in as additional context) ..."
)
pdf.key_value("Final Feedback: ",
              '"Perfect, the coaching institute example from Kolkata makes it very tangible."')
pdf.key_value("Agent Decision: ", "accept")

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "LLM JUDGE SCORES:", new_x="LMARGIN", new_y="NEXT")
cols = ["", "PF", "CC", "CA", "PC", "DA", "Composite"]
w2 = [30, 22, 22, 22, 22, 22, 30]
pdf.table_header(cols, w2)
pdf.table_row(["T0 (Baseline)", "2.31", "3.87", "4.94", "4.61", "3.72", "4.12"], w2)
pdf.table_row(["T3 (Final)", "4.10", "4.20", "5.00", "4.30", "4.00", "4.45"], w2, fill=True)
pdf.table_row(["Delta", "+1.79", "+0.33", "+0.06", "-0.31", "+0.28", "+0.33"], w2)
pdf.key_value("FCR (Mean): ", "4.29  |  Feedback Rounds: 3  |  PF improvement: +1.79 points")

# ── SCENARIO: EX05 (Amritangshu, Medical Student, DeepSeek) ──
pdf.subsection_title("Scenario A.1.3b: EX05 -- Medical Student, Natural Selection (DeepSeek)")
pdf.key_value("Participant: ", "Amritangshu Manna (A3)  |  Role: Medical Student  |  Location: Kolkata, India")
pdf.key_value("Topic: ", "Natural Selection  |  Provider: DeepSeek V3.2")
pdf.ln(1)
pdf.body_text(
    "The baseline T0 example was the same generic beetle analogy. The participant requested "
    "\"something clinically relevant -- like how bacteria evolve resistance.\" The system "
    "regenerated using antimicrobial resistance (AMR) as the primary example, explicitly "
    "connecting MRSA, antibiotic stewardship, and selection pressure in clinical settings."
)
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "FINAL EXAMPLE (T3) Key Content:", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "Concept: Natural Selection -- for a Medical Student\n"
    "\n"
    "The most clinically urgent example is antimicrobial resistance (AMR).\n"
    "\n"
    "Scenario: A patient with S. aureus infection. You prescribe methicillin.\n"
    "Most bacteria die. A tiny fraction carry a mutation in the mecA gene that\n"
    "alters penicillin-binding proteins -> methicillin cannot bind -> they survive.\n"
    "\n"
    "The drug acts as a SELECTION PRESSURE. Within days, the surviving resistant\n"
    "bacteria reproduce. The infection is now dominated by MRSA.\n"
    "\n"
    "1. Variation -- random mutations create diversity\n"
    "2. Selection -- antibiotic kills susceptible bacteria\n"
    "3. Inheritance -- resistance genes passed to daughter cells (and via HGT)\n"
    "4. Adaptation -- the population becomes resistant\n"
    "\n"
    "Key Insight: Every time you prescribe an antibiotic, you are applying a\n"
    "selection pressure. Natural selection is happening inside your patients right now."
)
cols = ["", "PF", "CC", "CA", "PC", "DA", "Composite"]
pdf.table_header(cols, w2)
pdf.table_row(["T0 (Baseline)", "2.31", "3.87", "4.94", "4.61", "3.72", "4.12"], w2)
pdf.table_row(["T3 (Final)", "4.60", "4.30", "5.00", "4.80", "4.70", "4.67"], w2, fill=True)
pdf.table_row(["Delta", "+2.29", "+0.43", "+0.06", "+0.19", "+0.98", "+0.55"], w2)
pdf.key_value("FCR (Mean): ", "4.33  |  Rounds: 2  |  PF improvement: +2.29 -- strongest PF gain in Study A")

# ── SCENARIO: EX08 (Anindita, Education, Plate Tectonics, GPT5) ──
pdf.subsection_title("Scenario A.1.3c: EX08 -- Education Student, Plate Tectonics (GPT-5-nano)")
pdf.key_value("Participant: ", "Anindita Chatterjee (A4)  |  Role: Education/B.Ed. Student")
pdf.key_value("Topic: ", "Plate Tectonics  |  Provider: GPT-5-nano")
pdf.ln(1)
pdf.body_text(
    "This is one of only 2 examples where T0 was preferred over T3. The education student "
    "asked for a connection to education, but the system struggled to generate a satisfying "
    "domain-relevant personalisation within a single cold-start session."
)
cols = ["", "PF", "CC", "CA", "PC", "DA", "Composite"]
pdf.table_header(cols, w2)
pdf.table_row(["T0 (Baseline)", "2.27", "3.76", "4.91", "4.48", "4.12", "4.14"], w2)
pdf.table_row(["T3 (Final)", "2.80", "3.50", "4.60", "3.60", "3.40", "3.73"], w2, fill=True)
pdf.table_row(["Delta", "+0.53", "-0.26", "-0.31", "-0.88", "-0.72", "-0.41"], w2)
pdf.key_value("FCR (Mean): ", "3.50 (lowest in study)  |  Rounds: 2  |  Note: T3 composite DECLINED from T0")
pdf.body_text(
    "This failure case is instructive: Plate Tectonics is a highly geological topic with limited "
    "natural connections to education/pedagogy. The regeneration attempted a geopolitical metaphor "
    "but the participant found it 'still mostly geological.' This reveals a boundary condition for "
    "the cold-start context manager: when the topic domain and user domain have minimal semantic "
    "overlap, the system may struggle to generate a satisfying bridge example."
)

# ── A.1.4  Results ──────────────────────────────────────────────────────
pdf.add_page()
pdf.subsection_title("A.1.4  Study A -- Quantitative Results Summary")

cols = ["Axis", "Mean", "SD", "Min", "Max", "Interpretation"]
w3 = [18, 18, 16, 16, 16, 86]
pdf.table_header(cols, w3)
rows_a = [
    ["PF", "4.05", "0.686", "2", "5", "Personalization felt clearly tailored"],
    ["CC", "3.85", "0.587", "3", "5", "Complexity calibration adequate"],
    ["CA", "4.45", "0.510", "4", "5", "High conceptual accuracy (self-reported)"],
    ["PC", "4.20", "0.616", "3", "5", "Pedagogical structure solid"],
    ["DA", "4.00", "0.725", "3", "5", "Domain framing appropriate"],
    ["FC", "3.95", "0.826", "2", "5", "Most feedback was addressed"],
    ["IS", "4.15", "1.040", "2", "5", "Significant improvement (p < 0.001)"],
    ["EU", "3.95", "0.605", "3", "5", "Meaningful educational utility"],
    ["WU", "3.90", "0.852", "2", "5", "75% would share with a peer"],
    ["BF", "4.80", "0.410", "4", "5", "100% scored 4 or 5 -- no bias detected"],
]
for r in rows_a:
    pdf.table_row(r, w3)

pdf.ln(2)
pdf.subsection_title("Informed Preference (IP) -- T3 vs T0")
pdf.body_text("T3 wins: 18/20 (90.0%)  |  T0 wins: 2/20 (EX08, EX17)  |  Binomial p = 2.01e-4 (significant)")
pdf.body_text(
    "Mean T3 vote share: 0.9. Both T0-preference examples involved Plate Tectonics for "
    "participants (education student, BA student) whose domain had minimal overlap with geology."
)

pdf.subsection_title("Statistical Tests")
pdf.bullet("IS t-test:  mean=4.15  t(19)=4.945  p=8.99e-5  (IS > null=3.0)", 12)
pdf.bullet("EU t-test:  mean=3.95  t(19)=7.025  p=1.09e-6  (EU > null=3.0)", 12)
pdf.bullet("WU t-test:  mean=3.90  t(19)=4.723  p=1.48e-4  (WU > null=3.0)", 12)
pdf.bullet("IP binomial:  18/20 T3 wins  p=2.01e-4  (null=0.5)", 12)

pdf.subsection_title("Role Breakdown (PF by Role)")
cols2 = ["Role", "n", "Mean PF", "Mean EU"]
w4 = [50, 15, 30, 30]
pdf.table_header(cols2, w4)
role_pf = [
    ["economics_student", 2, "4.5", "4.0"],
    ["education_student", 2, "3.0", "3.0"],
    ["educator", 4, "4.0", "4.25"],
    ["engineering_student", 2, "4.5", "4.0"],
    ["mathematics_student", 2, "4.5", "4.5"],
    ["medical_student", 2, "4.5", "4.5"],
    ["nursing_student", 2, "4.0", "4.0"],
    ["social_sciences_student", 2, "4.0", "4.0"],
    ["undergraduate_student", 2, "3.5", "3.0"],
]
for r in role_pf:
    pdf.table_row(r, w4)

pdf.ln(2)
pdf.subsection_title("Cross-Study PF Comparison")
cols_x = ["Study", "PF Mean", "Rater Type"]
w5 = [40, 40, 90]
pdf.table_header(cols_x, w5)
pdf.table_row(["Study A (self-report)", "4.05", "Learner self-report"], w5)
pdf.table_row(["Study B (expert-rated)", "3.637", "External domain experts (10 annotators)"], w5)
pdf.table_row(["Delta (A - B)", "+0.413", "Personalization more legible to recipients"], w5, fill=True)

# ── A.2  Study B ────────────────────────────────────────────────────────
pdf.add_page()
pdf.section_title("A.2  Study B: Contextual Full-Rubric Evaluation")
pdf.body_text(
    "Study B is a between-participant expert evaluation where 10 annotators evaluated "
    "30 examples (16 cold-start + 14 warm-start) across 4 professional roles. Each "
    "annotator scored each example on 7 axes (PF, CC, CA, PC, DA, FC, IS) using the "
    "same rubrics as Study A, plus an Informed Preference vote (T3 vs T0)."
)

pdf.subsection_title("A.2.1  Annotators (10 Domain Experts)")
ann_b = [
    "B1: Aritro Dutta (STEM)",
    "B2: Ankita Chowdhury (Social Sciences)",
    "B3: Amritangshu Manna (Life Sciences)",
    "B4: Anindita Chatterjee (Instructional Design)",
    "B5: Dr Subhobroto Dey (Generalist Educator)",
    "B6: Aritra Das (STEM)",
    "B7: Shrestha Banerjee (Social Sciences)",
    "B8: Sreya Mondal (Life Sciences)",
    "B9: Sheila Chatterjee (Instructional Design)",
    "B10: Sourav (Generalist Educator)",
]
for a in ann_b:
    pdf.bullet(a, 12)

pdf.subsection_title("A.2.2  Results Summary (Human Mean Scores, n=30)")

cols_b = ["Axis", "Mean", "SD", "Min", "Max"]
w6 = [22, 32, 32, 32, 32]
pdf.table_header(cols_b, w6)
rows_b = [
    ["PF", "3.637", "0.701", "1.6", "4.7"],
    ["CC", "3.867", "0.582", "2.4", "5.0"],
    ["CA", "4.313", "0.444", "3.4", "5.0"],
    ["PC", "3.940", "0.564", "2.6", "5.0"],
    ["DA", "4.197", "0.395", "3.6", "5.0"],
    ["FC", "3.707", "0.578", "2.4", "4.6"],
    ["IS", "4.107", "0.671", "1.8", "4.9"],
]
for r in rows_b:
    pdf.table_row(r, w6)

pdf.subsection_title("A.2.3  Informed Preference (T3 vs T0)")
pdf.body_text(
    "T3 wins: 26/30 examples (86.7%)  |  T0 wins: 4/30 (13.3%)  |  Mean T3 vote share: 85.3%"
)
pdf.body_text("Binomial test: p = 2.97e-5 (one-sided, null=0.5). Highly significant.")
pdf.body_text("T0-majority examples: EX09, EX11, EX20, EX28.")
pdf.ln(1)

pdf.subsection_title("A.2.4  Inter-Rater Reliability -- ICC(2,1)")
cols_icc = ["Axis", "ICC", "95% CI", "F", "Interpretation"]
w7 = [20, 22, 40, 22, 46]
pdf.table_header(cols_icc, w7)
icc_rows = [
    ["PF", "0.692", "[0.612, 0.832]", "27.36", "Moderate"],
    ["CC", "0.596", "[0.479, 0.748]", "16.67", "Moderate"],
    ["CA", "0.473", "[0.340, 0.637]", "10.04", "Fair"],
    ["PC", "0.540", "[0.484, 0.752]", "16.96", "Moderate"],
    ["DA", "0.465", "[0.359, 0.654]", "10.78", "Fair"],
    ["FC", "0.566", "[0.516, 0.773]", "19.01", "Moderate"],
    ["IS", "0.684", "[0.617, 0.835]", "27.93", "Moderate"],
]
for r in icc_rows:
    pdf.table_row(r, w7)
pdf.italic_text("All ICCs significant at p < 0.001. CA and DA are 'Fair' (< 0.5), reflecting legitimate domain-level variation.")

pdf.subsection_title("A.2.5  Human--LLM Judge Correlation (Pearson r)")
cols_hl = ["Axis", "r", "p", "n"]
w8 = [30, 30, 55, 35]
pdf.table_header(cols_hl, w8)
hl_rows = [
    ["PF", "0.820", "2.89e-8 ***", "30"],
    ["CC", "0.728", "5.25e-6 ***", "30"],
    ["CA", "N/A (zero var.)", "--", "30"],
    ["PC", "0.696", "1.93e-5 ***", "30"],
    ["DA", "0.025", "0.896 (n.s.)", "30"],
    ["Composite", "0.629", "0.0002 ***", "30"],
    ["FC vs FCR", "0.748", "2.03e-6 ***", "30"],
]
for r in hl_rows:
    pdf.table_row(r, w8)
pdf.body_text(
    "Strong human-LLM alignment on PF (r=0.820), CC (r=0.728), and PC (r=0.696). "
    "DA shows no correlation (r=0.025, n.s.) -- likely because LLM judge scores cluster "
    "near ceiling with minimal variance while expert human raters show broader spread. "
    "FC vs FCR correlation (r=0.748) validates the LLM-based feedback compliance metric."
)

pdf.subsection_title("A.2.6  Cold-Start vs Warm-Start Comparison")
cols_cw = ["Condition", "n", "Mean PF", "Mean IS"]
w9 = [40, 20, 40, 40]
pdf.table_header(cols_cw, w9)
pdf.table_row(["Cold", "16", "3.531", "3.894"], w9)
pdf.table_row(["Warm", "14", "3.757", "4.350"], w9, fill=True)
pdf.table_row(["Delta (Warm - Cold)", "--", "+0.226", "+0.456"], w9)

pdf.subsection_title("Profile Breakdown -- Mean PF by Role")
cols_pr = ["Role", "n", "Mean PF", "SD"]
w10 = [50, 20, 40, 40]
pdf.table_header(cols_pr, w10)
pdf.table_row(["Engineer", 7, "4.057", "0.597"], w10)
pdf.table_row(["Student", 8, "3.688", "0.601"], w10)
pdf.table_row(["Humanities Researcher", 7, "3.457", "1.061"], w10)
pdf.table_row(["Nurse", 8, "3.375", "0.337"], w10, fill=True)

# ── A.3 Multilingual Evaluation ──────────────────────────────────────────
pdf.add_page()
pdf.section_title("A.3  Multilingual Evaluation")
pdf.body_text(
    "The multilingual evaluation tests AdaCraft's ability to generate and adapt personalized "
    "educational examples across 6 languages (Hindi, Tamil, Bengali, German, Arabic, Mandarin) "
    "under 3 scenarios: FNL (Full Native Language), NFEO (Native Feedback, English Output), "
    "and EN_BASELINE (all English). Three providers tested: GPT-5-nano, DeepSeek V3.2, Sarvam (Indic only)."
)

pdf.subsection_title("A.3.1  Experimental Design")
cols_ml = ["Scenario", "Topic Lang.", "Feedback Lang.", "Output Lang.", "Purpose"]
w11 = [25, 25, 28, 28, 64]
pdf.table_header(cols_ml, w11)
pdf.table_row(["FNL", "Native (X)", "Native (X)", "Native (X)", "End-to-end multilingual pipeline"], w11)
pdf.table_row(["NFEO", "English", "Native (X)", "English", "Cross-lingual feedback processing"], w11)
pdf.table_row(["EN_BASELINE", "English", "English", "English", "Comparison baseline"], w11, fill=True)

pdf.ln(2)
pdf.subsection_title("Languages and Profiles")
cols_lp = ["User ID", "Name", "Language", "Code", "Role", "Location"]
w12 = [22, 16, 26, 14, 50, 52]
pdf.table_header(cols_lp, w12)
profiles_ml = [
    ["ml_user_01", "Priya", "Hindi", "hi", "Student", "Mumbai, India"],
    ["ml_user_02", "Meena", "Tamil", "ta", "Nurse", "Chennai, India"],
    ["ml_user_03", "Arjun", "Bengali", "bn", "Software Engineer", "Kolkata, India"],
    ["ml_user_04", "Klaus", "German", "de", "Humanities Researcher", "Munich, Germany"],
    ["ml_user_05", "Fatima", "Arabic", "ar", "Nurse", "Cairo, Egypt"],
    ["ml_user_06", "Wei", "Mandarin", "zh", "Software Engineer", "Shanghai, China"],
]
for r in profiles_ml:
    pdf.table_row(r, w12)

pdf.ln(2)
pdf.subsection_title("Test Matrix")
cols_tm = ["Scenario", "Profiles", "Topics", "Cells (GPT/DeepSeek)", "Cells (Sarvam)"]
w13 = [28, 22, 22, 48, 50]
pdf.table_header(cols_tm, w13)
pdf.table_row(["FNL", "6", "4", "24", "12 (Indic only)"], w13)
pdf.table_row(["NFEO", "6", "4", "24", "12 (Indic only)"], w13)
pdf.table_row(["EN_BASELINE", "6", "4", "24", "12 (Indic only)"], w13, fill=True)
pdf.table_row(["Total", "--", "--", "72", "36"], w13)

pdf.subsection_title("A.3.2  GPT-5-nano Results")
cols_gpt = ["Scenario", "Group", "n", "Composite", "LangMatch", "FCR@3", "FCR@4", "LUR", "DA"]
w14 = [22, 18, 12, 24, 22, 18, 18, 16, 16]
pdf.table_header(cols_gpt, w14)
pdf.table_row(["FNL", "Indic", "12", "4.800", "1.000", "0.917", "0.708", "1.000", "0.667"], w14)
pdf.table_row(["FNL", "Foreign", "12", "4.775", "0.500", "0.792", "0.708", "1.000", "0.667"], w14)
pdf.table_row(["FNL", "Overall", "24", "4.788", "0.800", "0.854", "0.708", "1.000", "0.667"], w14, fill=True)
pdf.table_row(["NFEO", "Indic", "12", "4.800", "0.917", "0.833", "0.792", "1.000", "0.667"], w14)
pdf.table_row(["NFEO", "Foreign", "12", "4.833", "0.833", "0.958", "0.792", "0.917", "0.639"], w14)
pdf.table_row(["NFEO", "Overall", "24", "4.817", "0.875", "0.896", "0.792", "0.958", "0.653"], w14, fill=True)
pdf.table_row(["EN_BASE", "Overall", "24", "4.758", "--", "--", "--", "--", "--"], w14)

pdf.body_text(
    "Mandarin LangMatch = 0.000 across all 4 FNL cells (both providers). "
    "This is a cross-provider systematic issue: the model generates English output despite "
    "Chinese topic/feedback, likely because the prompt lacks an explicit language enforcement directive."
)

pdf.subsection_title("A.3.3  DeepSeek V3.2 Results")
pdf.table_header(cols_gpt, w14)
pdf.table_row(["FNL", "Indic", "12", "4.775", "1.000", "1.000", "0.909", "0.917", "0.944"], w14)
pdf.table_row(["FNL", "Foreign", "12", "4.808", "0.500", "0.864", "0.682", "1.000", "0.819"], w14)
pdf.table_row(["FNL", "Overall", "24", "4.792", "0.800", "0.932", "0.795", "0.958", "0.882"], w14, fill=True)
pdf.table_row(["NFEO", "Indic", "12", "4.817", "0.917", "0.917", "0.500", "1.000", "0.778"], w14)
pdf.table_row(["NFEO", "Foreign", "12", "4.817", "1.000", "0.917", "0.750", "1.000", "0.833"], w14)
pdf.table_row(["NFEO", "Overall", "24", "4.817", "0.958", "0.917", "0.625", "1.000", "0.806"], w14, fill=True)
pdf.table_row(["EN_BASE", "Overall", "24", "4.817", "--", "--", "--", "--", "--"], w14)

pdf.subsection_title("A.3.4  Sarvam Results (Indic-only)")
pdf.table_header(cols_gpt, w14)
pdf.table_row(["FNL", "Indic", "12", "4.642", "1.000", "0.792", "0.542", "0.917", "0.667"], w14)
pdf.table_row(["NFEO", "Indic", "12", "4.767", "0.917", "0.667", "0.458", "1.000", "0.667"], w14)
pdf.table_row(["EN_BASE", "Indic", "12", "4.725", "--", "--", "--", "--", "--"], w14, fill=True)

pdf.subsection_title("A.3.5  Wilcoxon Test Results (All 10 tests -- None Significant)")
cols_wil = ["Provider", "Scenario", "Group", "n", "Delta", "p-val", "d", "Sig (a'=0.025)"]
w15 = [28, 22, 18, 12, 18, 18, 16, 28]
pdf.table_header(cols_wil, w15)
wilcoxon_data = [
    ["GPT-5-nano", "FNL", "Indic", 12, "-0.017", "0.655", "-0.130", "No"],
    ["GPT-5-nano", "FNL", "Foreign", 12, "+0.075", "0.547", "+0.158", "No"],
    ["GPT-5-nano", "NFEO", "Indic", 12, "-0.017", "0.655", "-0.130", "No"],
    ["GPT-5-nano", "NFEO", "Foreign", 12, "+0.133", "0.317", "+0.331", "No"],
    ["DeepSeek", "FNL", "Indic", 12, "-0.058", "0.317", "-0.316", "No"],
    ["DeepSeek", "FNL", "Foreign", 12, "+0.008", "0.705", "+0.080", "No"],
    ["DeepSeek", "NFEO", "Indic", 12, "-0.017", "0.739", "-0.097", "No"],
    ["DeepSeek", "NFEO", "Foreign", 12, "+0.017", "0.564", "+0.169", "No"],
    ["Sarvam", "FNL", "Indic", 12, "-0.083", "0.389", "-0.351", "No"],
    ["Sarvam", "NFEO", "Indic", 12, "+0.042", "0.458", "+0.195", "No"],
]
for r in wilcoxon_data:
    pdf.table_row(r, w15)
pdf.body_text(
    "Interpretation: No provider shows a statistically significant quality change under either "
    "multilingual scenario vs the English baseline (all p >> 0.025 Bonferroni threshold). "
    "Effect sizes are all small (|d| < 0.36). The null finding is consistent across both "
    "providers and both language groups -- multilingual interaction does not degrade (or inflate) "
    "composite example quality."
)

pdf.subsection_title("A.3.6  Key Findings")
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "Finding 1: No Quality Degradation from Multilingual Interaction", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 9)
pdf.body_text(
    "All 10 Wilcoxon tests non-significant (p > 0.30). Composite scores under FNL and NFEO "
    "statistically indistinguishable from English baseline. The AdaCraft pipeline generalizes "
    "to multilingual input/output without measurable quality cost."
)
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "Finding 2: Mandarin LangMatch Failure is Cross-Provider", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 9)
pdf.body_text(
    "FNL LangMatch for Mandarin (zh) = 0.000 across both GPT-5-nano and DeepSeek (8/8 cells). "
    "Arabic, Hindi, Tamil, Bengali achieve perfect LangMatch. German excluded (Latin-script ambiguity)."
)
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "Finding 3: DeepSeek Superior Decision Accuracy", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 9)
pdf.body_text(
    "DeepSeek DA (0.944 FNL Indic) substantially exceeds GPT-5-nano (0.667) and Sarvam (0.667). "
    "The 0.667 floor represents correct R2/R3 (accept, flag_pattern) but failure on R1 (regenerate)."
)
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "Finding 4: Sarvam Lower Composite and FCR vs. General-Purpose LLMs", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 9)
pdf.body_text(
    "Sarvam FNL composite (4.642) is 0.150-0.158 below GPT-5-nano and DeepSeek. Tamil weakest "
    "per-language cell (4.375) with FCR@3=0.500. However LangMatch=1.000 across all Indic cells."
)


# ══════════════════════════════════════════════════════════════════════════
# APPENDIX B
# ══════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.chapter_title("Appendix B: Main Ablation Study")
pdf.body_text(
    "The main ablation study evaluates the AdaCraft pipeline using a 4-tier ablation design "
    "(T0/T1/T2/T3) across 8 synthetic users (4 profiles x 2 start modes: cold/warm), 4 topics, "
    "and 2 LLM providers (GPT-5-nano, DeepSeek V3.2). Total: 128 cells per provider."
)

# ── B.1 Design ──────────────────────────────────────────────────────────
pdf.section_title("B.1  Experimental Design")

pdf.subsection_title("B.1.1  4-Tier Architecture")
cols_tiers = ["Tier", "Profile", "Context Mgr", "Feedback", "Description"]
w16 = [14, 26, 30, 26, 74]
pdf.table_header(cols_tiers, w16)
pdf.table_row(["T0", "Skipped", "Skipped", "Skipped", "Generic LLM -- no personalization"], w16)
pdf.table_row(["T1", "Injected", "Skipped", "Skipped", "Static profile only"], w16)
pdf.table_row(["T2", "Injected", "Active", "Skipped", "Profile + learning history context"], w16)
pdf.table_row(["T3", "Injected", "Active", "Active", "Full AdaCraft system"], w16, fill=True)

pdf.subsection_title("B.1.2  Synthetic Users (4 Profiles x 2 Start Modes)")
cols_users = ["User ID", "Name", "Role", "Location", "Start", "R1 Feedback"]
w17 = [24, 16, 46, 34, 16, 34]
pdf.table_header(cols_users, w17)
users_data = [
    ["eval_user_01", "Lena", "Student", "Berlin, Germany", "cold", 'F1: "too complicated"'],
    ["eval_user_02", "Amara", "Nurse", "Lagos, Nigeria", "cold", 'F2: "not my field"'],
    ["eval_user_03", "Carlos", "Humanities Researcher", "Sao Paulo, Brazil", "cold", 'F1: "too complicated"'],
    ["eval_user_04", "Kenji", "Software Engineer", "Tokyo, Japan", "cold", 'F2: "not my field"'],
    ["eval_user_05", "Lena", "Student", "Berlin, Germany", "warm", 'A1: "I dont get it"'],
    ["eval_user_06", "Amara", "Nurse", "Lagos, Nigeria", "warm", 'A2: contradictory'],
    ["eval_user_07", "Carlos", "Humanities Researcher", "Sao Paulo, Brazil", "warm", 'A5: hidden critique'],
    ["eval_user_08", "Kenji", "Software Engineer", "Tokyo, Japan", "warm", 'A4: "Hmm."'],
]
for r in users_data:
    pdf.table_row(r, w17)
pdf.body_text("4 Topics: Natural Selection (evolutionary_biology), Cognitive Bias (psychology), "
              "Compound Interest (mathematics_finance), Plate Tectonics (earth_sciences). "
              "All 4 topics crossed with all 8 users = 32 cells per tier.")

pdf.subsection_title("B.1.3  Scripted Feedback Battery (T3 only)")
cols_fb = ["Round", "Key", "Feedback Content", "Expected Decision"]
w18 = [16, 14, 100, 40]
pdf.table_header(cols_fb, w18)
fb_data = [
    ["R1 (cold)", "F1/F2", 'Unambiguous complaints: "too complicated" or "not my field"', "regenerate"],
    ["R1 (warm)", "A1/A2/A4/A5", 'Adversarial: vague, contradictory, minimal, hidden critique', "regenerate / accept"],
    ["R2 (all)", "F3", '"This is great! The example really helped me understand." (positive close)', "accept"],
    ["R3 (all)", "FP", "Stable-trait preference per role (student/nurse/researcher/engineer)", "flag_pattern"],
]
for r in fb_data:
    pdf.table_row(r, w18)
pdf.body_text(
    "The adversarial battery tests the Adaptive Response Agent's robustness to realistic, "
    "ambiguous user input. A1 = vague, A2 = contradictory (\"make it simpler but go deeper\"), "
    "A4 = minimal (\"Hmm.\"), A5 = hidden critique with surface praise."
)

pdf.subsection_title("B.1.4  Metrics")
pdf.bullet("Composite Score = 0.20*PF + 0.20*CC + 0.30*CA + 0.20*PC + 0.10*DA (1-5 scale)", 12)
pdf.bullet("FCR@3 / FCR@4: Fraction of regenerations with compliance score >= 3 / >= 4", 12)
pdf.bullet("LUR: Fraction of T3 sessions with at least 1 regeneration", 12)
pdf.bullet("PPU: PF delta between warm-start T3 and warm-start T1", 12)
pdf.bullet("Decision Accuracy: Fraction of agent actions matching ground-truth expected decisions", 12)

# ── B.2  Ablation Results ──────────────────────────────────────────────
pdf.add_page()
pdf.section_title("B.2  Ablation Results")

pdf.subsection_title("B.2.1  Composite Scores by Tier")
cols_comp = ["Tier", "DeepSeek V3.2", "GPT-5-nano", "Description"]
w19 = [16, 38, 38, 78]
pdf.table_header(cols_comp, w19)
pdf.table_row(["T0", "4.257 +/- 0.057", "3.712 +/- 0.280", "Generic -- no profile, no context"], w19)
pdf.table_row(["T1", "4.809 +/- 0.037", "4.388 +/- 0.261", "+ User profile only"], w19)
pdf.table_row(["T2", "4.859 +/- 0.025", "4.791 +/- 0.147", "+ Context instruction from learning history"], w19)
pdf.table_row(["T3", "4.888 +/- 0.015", "4.981 +/- 0.058", "+ Feedback loop (full system)"], w19, fill=True)
pdf.table_row(["T0->T1 Delta", "+0.552", "+0.676", ""], w19)
pdf.table_row(["T0->T3 Delta", "+0.631", "+1.269", ""], w19, fill=True)

pdf.body_text(
    "DeepSeek starts from a higher baseline (T0=4.257 vs 3.712) suggesting stronger zero-shot "
    "personalization. GPT-5-nano shows a larger T0->T3 gain (+1.269 vs +0.631). Both reach "
    "comparable T3 ceilings (~4.89 vs ~4.98)."
)

pdf.subsection_title("B.2.2  Per-Axis Breakdown")

pdf.set_font("Arial", "B", 8)
pdf.cell(0, 5, "DeepSeek V3.2", new_x="LMARGIN", new_y="NEXT")
cols_ax = ["Axis", "T0", "T1", "T2", "T3"]
w20 = [42, 32, 32, 32, 32]
pdf.table_header(cols_ax, w20)
ds_axis = [
    ["PF (Personalization Fidelity)", "2.73", "4.80", "4.93", "4.99"],
    ["CC (Complexity Calibration)", "4.13", "4.35", "4.43", "4.47"],
    ["CA (Conceptual Accuracy)", "4.94", "4.99", "5.00", "5.00"],
    ["PC (Pedagogical Clarity)", "4.82", "4.93", "4.95", "4.99"],
    ["DA (Domain Appropriateness)", "4.39", "4.95", "4.99", "5.00"],
]
for r in ds_axis:
    pdf.table_row(r, w20)

pdf.ln(2)
pdf.set_font("Arial", "B", 8)
pdf.cell(0, 5, "GPT-5-nano", new_x="LMARGIN", new_y="NEXT")
pdf.table_header(cols_ax, w20)
gp_axis = [
    ["PF (Personalization Fidelity)", "2.09", "3.47", "4.34", "4.94"],
    ["CC (Complexity Calibration)", "3.78", "4.38", "4.84", "5.00"],
    ["CA (Conceptual Accuracy)", "4.41", "4.78", "4.97", "5.00"],
    ["PC (Pedagogical Clarity)", "4.00", "4.53", "4.88", "4.97"],
    ["DA (Domain Appropriateness)", "4.16", "4.78", "4.88", "5.00"],
]
for r in gp_axis:
    pdf.table_row(r, w20)

pdf.body_text(
    "PF shows the largest tier-to-tier jump for both providers. For GPT-5-nano, PF rises from "
    "2.09 (T0, essentially generic) to 4.94 (T3, near-perfect personalization) -- a +2.85 point gain. "
    "This validates the core hypothesis: the combination of profile injection, context management, "
    "and adaptive feedback produces dramatically more personalized examples."
)

# ── B.3  Statistical Significance ────────────────────────────────────────
pdf.add_page()
pdf.section_title("B.3  Statistical Significance")

pdf.subsection_title("B.3.1  Friedman Test (Omnibus, all 4 tiers)")
cols_fr = ["Provider", "Chi-squared", "p-value", "Significant"]
w21 = [50, 50, 50, 20]
pdf.table_header(cols_fr, w21)
pdf.table_row(["DeepSeek V3.2", "96.000", "1.13e-20", "***"], w21)
pdf.table_row(["GPT-5-nano", "91.351", "1.12e-19", "***"], w21)

pdf.subsection_title("B.3.2  Pairwise Wilcoxon Signed-Rank (Holm-Bonferroni corrected, 6 pairs)")
cols_wil2 = ["Pair", "DeepSeek Diff", "DS r_rb", "DS p(Holm)", "GPT-5 Diff", "GPT r_rb", "GPT p(Holm)"]
w22 = [22, 28, 20, 30, 28, 20, 30]
pdf.table_header(cols_wil2, w22)
wilcox_data = [
    ["T0 vs T1", "+0.552", "1.000", "2.79e-09 ***", "+0.675", "1.000", "2.79e-09 ***"],
    ["T0 vs T2", "+0.602", "1.000", "2.79e-09 ***", "+1.078", "1.000", "2.79e-09 ***"],
    ["T0 vs T3", "+0.631", "1.000", "2.79e-09 ***", "+1.269", "1.000", "2.79e-09 ***"],
    ["T1 vs T2", "+0.049", "1.000", "2.79e-09 ***", "+0.403", "1.000", "6.95e-06 ***"],
    ["T1 vs T3", "+0.078", "1.000", "2.79e-09 ***", "+0.594", "1.000", "6.95e-06 ***"],
    ["T2 vs T3", "+0.029", "1.000", "2.79e-09 ***", "+0.191", "1.000", "1.22e-05 ***"],
]
for r in wilcox_data:
    pdf.table_row(r, w22)

pdf.body_text(
    "All 6 pairwise comparisons are significant for both providers. The rank-biserial r = 1.000 "
    "for all pairs means ALL 32 user-topic pairs improved monotonically -- zero exceptions. "
    "This is an extremely large and consistent effect."
)

pdf.subsection_title("B.3.3  Interpretation")
pdf.body_text(
    "The tier improvements are not just statistically significant but practically meaningful. "
    "The monotonic improvement across all 32 cells (r_rb = 1.0) confirms that adding each "
    "successive capability layer (profile, context, feedback) reliably improves example quality. "
    "The largest jump is T0->T1 (profile injection), particularly for PF. "
    "The T2->T3 jump (feedback loop) is smaller but still significant, suggesting that "
    "the largest gains come from personalization infrastructure rather than the feedback mechanism itself."
)

# ── B.4  Convergence Metrics ────────────────────────────────────────────
pdf.add_page()
pdf.section_title("B.4  Convergence Metrics")

pdf.subsection_title("B.4.1  Feedback Compliance Rate (FCR)")
cols_fcr = ["Battery", "DeepSeek FCR@3", "DS FCR@4", "DS Mean", "GPT-5 FCR@3", "GPT FCR@4", "GPT Mean"]
w23 = [28, 28, 22, 22, 28, 22, 22]
pdf.table_header(cols_fcr, w23)
fcr_data = [
    ["Easy", "1.000", "1.000", "4.536", "0.925", "0.850", "4.475"],
    ["Adversarial", "1.000", "0.692", "3.923", "1.000", "1.000", "4.800"],
    ["Overall", "1.000", "0.902", "4.341", "0.945", "0.891", "4.564"],
]
for r in fcr_data:
    pdf.table_row(r, w23)
pdf.body_text(
    "DeepSeek achieves perfect FCR@3 (1.000) overall; GPT-5-nano is close (0.945). "
    "Both providers show strong feedback compliance. DeepSeek's FCR@4 on adversarial battery "
    "(0.692) is notably lower than GPT-5-nano's perfect score (1.000), suggesting GPT-5-nano "
    "handles vague/contradictory feedback more reliably at higher compliance thresholds."
)

pdf.subsection_title("B.4.2  Loop Utilization Rate (LUR)")
cols_lur = ["Battery", "DeepSeek LUR", "DS Triggered", "GPT-5 LUR", "GPT Triggered"]
w24 = [34, 36, 42, 36, 42]
pdf.table_header(cols_lur, w24)
lur_data = [
    ["Easy (cold)", "1.000", "16/16", "1.000", "16/16"],
    ["Adversarial (warm)", "0.875", "14/16", "0.938", "15/16"],
    ["Overall", "0.938", "30/32", "0.969", "31/32"],
]
for r in lur_data:
    pdf.table_row(r, w24)
pdf.body_text(
    "Both providers trigger regeneration at very high rates (>= 93.8%). Cold-start users always "
    "trigger regeneration (100%), while 2-3 warm-start adversarial cases are accepted without "
    "regeneration -- the agent judges the feedback does not require a change."
)

pdf.subsection_title("B.4.3  Pattern Persistence Utilization (PPU)")
cols_ppu = ["Group", "DeepSeek Mean PF", "GPT-5-nano Mean PF"]
w25 = [52, 52, 52]
pdf.table_header(cols_ppu, w25)
ppu_data = [
    ["Warm T3 (full system)", "5.000", "5.000"],
    ["Warm T1 (no patterns, no feedback)", "4.688", "3.062"],
    ["Cold T3 (no prior history)", "4.979", "4.875"],
    ["Delta PF (Warm T3 - Warm T1)", "+0.312", "+1.938"],
]
for r in ppu_data:
    pdf.table_row(r, w25)
pdf.body_text(
    "PPU measures whether stored learning patterns improve personalization at generation time. "
    "GPT-5-nano shows a dramatic PPU delta (+1.938) because its warm-start T1 PF is notably "
    "low (3.062). When patterns are available at generation time (warm T3), PF jumps to 5.000 -- "
    "the system uses stored domain_preference patterns to insert appropriate domain context. "
    "DeepSeek's smaller delta (+0.312) reflects its already-strong warm T1 PF (4.688), "
    "leaving less room for improvement."
)

# ── B.5  Detailed Scenarios ─────────────────────────────────────────────
pdf.add_page()
pdf.section_title("B.5  Detailed Scenario Walkthroughs")

pdf.subsection_title("B.5.1  T0 Scenario -- Lena, Natural Selection (GPT-5-nano)")
pdf.body_text(
    "Tier T0 bypasses all personalization layers. The example uses a generic beetle analogy "
    "with no reference to Lena's profile (Berlin student). Feedback is skipped (eval_mode gate)."
)
pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "T0 GENERATED EXAMPLE (Initial + Final are identical -- no feedback processing):", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "Concept: Natural Selection\n"
    "\n"
    "Example:\n"
    "Think of a population of beetles living on a tree trunk. The beetles vary in\n"
    "color: some are light, some are dark. In this environment, birds tend to spot\n"
    "the light-colored beetles against the dark bark, so light beetles are more\n"
    "likely to be eaten. If the bark is dark, dark beetles blend in better and are\n"
    "more likely to survive and have babies.\n"
    "\n"
    "Starting numbers this season:\n"
    "- 40 light beetles\n"
    "- 60 dark beetles\n"
    "\n"
    "Predation and survival:\n"
    "- Light beetles survive at 20% -> 8 survive\n"
    "- Dark beetles survive at 60% -> 36 survive\n"
    "\n"
    "Result: Next generation: ~8 light offspring, ~36 dark offspring.\n"
    "Dark-colored beetles become more common over time."
)

cols_t0 = ["Axis", "PF", "CC", "CA", "PC", "DA", "Composite"]
w26 = [26, 22, 22, 22, 22, 22, 34]
pdf.table_header(cols_t0, w26)
pdf.table_row(["T0 Score", "2", "4", "4", "3", "3", "3.3"], w26)

pdf.body_text(
    "PF=2: 'Completely generic -- could have been written for anyone.' No location, no role "
    "adaptation. The beetle analogy is a standard textbook example. CA=4 is adequate (factually correct)."
)

pdf.subsection_title("B.5.2  T3 Scenario -- Lena, Natural Selection (GPT-5-nano)")
pdf.body_text(
    "Tier T3 runs the full pipeline: profile injection -> context manager -> generation -> "
    "3 feedback rounds (R1: simplify, R2: accept, R3: school-life scenario)."
)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "ROUND 0 (Initial Generation -- already personalized):", new_x="LMARGIN", new_y="NEXT")
pdf.code_block(
    "Concept: Natural Selection\n"
    "\n"
    "In a temperate European forest near Berlin, a population of moths shows color\n"
    "variation: light and dark forms. The trait is heritable, and color affects how\n"
    "easily predators spot moths on tree trunks.\n"
    "\n"
    "Setup: 100 moths (70 light, 30 dark)\n"
    "Environment: Tree bark becomes darker\n"
    "Survival rates: light 0.20, dark 0.60\n"
    "Surviving: light 14, dark 18 -> each leaves 2 offspring\n"
    "Next gen: 28 light, 36 dark -> dark = 56.3%\n"
    "\n"
    "Insight: The dark form becomes more common because it has higher fitness."
)
cols_t3r0 = ["Axis", "PF", "CC", "CA", "PC", "DA", "Composite"]
pdf.table_header(cols_t3r0, w26)
pdf.table_row(["Round 0 Score", "5", "5", "5", "5", "5", "5.0"], w26)
pdf.body_text(
    "PF=5: Already references Berlin, European forest. Complexity appropriate for high school student. "
    "The initial T3 example scores perfectly on all axes -- the profile injection alone achieves "
    "strong personalization for this user-topic pair."
)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "ROUND 1 -- Feedback + Regeneration:", new_x="LMARGIN", new_y="NEXT")
pdf.italic_text('User: "This is too complicated for me. Can you simplify it with a more basic example?"')
pdf.key_value("Agent Action: ", "regenerate")
pdf.code_block(
    "Regenerated: Setup: 20 moths (12 light, 8 dark). Dark background favors dark.\n"
    "Light survivors=1, Dark survivors=3. Each produces 1 offspring.\n"
    "Next gen: 2 light, 3 dark (dark = 60%)."
)
pdf.body_text(
    "FCR compliance score: 4/5 -- simplified correctly but still slightly numerical for a beginner request."
)

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "ROUND 2 -- Positive Close:", new_x="LMARGIN", new_y="NEXT")
pdf.italic_text('User: "This is great! The example really helped me understand the concept."')
pdf.key_value("Agent Action: ", "accept")

pdf.set_font("Arial", "B", 9)
pdf.cell(0, 5, "ROUND 3 -- Stable Trait + Regeneration:", new_x="LMARGIN", new_y="NEXT")
pdf.italic_text('User: "I always connect better when examples use everyday scenarios from school life, like assignments or exams."')
pdf.key_value("Agent Action: ", "regenerate")
pdf.code_block(
    "Final Example (Round 3):\n"
    "In Lena's biology class in Berlin, 20 students = mini-population.\n"
    "Alleles: A (preparedness), a (lower). AA=9, Aa=6, aa=5.\n"
    "Hard exam -> selection pressure. w_AA=1.0, w_Aa=0.9, w_aa=0.4.\n"
    "After selection: p(A) changes 0.60 -> 0.714.\n"
    "Key Insight: Selection pressure shifts allele frequencies toward advantageous traits."
)

cols_t3fn = ["Axis", "PF", "CC", "CA", "PC", "DA", "Composite"]
pdf.table_header(cols_t3fn, w26)
pdf.table_row(["Final Score", "4", "5", "5", "4", "4", "4.5"], w26)
pdf.body_text(
    "Final PF=4 (vs initial 5): the classroom scenario is less location-specific than the "
    "Berlin forest reference. But the example now explicitly integrates the user's stated "
    "preference for school-life scenarios -- demonstrating the adaptive response loop."
)

pdf.ln(2)
pdf.subsection_title("B.5.3  Decision Accuracy")
cols_da = ["Provider", "Battery", "Correct", "Total", "Accuracy"]
w27 = [38, 34, 24, 20, 24]
pdf.table_header(cols_da, w27)
pdf.table_row(["DeepSeek V3.2", "Overall T3", "--", "--", "0.926"], w27)
pdf.table_row(["GPT-5-nano", "Overall T3", "2.0 avg", "3 rounds", "0.667"], w27)
pdf.body_text(
    "GPT-5-nano consistently achieves 0.667 accuracy: it correctly identifies R2 (accept) and "
    "R3 (flag_pattern) but frequently fails R1 (regenerate) -- instead accepting the complaint "
    "and providing an insight. DeepSeek's higher accuracy reflects better sensitivity to "
    "domain-complaint signals (F2 feedback type)."
)

# ── B.6  Inter-Judge Agreement ─────────────────────────────────────────
pdf.add_page()
pdf.section_title("B.6  Inter-Judge Agreement & Cross-Provider Summary")

pdf.subsection_title("B.6.1  Cohen's Kappa (Primary: GPT-4.1-nano / Secondary: Llama 3.3 70B)")
cols_kap = ["Metric", "DeepSeek V3.2", "GPT-5-nano"]
w28 = [60, 55, 55]
pdf.table_header(cols_kap, w28)
kappa_rows = [
    ["Subsampled cells", "26", "26"],
    ["Axis-level pairs", "130", "130"],
    ["Exact agreement", "107 (82.3%)", "107 (82.3%)"],
    ["Off by 1", "13 (10.0%)", "22 (16.9%)"],
    ["Off by 2+", "10 (7.7%)", "1 (0.8%)"],
    ["Cohen's kappa", "0.607 (Substantial)", "0.681 (Substantial)"],
]
for r in kappa_rows:
    pdf.table_row(r, w28)
pdf.body_text("Both providers show 'Substantial' agreement (Landis & Koch) between the primary and secondary LLM judges. "
              "GPT-5-nano has fewer severe disagreements (0.8% off by 2+ vs DeepSeek 7.7%).")

pdf.subsection_title("B.6.2  Cross-Provider Summary Comparison")
cols_sum = ["Metric", "DeepSeek V3.2", "GPT-5-nano", "Interpretation"]
w29 = [48, 38, 38, 46]
pdf.table_header(cols_sum, w29)
summary_rows = [
    ["T0 composite", "4.257", "3.712", "DeepSeek stronger baseline"],
    ["T3 composite", "4.888", "4.981", "GPT-5-nano converges higher"],
    ["T0->T3 gain", "+0.631", "+1.269", "GPT-5-nano benefits more from full pipeline"],
    ["FCR@4 overall", "0.902", "0.891", "Comparable compliance"],
    ["LUR overall", "0.938", "0.969", "Both high loop utilization"],
    ["PPU delta PF", "+0.312", "+1.938", "GPT-5-nano shows larger pattern benefit"],
    ["Cohen's kappa", "0.607", "0.681", "Both 'Substantial' agreement"],
    ["Decision Accuracy", "0.926", "0.667", "DeepSeek better on regenerate decisions"],
    ["Friedman chi2", "96.000", "91.351", "Both highly significant"],
]
for r in summary_rows:
    pdf.table_row(r, w29)

pdf.ln(4)
pdf.subsection_title("B.6.3  Key Takeaway")
pdf.body_text(
    "The ablation study conclusively demonstrates that the AdaCraft pipeline produces "
    "monotonically improving example quality across all 4 tiers, with statistically significant "
    "gains at every layer (profile injection, context management, adaptive feedback). "
    "GPT-5-nano shows larger relative gains (+1.269 T0->T3) while DeepSeek V3.2 has a stronger "
    "zero-shot baseline (4.257). Both providers reach comparable T3 performance (~4.9-5.0), "
    "suggesting an empirical ceiling for the 5-axis G-Eval rubric."
)

# ── Save ─────────────────────────────────────────────────────────────────
pdf.output(OUTPUT)
print(f"PDF generated: {OUTPUT}")
print(f"Pages: {pdf.page_no()}")
