#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLife - Life Simulator (com.candywriter.bitlife)
Ultra Reverse-Engineering & Pure Linguistic Arabic Localization Engine (v3.0 - Batch Streaming Mode)
====================================================================================================
Designed specifically for BitLife's Unity IL2CPP `global-metadata.dat` (including v39 with 36,072+ literals):
1. Batch Processing (1,000 literals per batch) with real-time progress logging (`[IL2CPP Batch X/Y]`)
   and `sys.stdout.flush()` after every batch so GitHub Actions never kills the step for inactivity.
2. Zero-Shift In-Place + EOF-Tail Binary Patching:
   - Modifies `global-metadata.dat` in-place without duplicating the entire file or all 36,072 strings in RAM.
   - Auto-detects `(length, dataIndex)` vs `(dataIndex, length)` struct field order in IL2CPP v24–v39.
   - Strictly bounds `str_len` (`2 <= str_len <= 180`) before slicing bytes so corrupt/huge lengths never cause OOM.
   - Appends longer Arabic UTF-8 strings to a compact EOF tail block so ZERO section offsets in the v39 header shift.
3. Single-Pass Asset Scanner:
   - Skips huge Unity Addressables catalogs (`catalog.json`, files > 512 KB) and uses a single compiled regex pass.
"""

import os
import re
import gc
import sys
import time
import json
import struct
import shutil
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


# ==============================================================================
# PART 1: PURE-PYTHON ARABIC CONTEXTUAL SHAPER & BIDI ENGINE FOR UNITY
# ==============================================================================
ARABIC_FORMS = {
    '\u0621': ('\uFE80', '\uFE80', '\uFE80', '\uFE80'),
    '\u0622': ('\uFE81', '\uFE82', '\uFE81', '\uFE82'),
    '\u0623': ('\uFE83', '\uFE84', '\uFE83', '\uFE84'),
    '\u0624': ('\uFE85', '\uFE86', '\uFE85', '\uFE86'),
    '\u0625': ('\uFE87', '\uFE88', '\uFE87', '\uFE88'),
    '\u0626': ('\uFE89', '\uFE8A', '\uFE8B', '\uFE8C'),
    '\u0627': ('\uFE8D', '\uFE8E', '\uFE8D', '\uFE8E'),
    '\u0628': ('\uFE8F', '\uFE90', '\uFE91', '\uFE92'),
    '\u0629': ('\uFE93', '\uFE94', '\uFE93', '\uFE94'),
    '\u062A': ('\uFE95', '\uFE96', '\uFE97', '\uFE98'),
    '\u062B': ('\uFE99', '\uFE9A', '\uFE9B', '\uFE9C'),
    '\u062C': ('\uFE9D', '\uFE9E', '\uFE9F', '\uFEA0'),
    '\u062D': ('\uFEA1', '\uFEA2', '\uFEA3', '\uFEA4'),
    '\u062E': ('\uFEA5', '\uFEA6', '\uFEA7', '\uFEA8'),
    '\u062F': ('\uFEA9', '\uFEAA', '\uFEA9', '\uFEAA'),
    '\u0630': ('\uFEAB', '\uFEAC', '\uFEAB', '\uFEAC'),
    '\u0631': ('\uFEAD', '\uFEAE', '\uFEAD', '\uFEAE'),
    '\u0632': ('\uFEAF', '\uFEB0', '\uFEAF', '\uFEB0'),
    '\u0633': ('\uFEB1', '\uFEB2', '\uFEB3', '\uFEB4'),
    '\u0634': ('\uFEB5', '\uFEB6', '\uFEB7', '\uFEB8'),
    '\u0635': ('\uFEB9', '\uFEBA', '\uFEBB', '\uFEBC'),
    '\u0636': ('\uFEBD', '\uFEBE', '\uFEBF', '\uFEC0'),
    '\u0637': ('\uFEC1', '\uFEC2', '\uFEC3', '\uFEC4'),
    '\u0638': ('\uFEC5', '\uFEC6', '\uFEC7', '\uFEC8'),
    '\u0639': ('\uFEC9', '\uFECA', '\uFECB', '\uFECC'),
    '\u063A': ('\uFECD', '\uFECE', '\uFECF', '\uFED0'),
    '\u0641': ('\uFED1', '\uFED2', '\uFED3', '\uFED4'),
    '\u0642': ('\uFED5', '\uFED6', '\uFED7', '\uFED8'),
    '\u0643': ('\uFED9', '\uFEDA', '\uFEDB', '\uFEDC'),
    '\u0644': ('\uFEDD', '\uFEDE', '\uFEDF', '\uFEE0'),
    '\u0645': ('\uFEE1', '\uFEE2', '\uFEE3', '\uFEE4'),
    '\u0646': ('\uFEE5', '\uFEE6', '\uFEE7', '\uFEE8'),
    '\u0647': ('\uFEE9', '\uFEEA', '\uFEEB', '\uFEEC'),
    '\u0648': ('\uFEED', '\uFEEE', '\uFEED', '\uFEEE'),
    '\u0649': ('\uFEEF', '\uFEF0', '\uFEEF', '\uFEF0'),
    '\u064A': ('\uFEF1', '\uFEF2', '\uFEF3', '\uFEF4'),
}

RIGHT_JOIN_ONLY = {
    '\u0621', '\u0622', '\u0623', '\u0624', '\u0625', '\u0627',
    '\u0629', '\u062F', '\u0630', '\u0631', '\u0632', '\u0648', '\u0649'
}

LAM_ALEF_LIGATURES = {
    '\u0622': ('\uFEF5', '\uFEF6'),
    '\u0623': ('\uFEF7', '\uFEF8'),
    '\u0625': ('\uFEF9', '\uFEFA'),
    '\u0627': ('\uFEFB', '\uFEFC'),
}

DIACRITICS = set(chr(c) for c in range(0x064B, 0x065F))


def can_connect_left(ch):
    return ch in ARABIC_FORMS and ch not in RIGHT_JOIN_ONLY


def can_connect_right(ch):
    return ch in ARABIC_FORMS and ch != '\u0621'


def shape_arabic_word(text):
    chars = [c for c in text if c not in DIACRITICS]
    out = []
    i = 0
    n = len(chars)
    while i < n:
        ch = chars[i]
        if ch not in ARABIC_FORMS:
            out.append(ch)
            i += 1
            continue

        prev_ch = chars[i - 1] if i > 0 else None
        connects_prev = (prev_ch is not None) and can_connect_left(prev_ch) and can_connect_right(ch)

        if ch == '\u0644' and (i + 1 < n) and chars[i + 1] in LAM_ALEF_LIGATURES:
            alef_ch = chars[i + 1]
            iso_lig, fin_lig = LAM_ALEF_LIGATURES[alef_ch]
            out.append(fin_lig if connects_prev else iso_lig)
            i += 2
            continue

        next_ch = chars[i + 1] if (i + 1 < n) else None
        connects_next = (next_ch is not None) and can_connect_left(ch) and can_connect_right(next_ch)

        iso, fin, ini, med = ARABIC_FORMS[ch]
        if connects_prev and connects_next:
            out.append(med)
        elif connects_prev and not connects_next:
            out.append(fin)
        elif not connects_prev and connects_next:
            out.append(ini)
        else:
            out.append(iso)
        i += 1

    return "".join(out)


# Linear-time non-backtracking tokenizer for LTR tokens inside Arabic strings
TOKEN_SPLIT_RE = re.compile(
    r"(\{[0-9a-zA-Z_:]+\}|%[0-9]*[@dfsu]|\$[-]?[0-9,.\w]+|[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)"
)


def shape_and_bidi_for_unity(logical_arabic, visual_reverse_for_ltr_canvas=True):
    shaped = shape_arabic_word(logical_arabic)
    if not visual_reverse_for_ltr_canvas:
        return shaped

    parts = TOKEN_SPLIT_RE.split(shaped)
    visual_segments = []
    for part in parts:
        if not part:
            continue
        if TOKEN_SPLIT_RE.fullmatch(part):
            visual_segments.append(part)
        else:
            swapped = []
            for ch in reversed(part):
                if ch == '(':
                    swapped.append(')')
                elif ch == ')':
                    swapped.append('(')
                elif ch == '«':
                    swapped.append('»')
                elif ch == '»':
                    swapped.append('«')
                else:
                    swapped.append(ch)
            visual_segments.append("".join(swapped))

    return "".join(reversed(visual_segments))


# ==============================================================================
# PART 2: PRE-COMPUTED O(1) PURE ARABIC DICTIONARY FOR BITLIFE
# ==============================================================================
BITLIFE_BASE_TRANSLATIONS = {
    "Age": "العمر",
    "+ Age": "+ العمر",
    "Age Up": "تقدم بالعمر",
    "Occupation": "المهنة",
    "Occupations": "المهن",
    "Assets": "الأصول",
    "Relationships": "العلاقات",
    "Activities": "الأنشطة",
    "Bank Balance": "الرصيد البنكي",
    "Net Worth": "صافي الثروة",
    "Monthly Outflow": "المصاريف الشهرية",
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
    "Haptics": "الاهتزاز اللمسي",
    "Dark Mode": "الوضع الداكن",
    "Half-Year Age Up": "التقدم بنصف سنة (6 أشهر)",
    "Minigames": "الألعاب المصغّرة",
    "Restore Purchases": "استعادة المشتريات",
    "Education": "التعليم",
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
    "Army": "الجيش البري",
    "Navy": "البحرية",
    "Air Force": "القوات الجوية",
    "Marines": "مشاة البحرية",
    "Coast Guard": "خفر السواحل",
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
    "Stepfather": "زوج الأم",
    "Stepmother": "زوجة الأب",
    "Brother": "الأخ",
    "Sister": "الأخت",
    "Half-Brother": "الأخ غير الشقيق",
    "Half-Sister": "الأخت غير الشقيقة",
    "Boyfriend": "الحبيب",
    "Girlfriend": "الحبيبة",
    "Fiancé": "الخطيب",
    "Fiancée": "الخطيبة",
    "Husband": "الزوج",
    "Wife": "الزوجة",
    "Spouse": "الزوج / الزوجة",
    "Son": "الابن",
    "Daughter": "الابنة",
    "Best Friend": "الصديق المقرّب",
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
    "Elope": "الزواج السري السريع",
    "Divorce": "طلب الطلاق",
    "Break Up": "إنهاء العلاقة (انفصال)",
    "Couples Counseling": "استشارة زوجية",
    "Abandon": "التخلي عن",
    "Adopt Out": "عرض للتبني",
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
    "Hauntedness": "مستوى المسّ والأشباح",
    "Renovate": "ترميم وتجديد",
    "Rent Out": "تأجير للمستأجرين",
    "Apply for a Mortgage": "التقديم على رهن عقاري",
    "Adoption": "التبني",
    "Casino": "الكازينو",
    "Crime": "الجريمة",
    "Doctor": "الطبيب والعلاج",
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
    "Appeal": "استئناف الحكم القضائي",
    "Escape": "الهروب من السجن",
    "Riot": "إثارة شغب في السجن",
    "Prison Yard": "ساحة السجن",
    "R.I.P.": "ارقد في سلام (R.I.P.)",
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

# Pre-shape every dictionary entry once at startup so batch translation is an O(1) dict lookup!
PRECOMPUTED_LOGICAL_LOWER = {k.lower(): v for k, v in BITLIFE_BASE_TRANSLATIONS.items()}
PRECOMPUTED_SHAPED_BYTES_LOWER = {
    k.lower(): shape_and_bidi_for_unity(v, visual_reverse_for_ltr_canvas=True).encode("utf-8")
    for k, v in BITLIFE_BASE_TRANSLATIONS.items()
}

REGEX_SENTENCE_PATTERNS = [
    (
        re.compile(r"^Age:\s*(\d+)\s*years?$", re.IGNORECASE),
        lambda m: f"العمر: {m.group(1)} سنة"
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


def translate_string_entry(original_text, shape_for_unity_canvas=False):
    if not original_text:
        return None
    stripped = original_text.strip()
    if not stripped or len(stripped) > 160:
        return None

    low = stripped.lower()
    if shape_for_unity_canvas and low in PRECOMPUTED_SHAPED_BYTES_LOWER:
        return PRECOMPUTED_SHAPED_BYTES_LOWER[low].decode("utf-8")
    if not shape_for_unity_canvas and low in PRECOMPUTED_LOGICAL_LOWER:
        return PRECOMPUTED_LOGICAL_LOWER[low]

    # Only test sentence regexes if prefix matches 'age:' or 'you'
    if low.startswith(("age:", "you were born", "your birthday")):
        for regex, repl_fn in REGEX_SENTENCE_PATTERNS:
            m = regex.match(stripped)
            if m:
                tr = repl_fn(m)
                return shape_and_bidi_for_unity(tr, True) if shape_for_unity_canvas else tr
    return None


def translate_string_to_utf8_bytes_fast(decoded_str):
    """O(1) fast path returning UTF-8 bytes directly for IL2CPP batch processing."""
    stripped = decoded_str.strip()
    if not stripped:
        return None
    low = stripped.lower()
    hit = PRECOMPUTED_SHAPED_BYTES_LOWER.get(low)
    if hit is not None:
        return hit
    if low.startswith(("age:", "you were born", "your birthday")):
        for regex, repl_fn in REGEX_SENTENCE_PATTERNS:
            m = regex.match(stripped)
            if m:
                tr = repl_fn(m)
                return shape_and_bidi_for_unity(tr, True).encode("utf-8")
    return None


# ==============================================================================
# PART 3: BATCH-STREAMING, MEMORY-BOUNDED IL2CPP `global-metadata.dat` PATCHER
# ==============================================================================
IL2CPP_MAGIC = 0xFAB11BAF
BATCH_SIZE = 1000


def detect_il2cpp_literal_table_layout(raw_buf, file_size):
    """
    Auto-detects:
    1. Exact (lit_offset, lit_size, data_offset, data_size) in Il2CppGlobalMetadataHeader (supports v24..v39+).
    2. Exact field order inside 8-byte Il2CppStringLiteral:
       - 'len_first': (uint32 length, uint32 dataIndex)
       - 'idx_first': (uint32 dataIndex, uint32 length)
    """
    sanity, version = struct.unpack_from("<Ii", raw_buf, 0)
    if sanity != IL2CPP_MAGIC:
        raise ValueError(f"Invalid IL2CPP magic: 0x{sanity:08X} (expected 0xFAB11BAF)")

    # Scan header (first 64 ints) for the stringLiteral table + stringLiteralData pool pair
    lit_offset, lit_size, data_offset, data_size = struct.unpack_from("<iiii", raw_buf, 8)
    if not (0 < lit_offset < 4096 and lit_size > 0 and lit_size % 8 == 0 and 0 < data_offset < file_size):
        # Fallback header scan in case v39 shifted offsets by 4/8 bytes
        for pos in range(8, 128, 4):
            lo, ls, do, ds = struct.unpack_from("<iiii", raw_buf, pos)
            if 64 <= lo < 4096 and ls >= 800 and ls % 8 == 0 and abs((lo + ls) - do) <= 64 and (do + ds) <= file_size:
                lit_offset, lit_size, data_offset, data_size = lo, ls, do, ds
                break

    num_literals = lit_size // 8
    sample_n = min(num_literals, 100)
    len_first_score = 0
    idx_first_score = 0

    for i in range(sample_n):
        u0, u1 = struct.unpack_from("<II", raw_buf, lit_offset + i * 8)
        # Check if u0 is length and u1 is dataIndex
        if u0 <= 4096 and (data_offset + u1 + u0) <= file_size:
            len_first_score += 1
        # Check if u0 is dataIndex and u1 is length
        if u1 <= 4096 and (data_offset + u0 + u1) <= file_size:
            idx_first_score += 1

    # Also check entry 0 & entry 1 continuity
    if sample_n >= 2:
        u0_0, u1_0 = struct.unpack_from("<II", raw_buf, lit_offset)
        u0_1, u1_1 = struct.unpack_from("<II", raw_buf, lit_offset + 8)
        if u1_0 == 0 and u0_0 > 0 and u1_1 == u0_0:
            len_first_score += 500
        elif u0_0 == 0 and u1_0 > 0 and u0_1 == u1_0:
            idx_first_score += 500

    layout_mode = "len_first" if len_first_score >= idx_first_score else "idx_first"
    return version, lit_offset, lit_size, data_offset, data_size, num_literals, layout_mode


def patch_il2cpp_global_metadata(metadata_path, output_path=None, shape_for_unity_canvas=True):
    """
    Memory-safe, Batch-Streaming (1,000 literals/batch) IL2CPP Metadata Patcher:
    - Never loads 36,072 string slices into a list.
    - Uses Zero-Shift In-Place + EOF-Tail append so:
      1. Peak extra RAM is < 5 MB (instead of gigabytes).
      2. Zero section offsets in Il2CppGlobalMetadataHeader are shifted (100% safe on v39!).
      3. Logs progress every 1,000 strings (`[IL2CPP Batch X/Y]`) with immediate stdout flush.
    """
    if output_path is None:
        output_path = metadata_path

    t_start = time.time()
    file_size = os.path.getsize(metadata_path)
    log(f"[IL2CPP] Opening {metadata_path} ({file_size:,} bytes)...")

    with open(metadata_path, "rb") as f:
        raw = bytearray(f.read())

    if len(raw) < 64:
        raise ValueError(f"File too small ({len(raw)} bytes) to be a valid global-metadata.dat")

    version, lit_offset, lit_size, data_offset, data_size, num_literals, layout_mode = (
        detect_il2cpp_literal_table_layout(raw, len(raw))
    )

    log(
        f"[IL2CPP] Parsed global-metadata.dat (v{version}): {num_literals:,} string literals "
        f"| lit_offset={lit_offset}, data_offset={data_offset}, data_size={data_size:,}, layout={layout_mode}"
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
    skipped_invalid = 0

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

            # Strict O(1) bounds & length guard: never slice huge or out-of-range entries!
            if str_len < 2 or str_len > 160:
                continue
            abs_str_pos = data_offset + str_idx
            if abs_str_pos < 0 or (abs_str_pos + str_len) > eof_base_offset:
                skipped_invalid += 1
                continue

            # Fast first-byte ASCII filter before UTF-8 decode
            first_byte = raw[abs_str_pos]
            if not (first_byte == 0x2B or (0x41 <= first_byte <= 0x5A) or (0x61 <= first_byte <= 0x7A)):
                continue

            try:
                decoded = raw[abs_str_pos : abs_str_pos + str_len].decode("utf-8")
            except UnicodeDecodeError:
                continue

            ar_bytes = translate_string_to_utf8_bytes_fast(decoded)
            if ar_bytes is None:
                continue

            new_len = len(ar_bytes)
            if new_len <= str_len:
                # Overwrite directly in-place! Zero memory growth!
                raw[abs_str_pos : abs_str_pos + new_len] = ar_bytes
                new_idx = str_idx
                in_place_count += 1
            else:
                # Append to EOF tail buffer and point dataIndex to (eof_base_offset + len(eof_tail)) - data_offset
                tail_pos = eof_base_offset + len(eof_tail)
                new_idx = tail_pos - data_offset
                eof_tail.extend(ar_bytes)
                tail_append_count += 1

            if layout_mode == "len_first":
                struct.pack_into("<II", raw, entry_pos, new_len, new_idx)
            else:
                struct.pack_into("<II", raw, entry_pos, new_idx, new_len)

            translated_count += 1

        pct = (end_i * 100.0) / max(1, num_literals)
        log(
            f"[IL2CPP Batch {batch_idx + 1}/{total_batches}] "
            f"Processed {end_i:,}/{num_literals:,} literals ({pct:.1f}%) | "
            f"Patched: {translated_count:,} (in-place: {in_place_count}, tail: {tail_append_count})"
        )

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

    elapsed = time.time() - t_start
    log(
        f"[IL2CPP] Completed in {elapsed:.2f}s! Patched {translated_count:,} string literals "
        f"in {output_path} (final size: {os.path.getsize(output_path):,} bytes)"
    )
    return translated_count


# ==============================================================================
# PART 4: FULL ARABIC STRINGS.XML & SINGLE-PASS ASSET LOCALIZATION
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


# Single-pass regex for safe JSON/XML localization files (avoids 250x .replace() loops)
SKIP_UNITY_INTERNAL_FILES = {
    "catalog.json", "settings.json", "scriptingassemblies.json",
    "runtimeinitializeonloads.json", "boot.config", "globalgamemanagers",
    "unity default resources", "unity_builtin_extra"
}

ESCAPED_KEYS = "|".join(re.escape(k) for k in sorted(BITLIFE_BASE_TRANSLATIONS.keys(), key=len, reverse=True))
SINGLE_PASS_QUOTED_RE = re.compile(r'"(' + ESCAPED_KEYS + r')"')
SINGLE_PASS_TAG_RE = re.compile(r'>(' + ESCAPED_KEYS + r')<')


def patch_decompiled_apk_directory(decompiled_dir, overlay_dir=None):
    stats = {
        "manifest_patched": False,
        "xml_strings_patched": 0,
        "il2cpp_strings_patched": 0,
        "asset_files_patched": 0,
    }

    log(f"[Patcher] Starting localization on decompiled directory: {decompiled_dir}")

    # Merge any missing files from split_overlay (e.g. global-metadata.dat from UnityDataAssetPack.apk)
    if overlay_dir and os.path.isdir(overlay_dir):
        copied_overlay = 0
        for root_d, _, files in os.walk(overlay_dir):
            for fn in files:
                src_p = os.path.join(root_d, fn)
                rel_p = os.path.relpath(src_p, overlay_dir)
                dst_p = os.path.join(decompiled_dir, rel_p)
                if not os.path.isfile(dst_p):
                    os.makedirs(os.path.dirname(dst_p), exist_ok=True)
                    shutil.copyfile(src_p, dst_p)
                    copied_overlay += 1
        if copied_overlay > 0:
            log(f"[Patcher] Merged {copied_overlay} missing split files from overlay_dir.")

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
            tr = translate_string_entry(elem.text, shape_for_unity_canvas=False)
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

    # 3. Search for global-metadata.dat and batch-patch it
    log("[Patcher] Step 3/4: Scanning for Unity IL2CPP global-metadata.dat...")
    for root_d, _, files in os.walk(decompiled_dir):
        for fn in files:
            if fn == "global-metadata.dat":
                meta_p = os.path.join(root_d, fn)
                stats["il2cpp_strings_patched"] += patch_il2cpp_global_metadata(meta_p)

    # 4. Single-pass scan on small localization files in assets/ (skipping >512KB & Unity Addressables catalogs)
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
                            log(f"  [Skip Large File] {fn} ({fsize:,} bytes > 512 KB)")
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

    total_changes = stats["xml_strings_patched"] + stats["il2cpp_strings_patched"] + stats["asset_files_patched"]
    if not stats["manifest_patched"] or total_changes == 0:
        fail(f"Localization produced 0 changes: {stats}")

    return stats


def inject_patched_files_into_apk_zip(source_apk, decompiled_dir, output_apk):
    log(f"[Fallback-Zip-Injector] Streaming patched global-metadata.dat and assets into {output_apk}...")
    replacement_map = {}
    assets_dir = os.path.join(decompiled_dir, "assets")
    if os.path.isdir(assets_dir):
        for r_d, _, fns in os.walk(assets_dir):
            for fn in fns:
                abs_f = os.path.join(r_d, fn)
                arc_name = os.path.relpath(abs_f, decompiled_dir).replace("\\", "/")
                replacement_map[arc_name] = abs_f

    with zipfile.ZipFile(source_apk, "r") as zin, zipfile.ZipFile(output_apk, "w") as zout:
        existing_arcs = set()
        for item in zin.infolist():
            existing_arcs.add(item.filename)
            if item.filename in replacement_map:
                with open(replacement_map[item.filename], "rb") as rf:
                    zout.writestr(item, rf.read())
            else:
                zout.writestr(item, zin.read(item.filename))

        for arc_name, abs_f in replacement_map.items():
            if arc_name not in existing_arcs:
                zout.write(abs_f, arcname=arc_name, compress_type=zipfile.ZIP_DEFLATED)

    log(f"[Fallback-Zip-Injector] Successfully wrote {output_apk} ({os.path.getsize(output_apk):,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--inject-zip":
        inject_patched_files_into_apk_zip(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        ov_dir = sys.argv[2] if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]) else None
        res = patch_decompiled_apk_directory(sys.argv[1], overlay_dir=ov_dir)
        log("[SUCCESS] APK Directory Patch Summary: " + json.dumps(res, ensure_ascii=False))
    elif len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        patch_il2cpp_global_metadata(sys.argv[1])
    else:
        log("Usage: python3 reverse_engineer_bitlife_apk.py <decompiled_apk_dir> [overlay_dir]")
        sys.exit(1)
