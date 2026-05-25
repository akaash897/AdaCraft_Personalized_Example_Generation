"""
Multilingual Synthetic Profiles & Feedback Battery
6 users (ml_user_01–06): 6 languages × cold start only

Language assignments:
  Indic  : hi (Hindi), ta (Tamil), bn (Bengali)
  Foreign: de (German), ar (Arabic), zh (Mandarin)

Profile–language matching: each user's native language = the test language.
Topics in English for NFEO scenario; topics translated for FNL scenario.

Cold-start only: warm users dropped to reduce eval scale (72 cells vs 144)
while maintaining n=12 paired samples per group for Wilcoxon tests.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Dict, Any, Optional
from core.feedback_store import append_learning_pattern, append_accept_insight

# ── Languages ─────────────────────────────────────────────────────────────────

INDIC_LANGS = ["hi", "ta", "bn"]
FOREIGN_LANGS = ["de", "ar", "zh"]
ALL_LANGS = INDIC_LANGS + FOREIGN_LANGS

LANG_NAMES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "bn": "Bengali",
    "de": "German",
    "ar": "Arabic",
    "zh": "Mandarin",
}

# ── Topics (English + Translations) ───────────────────────────────────────────

TOPICS_EN = [
    "Natural Selection",
    "Cognitive Bias",
    "Compound Interest",
    "Plate Tectonics",
]

# Topic translations for FNL scenario (topic delivered in target language)
TOPIC_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "Natural Selection": {
        "hi": "प्राकृतिक चयन",
        "ta": "இயற்கை தேர்வு",
        "bn": "প্রাকৃতিক নির্বাচন",
        "de": "Natürliche Auslese",
        "ar": "الانتقاء الطبيعي",
        "zh": "自然选择",
    },
    "Cognitive Bias": {
        "hi": "संज्ञानात्मक पूर्वाग्रह",
        "ta": "அறிவாற்றல் சார்பு",
        "bn": "জ্ঞানীয় পক্ষপাত",
        "de": "Kognitive Verzerrung",
        "ar": "التحيز المعرفي",
        "zh": "认知偏差",
    },
    "Compound Interest": {
        "hi": "चक्रवृद्धि ब्याज",
        "ta": "கூட்டு வட்டி",
        "bn": "চক্রবৃদ্ধি সুদ",
        "de": "Zinseszins",
        "ar": "الفائدة المركبة",
        "zh": "复利",
    },
    "Plate Tectonics": {
        "hi": "प्लेट विवर्तनिकी",
        "ta": "தட்டு நகர்வியல்",
        "bn": "প্লেট টেকটোনিক্স",
        "de": "Plattentektonik",
        "ar": "الصفائح التكتونية",
        "zh": "板块构造",
    },
}

# ── Base profiles per language ─────────────────────────────────────────────────
# Each entry: (name, role, education_level, profession, location, cultural_background, lang_code)

_LANG_PROFILES = [
    {
        "lang": "hi",
        "name": "Priya",
        "role": "student",
        "education_level": "high_school",
        "profession": "Student",
        "location": "Mumbai, India",
        "cultural_background": "South Asian",
    },
    {
        "lang": "ta",
        "name": "Meena",
        "role": "nurse",
        "education_level": "professional",
        "profession": "Nurse",
        "location": "Chennai, India",
        "cultural_background": "South Indian",
    },
    {
        "lang": "bn",
        "name": "Arjun",
        "role": "engineer",
        "education_level": "undergraduate",
        "profession": "Software Engineer",
        "location": "Kolkata, India",
        "cultural_background": "Bengali",
    },
    {
        "lang": "de",
        "name": "Klaus",
        "role": "humanities_researcher",
        "education_level": "phd",
        "profession": "Humanities Researcher",
        "location": "Munich, Germany",
        "cultural_background": "European",
    },
    {
        "lang": "ar",
        "name": "Fatima",
        "role": "nurse",
        "education_level": "professional",
        "profession": "Nurse",
        "location": "Cairo, Egypt",
        "cultural_background": "Middle Eastern",
    },
    {
        "lang": "zh",
        "name": "Wei",
        "role": "engineer",
        "education_level": "undergraduate",
        "profession": "Software Engineer",
        "location": "Shanghai, China",
        "cultural_background": "East Asian",
    },
]


def _build_ml_profiles() -> List[Dict[str, Any]]:
    profiles = []
    for uid, lp in enumerate(_LANG_PROFILES, start=1):
        profiles.append({
            "user_id": f"ml_user_{uid:02d}",
            "name": lp["name"],
            "role": lp["role"],
            "education_level": lp["education_level"],
            "profession": lp["profession"],
            "location": lp["location"],
            "cultural_background": lp["cultural_background"],
            "learning_style": "example-based",
            "complexity": "medium",
            "start_mode": "cold",
            "lang": lp["lang"],
            "lang_name": LANG_NAMES[lp["lang"]],
        })
    return profiles


ML_PROFILES: List[Dict[str, Any]] = _build_ml_profiles()

# ── Scripted Feedback Battery ─────────────────────────────────────────────────
# For FNL scenario: all messages in the native language.
# For NFEO scenario: Round 1 critique in native language, Round 2 (F3) in native, Round 3 (FP) in native.
#
# Battery per language:
#   F2  — "not relevant to my field" critique (triggers regenerate)
#   F3  — positive close (triggers accept)
#   FP  — stable-trait message (triggers flag_pattern)
#   A1  — vague dissatisfaction (warm users, triggers regenerate)

ML_FEEDBACK: Dict[str, Dict[str, str]] = {
    "en": {
        "F2": "This example doesn't feel relevant to my field. Can you use something from my professional domain instead?",
        "F3": "This is great! The example really helped me understand the concept.",
        "FP": "I always connect better when examples are grounded in my everyday professional scenarios.",
        "A1": "I don't really get it.",
    },
    "hi": {
        "F2": "यह उदाहरण मेरे क्षेत्र से संबंधित नहीं लगता। क्या आप मेरे डोमेन से कुछ उदाहरण दे सकते हैं?",
        "F3": "यह बहुत अच्छा है! इस उदाहरण ने मुझे अवधारणा समझने में वास्तव में मदद की।",
        "FP": "मैं हमेशा बेहतर समझता हूँ जब उदाहरण मेरे रोज़मर्रा के जीवन से जुड़े होते हैं।",
        "A1": "मुझे यह ठीक से समझ नहीं आया।",
    },
    "ta": {
        "F2": "இந்த உதாரணம் என் துறையுடன் தொடர்பில்லாதது போல் தெரிகிறது. என் தொழில் சார்ந்த உதாரணம் தர முடியுமா?",
        "F3": "இது மிகவும் நன்றாக உள்ளது! இந்த உதாரணம் கருத்தை புரிந்துகொள்ள உதவியது.",
        "FP": "மருத்துவ உதாரணங்கள் எனக்கு கருத்துகளை புரிந்துகொள்ள எளிதாக இருக்கும்.",
        "A1": "இது எனக்கு சரியாக புரியவில்லை.",
    },
    "bn": {
        "F2": "এই উদাহরণটি আমার ক্ষেত্রের সাথে প্রাসঙ্গিক মনে হচ্ছে না। আমার ডোমেন থেকে কিছু উদাহরণ দিতে পারবেন?",
        "F3": "এটা দারুণ! এই উদাহরণটি আমাকে ধারণাটি বুঝতে সত্যিই সাহায্য করেছে।",
        "FP": "কোড-সংক্রান্ত উপমা আমার কাছে সবসময় বিমূর্ত বর্ণনার চেয়ে বেশি স্পষ্ট হয়।",
        "A1": "আমি ঠিকমতো বুঝতে পারলাম না।",
    },
    "de": {
        "F2": "Dieses Beispiel scheint nicht relevant für mein Fachgebiet zu sein. Könnten Sie ein Beispiel aus meiner Domäne verwenden?",
        "F3": "Das ist großartig! Das Beispiel hat mir wirklich geholfen, das Konzept zu verstehen.",
        "FP": "Ich bevorzuge immer Beispiele, die auf historischen oder kulturellen Kontexten basieren.",
        "A1": "Ich verstehe das nicht wirklich.",
    },
    "ar": {
        "F2": "هذا المثال لا يبدو ذا صلة بمجال عملي. هل يمكنك استخدام مثال من تخصصي؟",
        "F3": "هذا رائع! المثال ساعدني حقاً على فهم المفهوم.",
        "FP": "أفهم بشكل أفضل عندما تُستخدم أمثلة من المعدات الطبية لشرح الأفكار المجردة.",
        "A1": "لم أفهم هذا جيداً.",
    },
    "zh": {
        "F2": "这个例子似乎与我的领域不太相关。您能用我专业领域的例子吗？",
        "F3": "太棒了！这个例子真的帮助我理解了这个概念。",
        "FP": "与代码相关的类比对我来说总是比抽象描述更容易理解。",
        "A1": "我不太明白这个。",
    },
}

# ── Feedback sequence per start_mode ──────────────────────────────────────────
# Cold users  (01–06): R1=F2, R2=F3, R3=FP
# Warm users  (07–12): R1=A1, R2=F3, R3=FP


def get_ml_feedback_for_round(user_id: str, round_num: int, lang: str) -> str:
    """
    Return scripted feedback for a given round (1-indexed) in the target language.

    Round 1: F2 (domain complaint → regenerate)
    Round 2: F3 (positive close → accept)
    Round 3: FP (stable-trait → flag_pattern)
    Round 4+: F3 fallback
    """
    battery = ML_FEEDBACK[lang]
    if round_num == 3:
        return battery["FP"]
    if round_num >= 2:
        return battery["F3"]
    return battery["F2"]


# ── Ground Truth Expected Decisions ───────────────────────────────────────────
# Round 1 cold → regenerate (F2 domain complaint)
# Round 1 warm → regenerate (A1 vague complaint — still a dissatisfaction signal)
# Round 2 all  → accept (F3 positive)
# Round 3 all  → flag_pattern (FP stable-trait)

_ML_EXPECTED_DECISIONS: Dict = {
    **{(f"ml_user_{i:02d}", 1): "regenerate"   for i in range(1, 7)},
    **{(f"ml_user_{i:02d}", 2): "accept"        for i in range(1, 7)},
    **{(f"ml_user_{i:02d}", 3): "flag_pattern"  for i in range(1, 7)},
}


def get_ml_expected_decision(user_id: str, round_num: int) -> Optional[str]:
    return _ML_EXPECTED_DECISIONS.get((user_id, round_num))


# ── Warm-start Seeding ─────────────────────────────────────────────────────────

def seed_ml_warm_users() -> None:
    """Pre-seed feedback history for warm-start ml_users (07–12)."""
    warm_users = [p for p in ML_PROFILES if p["start_mode"] == "warm"]
    print(f"Seeding {len(warm_users)} ML warm-start users...")
    for profile in warm_users:
        user_id = profile["user_id"]
        lang_name = profile["lang_name"]
        patterns = [
            {
                "pattern_type": "domain_preference",
                "observation": (
                    f"User strongly prefers examples grounded in their professional domain "
                    f"({profile['profession']}) with real-world scenarios from {profile['location']}. "
                    f"Native language: {lang_name}."
                ),
            },
            {
                "pattern_type": "complexity_preference",
                "observation": (
                    f"User consistently engages better with medium-complexity examples. "
                    f"Responds well to {lang_name}-language content that matches professional context."
                ),
            },
        ]
        for pat in patterns:
            append_learning_pattern(
                user_id=user_id,
                pattern_type=pat["pattern_type"],
                observation=pat["observation"],
                example_id=f"seed_ex_{user_id}",
                source="seed",
            )
        insights = [
            (
                f"Using {profile['name']}'s name and {profile['location']} in the scenario "
                f"significantly improved engagement — the example felt personal and grounded."
            ),
            (
                f"Responding in {lang_name} and tying content to {profile['profession']}'s daily work "
                f"increased relevance scores for this user."
            ),
        ]
        for insight in insights:
            append_accept_insight(
                user_id=user_id,
                insight=insight,
                example_id=f"seed_ex_{user_id}",
            )
        print(f"  Seeded {user_id} ({profile['name']}, {lang_name}, {profile['start_mode']})")
    print("Done.")


def get_ml_profile_by_id(user_id: str) -> Dict[str, Any]:
    for p in ML_PROFILES:
        if p["user_id"] == user_id:
            return p
    raise ValueError(f"ML Profile not found: {user_id}")


if __name__ == "__main__":
    print(f"Total ML profiles : {len(ML_PROFILES)}")
    print(f"Languages         : {ALL_LANGS}")
    cold = [p for p in ML_PROFILES if p["start_mode"] == "cold"]
    warm = [p for p in ML_PROFILES if p["start_mode"] == "warm"]
    print(f"Cold: {len(cold)}, Warm: {len(warm)}")
    for p in ML_PROFILES:
        fb_fnl = get_ml_feedback_for_round(p["user_id"], 1, p["lang"])
        print(f"  {p['user_id']}  {p['lang']}  {p['start_mode']:5}  {p['name']:<8}  R1: {fb_fnl[:50]}")
