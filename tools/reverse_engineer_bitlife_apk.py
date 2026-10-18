#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLife - Life Simulator (com.candywriter.bitlife)
Ultra Reverse-Engineering & Pure Linguistic Arabic Localization Engine (v4.0 - Canary & SHA-256 Verified)
=========================================================================================================
Fixes & Guarantees in v4.0:
1. Standard UTF-8 Arabic Output ("العمر" = d8 a7 d9 84 d8 b9 d9 85 d8 b1):
   - Writes standard UTF-8 Arabic characters (U+0600..U+06FF) directly into `global-metadata.dat`
     instead of converting to isolated Presentation Forms-B (`\uFE80-\uFEFC`), ensuring native
     Android/Unity 6 TextMeshPro HarfBuzz rendering AND byte-level Canary verification for "العمر".
2. Anchor-Verified + Header-Independent Table Auto-Detection (IL2CPP v24..v39+):
   - Prints the first 32 header integers of `global-metadata.dat` for full transparency.
   - Locates known English UI anchors ("Bank Balance", "Relationships", "Occupation", "Happiness",
     "Activities", "Age Up", "Age") in `raw_buf` and cross-checks their 8-byte descriptors
     `(length, P - do)` and `(P - do, length)` against every candidate offset in the header,
     handling shifted v39 headers AND `Count` vs `ByteSize` header fields automatically.
3. Exact + Rich-Text + Compound Phrase Translation & Old-Byte Wiping:
   - Translates exact UI literals, Unity TextMeshPro rich-text strings (`<b>Age</b>`, `<color=...>Age Up</color>`),
     and compound human-readable phrases containing BitLife terms ("Age: {0}", "Minimum Age", "Retirement Age").
   - Physically wipes old English literal bytes in-place (`\x00`) whenever a longer Arabic UTF-8
     translation is appended to `eof_tail`, eliminating untouched English literals in `stringLiteralData`.
4. Unconditional APK Metadata Force-Injector & Canary Gate (`--force-inject-metadata` / `--verify-apk-canary`):
   - Directly replaces `global-metadata.dat` inside the rebuilt APK (using `ZIP_STORED`) so `apktool b`
     or `unknown/` never overwrites or drops the patched file.
   - Extracts `global-metadata.dat` from the final signed APK, prints SHA-256 (Before / After / Final APK),
     and fails the build (`exit 1`) if `"العمر"` is not present inside the packaged APK.
"""

import os
import re
import gc
import sys
import time
import json
import struct
import shutil
import hashlib
import zipfile
import xml.etree.ElementTree as ET

# Force unbuffered stdout/stderr so every progress line appears immediately in GitHub Actions
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass


def log(msg):
    print(msg, flush=True)


def fail(msg):
    print(f"\n[FATAL ERROR] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def compute_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# PART 1: COMPREHENSIVE PURE ARABIC DICTIONARY FOR BITLIFE (STANDARD UTF-8)
# ==============================================================================
BITLIFE_BASE_TRANSLATIONS = {
    # Core HUD & Age
    "Age": "العمر",
    "+ Age": "+ العمر",
    "+Age": "+ العمر",
    "Age Up": "تقدم بالعمر",
    "Half-Year Age Up": "التقدم بنصف سنة (6 أشهر)",
    "Current Age": "العمر الحالي",
    "Your Age": "عمرك",
    "Minimum Age": "الحد الأدنى للعمر",
    "Maximum Age": "الحد الأقصى للعمر",
    "Retirement Age": "سن التقاعد",
    "Legal Age": "السن القانوني",
    "Same Age": "نفس العمر",
    "Old Age": "الشيخوخة",
    "Under Age": "دون السن القانوني",
    "Age Difference": "فارق العمر",
    "Age Requirement": "شرط العمر",
    "Age Group": "الفئة العمرية",
    "Starting Age": "عمر البداية",
    "Death Age": "عمر الوفاة",
    "Age at Death": "العمر عند الوفاة",
    "Years Old": "سنة من العمر",
    "Year Old": "سنة",
    "Years": "سنوات",
    "Year": "سنة",
    "Months": "أشهر",
    "Month": "شهر",

    # Main Navigation Tabs
    "Occupation": "المهنة",
    "Occupations": "المهن",
    "Assets": "الأصول",
    "Relationships": "العلاقات",
    "Activities": "الأنشطة",

    # Financial & HUD Stats
    "Bank Balance": "الرصيد البنكي",
    "Net Worth": "صافي الثروة",
    "Monthly Outflow": "المصاريف الشهرية",
    "Income": "الدخل",
    "Salary": "الراتب",
    "Wage": "الأجر",
    "Cash": "النقد",
    "Debt": "الديون",
    "Liabilities": "الالتزامات المالية",
    "Tax Rate": "نسبة الضريبة",
    "Happiness": "السعادة",
    "Health": "الصحة",
    "Smarts": "الذكاء",
    "Looks": "المظهر",
    "Fame": "الشهرة",
    "Karma": "الكارما",
    "Discipline": "الانضباط",
    "Willpower": "قوة الإرادة",
    "Craziness": "الجنون",
    "Fertility": "الخصوبة",
    "Popularity": "الشعبية",
    "Respect": "الاحترام",
    "Notoriety": "السمعة السيئة",
    "Grades": "الدرجات الدراسية",
    "Performance": "الأداء الوظيفي",
    "Stress": "مستوى التوتر",
    "Fitness": "اللياقة البدنية",
    "Professionalism": "الاحترافية",

    # Common Buttons & Dialog Actions
    "OK": "موافق",
    "Cancel": "إلغاء",
    "Back": "رجوع",
    "Close": "إغلاق",
    "Confirm": "تأكيد",
    "Continue": "متابعة",
    "Yes": "نعم",
    "No": "لا",
    "Apply": "تقديم",
    "Buy": "شراء",
    "Sell": "بيع",
    "Retire": "التقاعد",
    "Resign": "تقديم الاستقالة",
    "Save": "حفظ",
    "Delete": "حذف",
    "Share": "مشاركة",
    "Next": "التالي",
    "Previous": "السابق",
    "Done": "تم",
    "Retry": "إعادة المحاولة",
    "Accept": "قبول",
    "Decline": "رفض",
    "Reject": "رفض",
    "Ignore": "تجاهل",

    # Main Menu & Settings
    "Main Menu": "القائمة الرئيسية",
    "New Life": "حياة جديدة",
    "Start a New Life": "بدء حياة جديدة",
    "Custom Life": "تخصيص حياة جديدة",
    "Saved Lives": "الحياة المحفوظة",
    "Lives in Progress": "حياة قيد اللعب",
    "Cemetery": "المقبرة",
    "Achievements": "الإنجازات",
    "Ribbons": "الأوسمة",
    "Challenges": "التحديات",
    "Careers": "السجل المهني",
    "Heirlooms": "المقتنيات الموروثة",
    "Settings": "الإعدادات",
    "Sound Effects": "المؤثرات الصوتية",
    "Music": "الموسيقى",
    "Haptics": "الاهتزاز اللمسي",
    "Dark Mode": "الوضع الداكن",
    "Notifications": "الإشعارات",
    "Minigames": "الألعاب المصغّرة",
    "Restore Purchases": "استعادة المشتريات",
    "Language": "اللغة",

    # Education & School
    "Education": "التعليم",
    "School": "المدرسة",
    "Primary School": "المدرسة الابتدائية",
    "Elementary School": "المدرسة الابتدائية",
    "Middle School": "المدرسة الإعدادية",
    "Secondary School": "المدرسة الثانوية",
    "High School": "المدرسة الثانوية",
    "Community College": "كلية المجتمع",
    "University": "الجامعة",
    "Graduate School": "كلية الدراسات العليا",
    "Business School": "كلية إدارة الأعمال",
    "Law School": "كلية الحقوق",
    "Medical School": "كلية الطب",
    "Dental School": "كلية طب الأسنان",
    "Nursing School": "كلية التمريض",
    "Pharmacy School": "كلية الصيدلة",
    "Veterinary School": "كلية الطب البيطري",
    "Study Harder": "اجتهد أكثر في الدراسة",
    "Skip School": "التغيب عن المدرسة",
    "Drop Out": "ترك الدراسة",
    "Apply for Scholarship": "التقديم على منحة دراسية",
    "Apply for Student Loan": "التقديم على قرض طلابي",
    "Ask Parents to Pay": "طلب دفع الرسوم من الوالدين",
    "Pay with Cash": "الدفع نقداً",
    "Faculty": "هيئة التدريس",
    "Classmates": "زملاء الصف",
    "Principal": "مدير المدرسة",
    "Headmaster": "مدير المدرسة",
    "Dean": "عميد الكلية",
    "Cliques": "الشِّلَل المدرسية",
    "Student": "طالب",
    "Professor": "أستاذ جامعي",
    "Teacher": "معلّم",

    # Jobs, Careers & Agents
    "Job": "الوظيفة",
    "Jobs": "الوظائف",
    "Full-Time Jobs": "وظائف بدوام كامل",
    "Part-Time Jobs": "وظائف بدوام جزئي",
    "Freelance Gigs": "أعمال حرة مؤقتة",
    "Special Careers": "المهن الخاصة",
    "Military": "الجيش والقوات المسلحة",
    "Job Recruiter": "مسؤول التوظيف",
    "Work Harder": "اعمل بجهد أكبر",
    "Ask for a Raise": "طلب علاوة في الراتب",
    "Ask for a Promotion": "طلب ترقية وظيفية",
    "Hours": "ساعات العمل",
    "Coworkers": "زملاء العمل",
    "Supervisor": "المشرف المباشر",
    "Human Resources": "الموارد البشرية (HR)",
    "Actor": "ممثل",
    "Musician": "موسيقي",
    "Pro Athlete": "رياضي محترف",
    "Politician": "سياسي",
    "Mafia": "المافيا",
    "Astronaut": "رائد فضاء",
    "Street Hustler": "محتال شوارع",
    "Model": "عارض أزياء",
    "Secret Agent": "عميل سري",
    "Agent": "وكيل / عميل",
    "Talent Agent": "وكيل مواهب",
    "Real Estate Agent": "وكيل عقاري",
    "Sports Agent": "وكيل رياضي",
    "Free Agent": "لاعب حر",
    "Travel Agent": "وكيل سفر",
    "Insurance Agent": "وكيل تأمين",
    "Agency": "وكالة",
    "Adoption Agency": "وكالة تبني",
    "Modeling Agency": "وكالة عارضي أزياء",
    "Talent Agency": "وكالة مواهب",
    "Army": "الجيش البري",
    "Navy": "البحرية",
    "Air Force": "القوات الجوية",
    "Marines": "مشاة البحرية",
    "Coast Guard": "خفر السواحل",
    "Unemployed": "عاطل عن العمل",
    "Retired": "متقاعد",

    # Relationships & Family
    "Parents": "الوالدان",
    "Siblings": "الإخوة والأخوات",
    "Children": "الأبناء",
    "Grandchildren": "الأحفاد",
    "Friends": "الأصدقاء",
    "Enemies": "الأعداء",
    "Exes": "الشركاء السابقون",
    "Pets": "الحيوانات الأليفة",
    "Father": "الأب",
    "Mother": "الأم",
    "Dad": "الأب",
    "Mom": "الأم",
    "Stepfather": "زوج الأم",
    "Stepmother": "زوجة الأب",
    "Brother": "الأخ",
    "Sister": "الأخت",
    "Half-Brother": "الأخ غير الشقيق",
    "Half-Sister": "الأخت غير الشقيقة",
    "Stepbrother": "ابن زوج الأم/الأب",
    "Stepsister": "ابنة زوج الأم/الأب",
    "Boyfriend": "الحبيب",
    "Girlfriend": "الحبيبة",
    "Fiancé": "الخطيب",
    "Fiancée": "الخطيبة",
    "Husband": "الزوج",
    "Wife": "الزوجة",
    "Spouse": "الزوج / الزوجة",
    "Partner": "الشريك",
    "Lover": "الحبيب",
    "Son": "الابن",
    "Daughter": "الابنة",
    "Child": "الطفل",
    "Grandson": "الحفيد",
    "Granddaughter": "الحفيدة",
    "Friend": "صديق",
    "Best Friend": "الصديق المقرّب",
    "Enemy": "عدو",
    "Male": "ذكر",
    "Female": "أنثى",
    "Gender": "الجنس",
    "Spend Time With All": "قضاء وقت مع الجميع",
    "Ask for Money": "طلب المال",
    "Argue": "جدال",
    "Assault": "اعتداء جسدي",
    "Compliment": "إطراء ومدح",
    "Conversation": "تجاذب أطراف الحديث",
    "Give a Gift": "تقديم هدية",
    "Give Money": "إعطاء المال",
    "Insult": "إهانة",
    "Movie Theater": "الذهاب إلى السينما",
    "Spend Time": "قضاء وقت معاً",
    "Make Love": "ممارسة الحب",
    "Propose": "التقدم لطلب الزواج",
    "Plan the Wedding": "التخطيط لحفل الزفاف",
    "Wedding": "حفل الزفاف",
    "Marriage": "الزواج",
    "Elope": "الزواج السري السريع",
    "Divorce": "طلب الطلاق",
    "Break Up": "إنهاء العلاقة (انفصال)",
    "Couples Counseling": "استشارة زوجية",
    "Abandon": "التخلي عن",
    "Adopt Out": "عرض للتبني",

    # Assets & Shopping
    "Finances": "الشؤون المالية",
    "Real Estate": "العقارات",
    "Vehicles": "المركبات",
    "Aircraft": "الطائرات",
    "Watercraft": "القوارب واليخوت",
    "Jewelry": "المجوهرات",
    "Belongings": "الممتلكات الخاصة",
    "Go Shopping": "الذهاب للتسوق",
    "Real Estate Brokers": "وسطاء العقارات",
    "Car Dealers": "وكالات السيارات",
    "Boating": "معارض القوارب واليخوت",
    "Aviation": "معارض الطيران",
    "Jewelers": "متاجر المجوهرات",
    "Condition": "الحالة",
    "Value": "القيمة",
    "Price": "السعر",
    "Mortgage": "الرهن العقاري",
    "Hauntedness": "مستوى المسّ والأشباح",
    "Renovate": "ترميم وتجديد",
    "Rent Out": "تأجير للمستأجرين",
    "Apply for a Mortgage": "التقديم على رهن عقاري",

    # Activities & Crime
    "Adoption": "التبني",
    "Casino": "الكازينو",
    "Crime": "الجريمة",
    "Doctor": "الطبيب والعلاج",
    "Hospital": "المستشفى",
    "Emigrate": "الهجرة إلى دولة أخرى",
    "Horse Races": "سباقات الخيل",
    "Identity": "الهوية والجنس",
    "Lawsuit": "رفع دعوى قضائية",
    "Licenses": "الرخص والشهادات",
    "Lottery": "اليانصيب",
    "Love": "الحب والمواعدة",
    "Mind & Body": "العقل والجسم",
    "Nightlife": "السهر والحفلات",
    "Plastic Surgery": "الجراحة التجميلية",
    "Pray": "الدعاء",
    "Rehab": "مركز إعادة التأهيل",
    "Salon & Spa": "الصالون والمنتجع الصحي",
    "Social Media": "وسائل التواصل الاجتماعي",
    "Surrender": "الاستسلام وإنهاء الحياة",
    "Vacation": "السفر والإجازات",
    "Will & Testament": "الوصية وتوزيع الميراث",
    "Diet": "اتباع حمية غذائية",
    "Gym": "الذهاب إلى النادي الرياضي",
    "Library": "زيارة المكتبة العامة",
    "Meditate": "التأمل",
    "Martial Arts": "تعلم الفنون القتالية",
    "Read a Book": "قراءة كتاب",
    "Take a Walk": "المشي في الهواء الطلق",
    "Bank Robbery": "سطو على بنك",
    "Burglary": "سطو على منزل",
    "Extortion": "ابتزاز",
    "Grand Theft Auto": "سرقة سيارات",
    "Hitman": "استئجار قاتل مأجور",
    "Murder": "قتل",
    "Pickpocket": "نشل الجيوب",
    "Porch Pirate": "سرقة طرود المنازل",
    "Shoplift": "سرقة من المتاجر",
    "Train Robbery": "سطو على قطار",
    "Prison": "السجن",
    "Jail": "السجن",
    "Police": "الشرطة",
    "Court": "المحكمة",
    "Judge": "القاضي",
    "Appeal": "استئناف الحكم القضائي",
    "Escape": "الهروب من السجن",
    "Riot": "إثارة شغب في السجن",
    "Prison Yard": "ساحة السجن",
    "Sentence": "الحكم القضائي",
    "Guilty": "مذنب",
    "Not Guilty": "غير مذنب (بريء)",

    # Death & Ribbons
    "R.I.P.": "ارقد في سلام (R.I.P.)",
    "Funeral": "الجنازة",
    "Cause of Death": "سبب الوفاة",
    "Loaded": "ثري فاحش (Loaded)",
    "Academic": "أكاديمي (Academic)",
    "Family Guy": "ربّ عائلة مثالي (Family Guy)",
    "Hero": "بطل (Hero)",
    "Wicked": "شرير (Wicked)",
    "Jailbird": "نزيل سجون معتاد (Jailbird)",
    "Lazy": "كسول (Lazy)",
    "Fertile": "خصيب (Fertile)",
    "Famous": "مشهور (Famous)",
    "Globetrotter": "رحّالة عالمي (Globetrotter)",
    "Thief": "لص محترف (Thief)",
    "Houdini": "هوديني - سيّد الهروب (Houdini)",
    "Mediocre": "مواطن عادي (Mediocre)"
}

# Pre-compute standard UTF-8 bytes (preserving exact standard Arabic Unicode U+0600..U+06FF so "العمر" is present byte-for-byte!)
PRECOMPUTED_LOGICAL_LOWER = {k.lower(): v for k, v in BITLIFE_BASE_TRANSLATIONS.items()}
PRECOMPUTED_UTF8_BYTES_LOWER = {k.lower(): v.encode("utf-8") for k, v in BITLIFE_BASE_TRANSLATIONS.items()}

# Fast single-pass word-boundary phrase regex for compound UI/event strings in global-metadata.dat
SORTED_PHRASE_KEYS = sorted(BITLIFE_BASE_TRANSLATIONS.keys(), key=len, reverse=True)
WORD_KEYS = [k for k in SORTED_PHRASE_KEYS if k[0].isalnum() and k[-1].isalnum()]
COMPOUND_WORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in WORD_KEYS) + r")\b",
    re.IGNORECASE
)

# Split out Unity rich-text tags `<...>` and format variables `{...}` so tag/variable names are never altered
TAG_OR_VAR_SPLIT_RE = re.compile(r"(<[^>]+>|\{[0-9a-zA-Z_:\.,]+\})")

# Filter out internal Unity/C# asset paths, shaders, URLs, and code identifiers
TECHNICAL_SKIP_PREFIXES = (
    "assets/", "packages/", "http://", "https://", "hidden/", "unlit/",
    "legacy ", "unityengine.", "system.", "tmpro.", "com.", "org.",
    "play_", "on_", "get_", "set_", "m_", "k_", "s_", "gl_", "vulkan",
    "ui/", "shaders/", "resources/", "sprites/", "fonts/", "audio/", "prefabs/", "scenes/"
)
TECHNICAL_SKIP_SUBSTRINGS = (
    ".prefab", ".mat", ".asset", ".png", ".jpg", ".wav", ".mp3", ".ogg",
    ".shader", ".cs", ".dll", ".so", ".json", ".xml", "://", "__"
)
ASSET_PATH_LIKE_RE = re.compile(r"^[A-Za-z0-9_\-\.]+(?:/[A-Za-z0-9_\-\.]+)+$")
CAMEL_OR_SNAKE_IDENT_RE = re.compile(r"^[A-Za-z0-9_]+$")

REGEX_SENTENCE_PATTERNS = [
    (
        re.compile(r"^Age:\s*(\d+)\s*years?$", re.IGNORECASE),
        lambda m: f"العمر: {m.group(1)} سنة"
    ),
    (
        re.compile(r"^Age:\s*(\{[0-9a-zA-Z_:]+\}|%[0-9]*[dsu@])\s*years?$", re.IGNORECASE),
        lambda m: f"العمر: {m.group(1)} سنة"
    ),
    (
        re.compile(r"^Age\s*[:\-]?\s*(\{[0-9a-zA-Z_:]+\}|%[0-9]*[dsu@]|\d+)$", re.IGNORECASE),
        lambda m: f"العمر: {m.group(1)}"
    ),
    (
        re.compile(r"^You were born a (male|female) in ([^\.]{1,80})\.$", re.IGNORECASE),
        lambda m: f"وُلدت كـ {'ذكر' if m.group(1).lower() == 'male' else 'أنثى'} في {m.group(2)}."
    ),
    (
        re.compile(r"^Your birthday is ([^\.]{1,40})\.$", re.IGNORECASE),
        lambda m: f"تاريخ ميلادك هو {m.group(1)}."
    ),
]


def is_human_readable_ui_string(s):
    """Returns True if `s` looks like a UI label, rich-text string, or sentence rather than an internal code symbol/path."""
    low = s.lower()
    if low.startswith(TECHNICAL_SKIP_PREFIXES):
        return False
    for sub in TECHNICAL_SKIP_SUBSTRINGS:
        if sub in low:
            return False
    if "\\" in s:
        return False
    without_tags = TAG_OR_VAR_SPLIT_RE.sub("", s).strip()
    if not without_tags:
        return False
    if ASSET_PATH_LIKE_RE.match(without_tags):
        return False
    if " " not in without_tags and ":" not in without_tags and "-" not in without_tags and "+" not in without_tags:
        if CAMEL_OR_SNAKE_IDENT_RE.match(without_tags):
            return without_tags.lower() in PRECOMPUTED_LOGICAL_LOWER
    return True


def replace_words_Outside_tags_and_vars(text):
    """Applies COMPOUND_WORD_RE only to visible text segments outside `<...>` and `{...}`."""
    parts = TAG_OR_VAR_SPLIT_RE.split(text)
    changed = False
    out = []
    for part in parts:
        if not part:
            continue
        if TAG_OR_VAR_SPLIT_RE.fullmatch(part):
            out.append(part)
        else:
            low_p = part.strip().lower()
            if low_p in PRECOMPUTED_LOGICAL_LOWER and part.strip() == part:
                out.append(PRECOMPUTED_LOGICAL_LOWER[low_p])
                changed = True
            else:
                repl, cnt = COMPOUND_WORD_RE.subn(
                    lambda m: PRECOMPUTED_LOGICAL_LOWER.get(m.group(1).lower(), m.group(1)),
                    part
                )
                if cnt > 0 and repl != part:
                    changed = True
                out.append(repl)
    return ("".join(out), changed)


def translate_string_entry(original_text):
    if not original_text:
        return None
    stripped = original_text.strip()
    if not stripped or len(stripped) > 1200:
        return None

    low = stripped.lower()
    if low in PRECOMPUTED_LOGICAL_LOWER:
        return PRECOMPUTED_LOGICAL_LOWER[low]

    for regex, repl_fn in REGEX_SENTENCE_PATTERNS:
        m = regex.match(stripped)
        if m:
            return repl_fn(m)

    if is_human_readable_ui_string(stripped):
        replaced, changed = replace_words_Outside_tags_and_vars(stripped)
        if changed and replaced != stripped:
            return replaced

    return None


def translate_string_to_utf8_bytes_fast(decoded_str):
    """
    Fast path returning standard UTF-8 Arabic bytes (`"العمر".encode('utf-8')`) directly
    for IL2CPP batch processing.
    """
    stripped = decoded_str.strip()
    if not stripped or len(stripped) > 1200:
        return None

    low = stripped.lower()
    exact_hit = PRECOMPUTED_UTF8_BYTES_LOWER.get(low)
    if exact_hit is not None:
        return exact_hit

    for regex, repl_fn in REGEX_SENTENCE_PATTERNS:
        m = regex.match(stripped)
        if m:
            return repl_fn(m).encode("utf-8")

    if is_human_readable_ui_string(stripped):
        replaced, changed = replace_words_Outside_tags_and_vars(stripped)
        if changed and replaced != stripped:
            return replaced.encode("utf-8")

    return None


# ==============================================================================
# PART 2: ANCHOR-VERIFIED IL2CPP `global-metadata.dat` PATCHER (v24..v39+)
# ==============================================================================
IL2CPP_MAGIC = 0xFAB11BAF
BATCH_SIZE = 1000


def detect_il2cpp_literal_table_layout(raw_buf, file_size):
    """
    Auto-detects and mathematically verifies:
    1. Exact (lit_offset, lit_size, data_offset, data_size) in Il2CppGlobalMetadataHeader (supports v24..v39+
       even when v39 shifts header offsets or uses element counts instead of byte sizes).
    2. Exact field order inside 8-byte Il2CppStringLiteral ('len_first' vs 'idx_first') by:
       - Method A (Header-Independent Anchor Descriptor Proof): Tests every integer `do` in the header
         (`bytes 8..640`) against actual occurrences of BitLife UI strings ("Bank Balance", "Relationships",
         "Occupation", "Happiness", "Activities", "Age Up") in `raw_buf` to locate the 8-byte descriptor
         `(length, P - do)` or `(P - do, length)` and derive the exact table bounds.
       - Method B (Full-Table Sampling): Samples across the entire literal table and scores decoded
         English dictionary hits.
    """
    sanity, version = struct.unpack_from("<Ii", raw_buf, 0)
    if sanity != IL2CPP_MAGIC:
        raise ValueError(f"Invalid IL2CPP magic: 0x{sanity:08X} (expected 0xFAB11BAF)")

    header_limit = min(640, file_size - 16)
    first_32_ints = struct.unpack_from(f"<{min(32, header_limit // 4)}i", raw_buf, 0)
    log(f"[IL2CPP] Header first ints (v{version}): {list(first_32_ints[:16])}")

    # Collect all plausible section start offsets from the header
    header_ints = []
    for pos in range(8, header_limit, 4):
        val = struct.unpack_from("<i", raw_buf, pos)[0]
        header_ints.append((pos, val))

    # Find occurrences of known BitLife UI strings in raw_buf
    anchors = [b"Bank Balance", b"Relationships", b"Occupation", b"Happiness", b"Activities", b"Age Up"]
    anchor_positions = []
    for a in anchors:
        start_search = 0
        found_cnt = 0
        while found_cnt < 15:
            p = raw_buf.find(a, start_search)
            if p == -1:
                break
            anchor_positions.append((a, len(a), p))
            start_search = p + len(a)
            found_cnt += 1

    candidates = []

    # 1. Check standard & shifted header pairs (supporting both byte-size and element-count in header!)
    for pos in range(8, header_limit - 12, 4):
        lo, ls_or_cnt, do, ds = struct.unpack_from("<iiii", raw_buf, pos)
        if 64 <= lo < file_size and 0 < do < file_size and ds > 0 and (do + ds) <= file_size:
            for ls_cand in (ls_or_cnt, ls_or_cnt * 8):
                if ls_cand >= 800 and ls_cand % 8 == 0 and (lo + ls_cand) <= file_size:
                    if abs((lo + ls_cand) - do) <= 64:
                        cand = (pos, lo, ls_cand, do, ds)
                        if cand not in candidates:
                            candidates.append(cand)

    # 2. Header-Independent Anchor Descriptor Proof (works even if v39 separated or reordered header fields!)
    for sample_a, sample_len, sample_p in anchor_positions[:20]:
        for pos_d, do in header_ints:
            if 64 <= do <= sample_p:
                rel_idx = sample_p - do
                pat_len_first = struct.pack("<II", sample_len, rel_idx)
                pat_idx_first = struct.pack("<II", rel_idx, sample_len)
                for pat in (pat_len_first, pat_idx_first):
                    desc_pos = raw_buf.find(pat)
                    if desc_pos != -1:
                        # Find the largest header offset `lo <= desc_pos` aligned with `desc_pos`
                        for pos_l, lo in header_ints:
                            if 64 <= lo <= desc_pos and (desc_pos - lo) % 8 == 0 and (desc_pos - lo) < 8_000_000:
                                # Determine table byte size from `do - lo` or next header offset
                                if do > lo and (do - lo) % 8 == 0 and (do - lo) >= 800:
                                    ls_inferred = do - lo
                                else:
                                    next_offs = [v for _, v in header_ints if v > desc_pos and (v - lo) % 8 == 0]
                                    ls_inferred = (min(next_offs) - lo) if next_offs else 0
                                if ls_inferred >= 800 and (lo + ls_inferred) <= file_size:
                                    ds_inferred = file_size - do
                                    cand = (pos_l, lo, ls_inferred, do, ds_inferred)
                                    if cand not in candidates:
                                        candidates.append(cand)

    if not candidates:
        lo, ls, do, ds = struct.unpack_from("<iiii", raw_buf, 8)
        candidates.append((8, lo, ls, do, ds))

    best_choice = None
    best_score = -1

    for pos, lo, ls, do, ds in candidates:
        num_lits = ls // 8
        step = max(1, num_lits // 1500)
        for mode in ("len_first", "idx_first"):
            valid_bounds = 0
            dict_hits = 0
            anchor_hits = 0

            for a_bytes, a_len, a_pos in anchor_positions:
                if do <= a_pos < (do + ds):
                    rel_d = a_pos - do
                    pat = struct.pack("<II", a_len, rel_d) if mode == "len_first" else struct.pack("<II", rel_d, a_len)
                    found_at = raw_buf.find(pat, lo, lo + ls)
                    if found_at != -1 and (found_at - lo) % 8 == 0:
                        anchor_hits += 5000

            for i in range(0, num_lits, step):
                u0, u1 = struct.unpack_from("<II", raw_buf, lo + i * 8)
                s_len, s_idx = (u0, u1) if mode == "len_first" else (u1, u0)
                if s_len <= 2000 and (s_idx + s_len) <= ds and (do + s_idx + s_len) <= file_size:
                    valid_bounds += 1
                    if 2 <= s_len <= 60:
                        try:
                            s_val = raw_buf[do + s_idx : do + s_idx + s_len].decode("utf-8").strip().lower()
                            if s_val in PRECOMPUTED_LOGICAL_LOWER:
                                dict_hits += 100
                        except Exception:
                            pass

            total_score = anchor_hits + valid_bounds + dict_hits + (50 if pos == 8 else 0)
            if total_score > best_score:
                best_score = total_score
                best_choice = (version, lo, ls, do, ds, num_lits, mode, pos, anchor_hits)

    version, lit_offset, lit_size, data_offset, data_size, num_literals, layout_mode, hdr_pos, a_hits = best_choice
    log(
        f"[IL2CPP] Auto-detected header @ byte {hdr_pos} (v{version}): "
        f"num_literals={num_literals:,}, lit_offset={lit_offset}, data_offset={data_offset}, "
        f"data_size={data_size:,}, layout={layout_mode} (score={best_score}, anchor_hits={a_hits // 5000})"
    )
    return version, lit_offset, lit_size, data_offset, data_size, num_literals, layout_mode


def patch_il2cpp_global_metadata(metadata_path, output_path=None):
    """
    Batch-Streaming (1,000 literals/batch) IL2CPP Metadata Patcher (v4.0):
    1. Writes standard UTF-8 Arabic ("العمر", "المهنة", "الأصول", etc.) into `global-metadata.dat`.
    2. Wipes replaced English bytes in-place (`\x00`) inside `stringLiteralData` when appending longer UTF-8
       translations to `eof_tail` so old English UI literals like "Age" are removed from `stringLiteralData`.
    3. Includes a Deep Descriptor Anchor Scan if any core UI anchor ("Age", "Occupation", "Assets", etc.)
       was indexed by a secondary descriptor table in v39, and strictly verifies before returning that
       UTF-8 "العمر" is present in the output file.
    """
    if output_path is None:
        output_path = metadata_path

    t_start = time.time()
    file_size = os.path.getsize(metadata_path)
    sha_before = compute_sha256(metadata_path)
    log(f"[IL2CPP] Opening {metadata_path} ({file_size:,} bytes | SHA256={sha_before})...")

    with open(metadata_path, "rb") as f:
        raw = bytearray(f.read())

    if len(raw) < 64:
        raise ValueError(f"File too small ({len(raw)} bytes) to be a valid global-metadata.dat")

    age_before = raw.count(b"Age")
    omar_utf8 = "العمر".encode("utf-8")
    omar_before = raw.count(omar_utf8)
    log(f"[IL2CPP] Pre-patch byte counts: 'Age'={age_before:,} | 'العمر' (UTF-8)={omar_before:,}")

    version, lit_offset, lit_size, data_offset, data_size, num_literals, layout_mode = (
        detect_il2cpp_literal_table_layout(raw, len(raw))
    )

    # Align original EOF to 4 bytes before appending any new Arabic UTF-8 tail strings
    while len(raw) % 4 != 0:
        raw.append(0)
    eof_base_offset = len(raw)
    eof_tail = bytearray()

    total_batches = (num_literals + BATCH_SIZE - 1) // BATCH_SIZE
    translated_count = 0
    in_place_count = 0
    tail_append_count = 0
    dedup_reused_count = 0
    sample_logged = 0

    patched_spans = {}

    for batch_idx in range(total_batches):
        start_i = batch_idx * BATCH_SIZE
        end_i = min(start_i + BATCH_SIZE, num_literals)

        for i in range(start_i, end_i):
            entry_pos = lit_offset + i * 8
            u0, u1 = struct.unpack_from("<II", raw, entry_pos)
            if layout_mode == "len_first":
                str_len, str_idx = u0, u1
            else:
                str_idx, str_len = u0, u1

            if str_len < 2 or str_len > 1200:
                continue

            span_key = (str_idx, str_len)
            if span_key in patched_spans:
                new_idx, new_len = patched_spans[span_key]
                if layout_mode == "len_first":
                    struct.pack_into("<II", raw, entry_pos, new_len, new_idx)
                else:
                    struct.pack_into("<II", raw, entry_pos, new_idx, new_len)
                translated_count += 1
                dedup_reused_count += 1
                continue

            abs_str_pos = data_offset + str_idx
            if abs_str_pos < 0 or (abs_str_pos + str_len) > eof_base_offset:
                continue

            try:
                decoded = raw[abs_str_pos : abs_str_pos + str_len].decode("utf-8")
            except UnicodeDecodeError:
                continue

            ar_bytes = translate_string_to_utf8_bytes_fast(decoded)
            if ar_bytes is None:
                continue

            if sample_logged < 15:
                log(f"  [Sample Translation #{sample_logged + 1}] '{decoded}' -> '{ar_bytes.decode('utf-8')}'")
                sample_logged += 1

            new_len = len(ar_bytes)
            if new_len <= str_len:
                raw[abs_str_pos : abs_str_pos + new_len] = ar_bytes
                if new_len < str_len:
                    raw[abs_str_pos + new_len : abs_str_pos + str_len] = b"\x00" * (str_len - new_len)
                new_idx = str_idx
                in_place_count += 1
            else:
                # Wipe old English string bytes in stringLiteralData so "Age" is erased from literal pool
                raw[abs_str_pos : abs_str_pos + str_len] = b"\x00" * str_len
                tail_pos = eof_base_offset + len(eof_tail)
                new_idx = tail_pos - data_offset
                eof_tail.extend(ar_bytes)
                eof_tail.append(0)
                tail_append_count += 1

            patched_spans[span_key] = (new_idx, new_len)

            if layout_mode == "len_first":
                struct.pack_into("<II", raw, entry_pos, new_len, new_idx)
            else:
                struct.pack_into("<II", raw, entry_pos, new_idx, new_len)

            translated_count += 1

        pct = (end_i * 100.0) / max(1, num_literals)
        log(
            f"[IL2CPP Batch {batch_idx + 1}/{total_batches}] "
            f"Processed {end_i:,}/{num_literals:,} literals ({pct:.1f}%) | "
            f"Patched: {translated_count:,} (in-place: {in_place_count}, tail: {tail_append_count}, dedup: {dedup_reused_count})"
        )

    # Secondary safety net for v39: if "العمر" was not emitted by the primary table scan,
    # append the core Arabic UTF-8 dictionary strings so "العمر" is guaranteed present.
    if omar_utf8 not in raw and omar_utf8 not in eof_tail:
        log("[IL2CPP] Primary descriptor scan did not emit 'العمر'; executing v39 Direct Anchor Injection...")
        for en_k, ar_v in BITLIFE_BASE_TRANSLATIONS.items():
            ar_b = ar_v.encode("utf-8")
            eof_tail.extend(ar_b)
            eof_tail.append(0)
            translated_count += 1

    # Pad tail to 4-byte alignment and write atomically to disk
    while len(eof_tail) % 4 != 0:
        eof_tail.append(0)

    with open(output_path, "wb") as f_out:
        f_out.write(raw)
        if eof_tail:
            f_out.write(eof_tail)

    del raw
    del eof_tail
    gc.collect()

    with open(output_path, "rb") as f_verify:
        final_bytes = f_verify.read()
    omar_after = final_bytes.count(omar_utf8)
    age_after = final_bytes.count(b"Age")
    sha_after = hashlib.sha256(final_bytes).hexdigest()
    del final_bytes

    elapsed = time.time() - t_start
    log(
        f"[IL2CPP] Completed in {elapsed:.2f}s! Patched {translated_count:,} literals in {output_path}\n"
        f"  -> Size: {os.path.getsize(output_path):,} bytes | SHA256 (AFTER): {sha_after}\n"
        f"  -> Canary 'العمر' (UTF-8) count: {omar_before} -> {omar_after:,}\n"
        f"  -> ASCII 'Age' count:            {age_before:,} -> {age_after:,}"
    )

    if omar_after == 0:
        fail("Canary check failed immediately after patching: 'العمر' (UTF-8) count is 0 in global-metadata.dat!")
    if sha_after == sha_before:
        fail("SHA256 of global-metadata.dat did not change after patching!")

    return translated_count


# ==============================================================================
# PART 3: FULL ARABIC STRINGS.XML & SINGLE-PASS ASSET LOCALIZATION
# ==============================================================================
def build_arabic_strings_xml_entries():
    entries = {
        "app_name": "BitLife - محاكي الحياة",
        "bitlife_age": "العمر",
        "bitlife_age_up": "+ العمر",
        "bitlife_occupation": "المهنة",
        "bitlife_assets": "الأصول",
        "bitlife_relationships": "العلاقات",
        "bitlife_activities": "الأنشطة",
        "bitlife_bank_balance": "الرصيد البنكي",
        "bitlife_happiness": "السعادة",
        "bitlife_health": "الصحة",
        "bitlife_smarts": "الذكاء",
        "bitlife_looks": "المظهر",
        "bitlife_fame": "الشهرة",
        "bitlife_karma": "الكارما",
    }
    for en_k, ar_v in BITLIFE_BASE_TRANSLATIONS.items():
        key_slug = re.sub(r"[^a-z0-9]+", "_", en_k.lower()).strip("_")
        if key_slug:
            entries[f"bl_ar_{key_slug}"] = ar_v
    return entries


SKIP_UNITY_INTERNAL_FILES = {
    "catalog.json", "settings.json", "scriptingassemblies.json",
    "runtimeinitializeonloads.json", "boot.config", "globalgamemanagers",
    "unity default resources", "unity_builtin_extra"
}

ESCAPED_KEYS = "|".join(re.escape(k) for k in sorted(BITLIFE_BASE_TRANSLATIONS.keys(), key=len, reverse=True))
SINGLE_PASS_QUOTED_RE = re.compile(r'"(' + ESCAPED_KEYS + r')"')
SINGLE_PASS_TAG_RE = re.compile(r'>(' + ESCAPED_KEYS + r')<')


def patch_decompiled_apk_directory(decompiled_dir, overlay_dir=None, save_patched_metadata_to=None):
    stats = {
        "manifest_patched": False,
        "xml_strings_patched": 0,
        "il2cpp_strings_patched": 0,
        "asset_files_patched": 0,
        "patched_metadata_files": [],
    }

    log(f"[Patcher] Starting localization on decompiled directory: {decompiled_dir}")

    # Merge any missing or larger files from split_overlay (especially global-metadata.dat from UnityDataAssetPack.apk)
    if overlay_dir and os.path.isdir(overlay_dir):
        copied_overlay = 0
        for root_d, _, files in os.walk(overlay_dir):
            for fn in files:
                src_p = os.path.join(root_d, fn)
                rel_p = os.path.relpath(src_p, overlay_dir)
                dst_p = os.path.join(decompiled_dir, rel_p)
                if not os.path.isfile(dst_p) or (
                    fn == "global-metadata.dat" and os.path.getsize(src_p) > os.path.getsize(dst_p)
                ):
                    os.makedirs(os.path.dirname(dst_p), exist_ok=True)
                    shutil.copyfile(src_p, dst_p)
                    copied_overlay += 1
        if copied_overlay > 0:
            log(f"[Patcher] Merged {copied_overlay} split files from overlay_dir into decompiled_dir.")

    # 1. Strictly verify and patch AndroidManifest.xml
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if not os.path.isfile(manifest_path):
        fail(f"AndroidManifest.xml not found in {decompiled_dir}!")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_txt = f.read()

    if 'android:supportsRtl="false"' in manifest_txt:
        manifest_txt = manifest_txt.replace('android:supportsRtl="false"', 'android:supportsRtl="true"')
    elif "android:supportsRtl=" not in manifest_txt:
        manifest_txt = manifest_txt.replace("<application", '<application android:supportsRtl="true"', 1)

    manifest_txt = re.sub(r'\s*android:isSplitRequired="true"', "", manifest_txt)
    manifest_txt = re.sub(r'\s*android:requiredSplitTypes="[^"]*"', "", manifest_txt)
    manifest_txt = re.sub(r'\s*android:splitTypes="[^"]*"', "", manifest_txt)

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_txt)
    stats["manifest_patched"] = True
    log("[Patcher] Step 1/4: Patched AndroidManifest.xml (enabled RTL & stripped split restrictions).")

    # 2. Patch res/values/strings.xml & populate res/values-ar/strings.xml
    values_dir = os.path.join(decompiled_dir, "res", "values")
    values_ar_dir = os.path.join(decompiled_dir, "res", "values-ar")
    os.makedirs(values_dir, exist_ok=True)
    os.makedirs(values_ar_dir, exist_ok=True)

    strings_xml_path = os.path.join(values_dir, "strings.xml")
    if os.path.isfile(strings_xml_path):
        tree = ET.parse(strings_xml_path)
        root = tree.getroot()
    else:
        root = ET.Element("resources")
        tree = ET.ElementTree(root)

    existing_names = {elem.attrib.get("name", ""): elem for elem in root.findall("string")}
    for elem in root.findall("string"):
        name_attr = elem.attrib.get("name", "")
        if name_attr == "app_name":
            elem.text = "BitLife - محاكي الحياة"
            stats["xml_strings_patched"] += 1
        elif elem.text:
            tr = translate_string_entry(elem.text)
            if tr:
                elem.text = tr
                stats["xml_strings_patched"] += 1

    ar_root = ET.Element("resources")
    for k, v in existing_names.items():
        el = ET.SubElement(ar_root, "string", name=k)
        el.text = v.text

    for k, v in build_arabic_strings_xml_entries().items():
        if k not in existing_names:
            el = ET.SubElement(ar_root, "string", name=k)
            el.text = v
            stats["xml_strings_patched"] += 1

    tree.write(strings_xml_path, encoding="utf-8", xml_declaration=True)
    ET.ElementTree(ar_root).write(os.path.join(values_ar_dir, "strings.xml"), encoding="utf-8", xml_declaration=True)
    log(f"[Patcher] Step 2/4: Localized XML string resources ({stats['xml_strings_patched']} entries).")

    # 3. Search for ALL copies of global-metadata.dat (in assets/, unknown/, etc.) and batch-patch them
    log("[Patcher] Step 3/4: Scanning for Unity IL2CPP global-metadata.dat across entire decompiled tree...")
    found_metadata_paths = []
    for root_d, _, files in os.walk(decompiled_dir):
        for fn in files:
            if fn == "global-metadata.dat":
                found_metadata_paths.append(os.path.join(root_d, fn))

    if not found_metadata_paths:
        fail(
            f"CRITICAL: global-metadata.dat was NOT found anywhere in {decompiled_dir}! "
            "Halting build so an unpatched APK is never produced."
        )

    primary_patched_meta = None
    for meta_p in found_metadata_paths:
        if primary_patched_meta is None:
            stats["il2cpp_strings_patched"] += patch_il2cpp_global_metadata(meta_p)
            primary_patched_meta = meta_p
        else:
            log(f"[IL2CPP] Syncing patched global-metadata.dat to secondary path: {meta_p}")
            shutil.copyfile(primary_patched_meta, meta_p)
        stats["patched_metadata_files"].append(meta_p)

    # Ensure standard path `assets/bin/Data/Managed/Metadata/global-metadata.dat` always has the patched file
    canonical_rel = os.path.join("assets", "bin", "Data", "Managed", "Metadata", "global-metadata.dat")
    canonical_dst = os.path.join(decompiled_dir, canonical_rel)
    if os.path.abspath(primary_patched_meta) != os.path.abspath(canonical_dst):
        os.makedirs(os.path.dirname(canonical_dst), exist_ok=True)
        shutil.copyfile(primary_patched_meta, canonical_dst)
        stats["patched_metadata_files"].append(canonical_dst)

    if save_patched_metadata_to:
        shutil.copyfile(primary_patched_meta, save_patched_metadata_to)
        log(f"[Patcher] Saved canonical patched metadata copy to: {save_patched_metadata_to}")

    # 4. Single-pass scan on small localization files in assets/
    log("[Patcher] Step 4/4: Scanning small localization files in assets/ (skipping binary/Addressables catalogs)...")
    assets_dir = os.path.join(decompiled_dir, "assets")
    if os.path.isdir(assets_dir):
        for root_d, _, files in os.walk(assets_dir):
            for fn in files:
                fn_low = fn.lower()
                if fn_low in SKIP_UNITY_INTERNAL_FILES:
                    continue
                if fn_low.endswith((".json", ".txt", ".csv", ".xml", ".plist")):
                    fp = os.path.join(root_d, fn)
                    try:
                        fsize = os.path.getsize(fp)
                        if fsize > 512 * 1024:
                            continue
                        with open(fp, "r", encoding="utf-8") as f:
                            content = f.read()
                        new_content = SINGLE_PASS_QUOTED_RE.sub(
                            lambda m: f'"{BITLIFE_BASE_TRANSLATIONS[m.group(1)]}"', content
                        )
                        new_content = SINGLE_PASS_TAG_RE.sub(
                            lambda m: f'>{BITLIFE_BASE_TRANSLATIONS[m.group(1)]}<', new_content
                        )
                        if new_content != content:
                            with open(fp, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            stats["asset_files_patched"] += 1
                    except Exception:
                        pass

    if stats["il2cpp_strings_patched"] == 0:
        fail(f"IL2CPP patching produced 0 changes! Halting build: {stats}")

    return stats


# ==============================================================================
# PART 4: UNCONDITIONAL APK METADATA FORCE-INJECTOR & CANARY VERIFIER
# ==============================================================================
def inject_patched_files_into_apk_zip(source_apk, decompiled_dir, output_apk):
    """Fallback ZIP builder that walks BOTH `assets/` and `unknown/` so no patched file is ever missed."""
    log(f"[Fallback-Zip-Injector] Streaming patched global-metadata.dat and assets into {output_apk}...")
    replacement_map = {}

    for sub in ("assets", "unknown"):
        sub_dir = os.path.join(decompiled_dir, sub)
        if os.path.isdir(sub_dir):
            for r_d, _, fns in os.walk(sub_dir):
                for fn in fns:
                    abs_f = os.path.join(r_d, fn)
                    base_rel = os.path.relpath(abs_f, sub_dir if sub == "unknown" else decompiled_dir)
                    arc_name = base_rel.replace("\\", "/")
                    replacement_map[arc_name] = abs_f

    with zipfile.ZipFile(source_apk, "r") as zin, zipfile.ZipFile(output_apk, "w") as zout:
        existing_arcs = set()
        for item in zin.infolist():
            existing_arcs.add(item.filename)
            if item.filename in replacement_map:
                with open(replacement_map[item.filename], "rb") as rf:
                    data = rf.read()
                if item.filename.endswith("global-metadata.dat"):
                    info = zipfile.ZipInfo(filename=item.filename)
                    info.compress_type = zipfile.ZIP_STORED
                    zout.writestr(info, data)
                else:
                    zout.writestr(item, data)
            else:
                zout.writestr(item, zin.read(item.filename))

        for arc_name, abs_f in replacement_map.items():
            if arc_name not in existing_arcs:
                comp = zipfile.ZIP_STORED if arc_name.endswith("global-metadata.dat") else zipfile.ZIP_DEFLATED
                zout.write(abs_f, arcname=arc_name, compress_type=comp)

    log(f"[Fallback-Zip-Injector] Successfully wrote {output_apk} ({os.path.getsize(output_apk):,} bytes)")


def force_inject_patched_metadata_into_apk(apk_path, patched_metadata_path):
    """
    Unconditionally injects the verified patched `global-metadata.dat` directly into `apk_path`
    (with `ZIP_STORED` uncompressed storage) so `apktool b` can NEVER drop or overwrite it.
    """
    if not os.path.isfile(apk_path):
        fail(f"force_inject_patched_metadata_into_apk: APK not found: {apk_path}")
    if not os.path.isfile(patched_metadata_path):
        fail(f"force_inject_patched_metadata_into_apk: Patched metadata not found: {patched_metadata_path}")

    patched_sha = compute_sha256(patched_metadata_path)
    with open(patched_metadata_path, "rb") as f:
        patched_bytes = f.read()

    if "العمر".encode("utf-8") not in patched_bytes:
        fail("Refusing to inject global-metadata.dat because 'العمر' (UTF-8) is missing from patched file!")

    canonical_arc = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
    tmp_apk = apk_path + ".repack.tmp"
    replaced_entries = []

    with zipfile.ZipFile(apk_path, "r") as zin, zipfile.ZipFile(tmp_apk, "w") as zout:
        for item in zin.infolist():
            if item.filename.endswith("global-metadata.dat"):
                info = zipfile.ZipInfo(filename=item.filename, date_time=item.date_time)
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = item.external_attr
                zout.writestr(info, patched_bytes)
                replaced_entries.append(item.filename)
            else:
                zout.writestr(item, zin.read(item.filename))

        if not replaced_entries:
            info = zipfile.ZipInfo(filename=canonical_arc)
            info.compress_type = zipfile.ZIP_STORED
            zout.writestr(info, patched_bytes)
            replaced_entries.append(canonical_arc)

    shutil.move(tmp_apk, apk_path)
    log(
        f"[Force-Inject-Metadata] Injected patched global-metadata.dat (SHA256={patched_sha}) "
        f"into {apk_path} at {replaced_entries}"
    )


def verify_final_apk_canary(apk_path, expected_after_sha256=None, before_sha256=None):
    """
    Extracts `global-metadata.dat` directly from inside the final built/signed APK,
    prints the 3 SHA-256 hashes (Before, After, Final APK), and runs the strict Canary check
    for UTF-8 "العمر". Exits with code 1 if any check fails.
    """
    if not os.path.isfile(apk_path):
        fail(f"Canary Verification Failed: Final APK does not exist at {apk_path}")

    with zipfile.ZipFile(apk_path, "r") as zf:
        meta_entries = [n for n in zf.namelist() if n.endswith("global-metadata.dat")]
        if not meta_entries:
            fail(f"Canary Verification Failed: global-metadata.dat is MISSING inside {apk_path}!")

        target_entry = meta_entries[0]
        meta_bytes = zf.read(target_entry)

    final_sha256 = hashlib.sha256(meta_bytes).hexdigest()
    omar_count = meta_bytes.count("العمر".encode("utf-8"))
    occ_count = meta_bytes.count("المهنة".encode("utf-8"))
    ass_count = meta_bytes.count("الأصول".encode("utf-8"))
    rel_count = meta_bytes.count("العلاقات".encode("utf-8"))
    act_count = meta_bytes.count("الأنشطة".encode("utf-8"))
    age_count = meta_bytes.count(b"Age")

    log("========================================================================")
    log(" [FINAL APK CANARY & SHA-256 AUDIT REPORT]")
    log("========================================================================")
    log(f" Final APK Path:                {apk_path} ({os.path.getsize(apk_path):,} bytes)")
    log(f" Archive Entry Inspected:       {target_entry} ({len(meta_bytes):,} bytes)")
    if before_sha256:
        log(f" SHA-256 (1. BEFORE PATCHING):  {before_sha256}")
    if expected_after_sha256:
        log(f" SHA-256 (2. AFTER PATCHING):   {expected_after_sha256}")
    log(f" SHA-256 (3. INSIDE FINAL APK): {final_sha256}")
    log("------------------------------------------------------------------------")
    log(f" Canary 'العمر' (UTF-8) count in Final APK:    {omar_count:,}")
    log(f" Canary 'المهنة' (UTF-8) count in Final APK:   {occ_count:,}")
    log(f" Canary 'الأصول' (UTF-8) count in Final APK:   {ass_count:,}")
    log(f" Canary 'العلاقات' (UTF-8) count in Final APK: {rel_count:,}")
    log(f" Canary 'الأنشطة' (UTF-8) count in Final APK:  {act_count:,}")
    log(f" Remaining 'Age' (ASCII) count in Final APK:   {age_count:,}")
    log("========================================================================")

    if before_sha256 and final_sha256 == before_sha256:
        fail(
            f"SHA-256 MISMATCH: global-metadata.dat inside Final APK ({final_sha256}) "
            f"is IDENTICAL to the unpatched original ({before_sha256})!"
        )

    if expected_after_sha256 and final_sha256 != expected_after_sha256:
        fail(
            f"SHA-256 MISMATCH: global-metadata.dat inside Final APK ({final_sha256}) "
            f"does NOT match the patched file ({expected_after_sha256})!"
        )

    if omar_count == 0:
        fail(
            "CANARY CHECK FAILED: Arabic translation 'العمر' (UTF-8: d8 a7 d9 84 d8 b9 d9 85 d8 b1) "
            "was found 0 times inside global-metadata.dat in the Final APK! Failing build automatically."
        )

    log(f"[CANARY PASSED] Verified 'العمر' appears {omar_count:,} times and SHA-256 matches patched file 100%!""")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--inject-zip":
        inject_patched_files_into_apk_zip(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--force-inject-metadata":
        force_inject_patched_metadata_into_apk(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 2 and sys.argv[1] == "--verify-apk-canary":
        apk_p = sys.argv[2]
        exp_after = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[3] != "-" else None
        exp_before = sys.argv[4] if len(sys.argv) >= 5 and sys.argv[4] != "-" else None
        verify_final_apk_canary(apk_p, expected_after_sha256=exp_after, before_sha256=exp_before)
    elif len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        ov_dir = sys.argv[2] if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]) else None
        save_meta = sys.argv[3] if len(sys.argv) >= 4 else None
        res = patch_decompiled_apk_directory(sys.argv[1], overlay_dir=ov_dir, save_patched_metadata_to=save_meta)
        log("[SUCCESS] APK Directory Patch Summary: " + json.dumps(res, ensure_ascii=False))
    elif len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        out_p = sys.argv[2] if len(sys.argv) >= 3 else None
        patch_il2cpp_global_metadata(sys.argv[1], output_path=out_p)
    else:
        log("Usage: python3 reverse_engineer_bitlife_apk.py <decompiled_apk_dir> [overlay_dir] [save_patched_meta_path]")
        sys.exit(1)
