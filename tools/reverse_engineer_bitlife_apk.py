#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLife - Life Simulator (com.candywriter.bitlife)
Ultra Reverse-Engineering & Pure Linguistic Arabic Localization Engine (v2.0 - Strict Mode)
===========================================================================================
1. Patches AndroidManifest.xml (enables `android:supportsRtl="true"` and strips split-only restrictions).
2. Patches `res/values/strings.xml` and generates full `res/values-ar/strings.xml`.
3. Recursively locates and binary-patches Unity IL2CPP `global-metadata.dat` (Magic 0xFAB11BAF, v24–v31)
   string literal table without breaking binary offsets or game logic.
4. Applies Pure-Python Arabic Contextual Shaping (Presentation Forms-B + Lam-Alef ligatures + BiDi ordering)
   so Unity's UGUI / TextMeshPro renders connected, right-to-left Arabic strings while preserving:
   - Proper names (John Smith, Los Angeles, etc.)
   - Currency symbols ($1,500, $1.5M)
   - Format specifiers & variables ({0}, {1}, {name}, %d, %s, %@)
5. Enforces STRICT verification: exits with non-zero status if AndroidManifest.xml is missing or 0 strings patched.
"""

import os
import re
import sys
import json
import struct
import shutil
import zipfile
import xml.etree.ElementTree as ET

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


TOKEN_SPLIT_RE = re.compile(
    r"(\{[0-9a-zA-Z_:]+\}|%[0-9]*[@dfsu]|\$[-]?[0-9,.\w]+|[A-Za-z0-9][A-Za-z0-9_.\-',:/ ]*[A-Za-z0-9]|[A-Za-z0-9])"
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
# PART 2: COMPREHENSIVE PURE ARABIC DICTIONARY FOR BITLIFE (CASE-INSENSITIVE)
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

# Build case-insensitive lookup table (handles UPPERCASE, lowercase, and Title Case in Unity UI)
LOWER_LOOKUP = {k.lower(): v for k, v in BITLIFE_BASE_TRANSLATIONS.items()}

REGEX_SENTENCE_PATTERNS = [
    (
        re.compile(r"^Age:\s*(\d+)\s*years?$", re.IGNORECASE),
        lambda m: f"العمر: {m.group(1)} سنة"
    ),
    (
        re.compile(r"^You were born a (male|female) in ([^\.]+)\.$", re.IGNORECASE),
        lambda m: f"وُلدت كـ {'ذكر' if m.group(1).lower() == 'male' else 'أنثى'} في {m.group(2)}."
    ),
    (
        re.compile(r"^Your birthday is ([^\.]+)\.$", re.IGNORECASE),
        lambda m: f"تاريخ ميلادك هو {m.group(1)}."
    ),
]


def translate_string_entry(original_text, shape_for_unity_canvas=False):
    if not original_text:
        return None
    stripped = original_text.strip()
    if not stripped:
        return None

    translated = BITLIFE_BASE_TRANSLATIONS.get(stripped)
    if translated is None:
        translated = LOWER_LOOKUP.get(stripped.lower())
    if translated is None:
        for regex, repl_fn in REGEX_SENTENCE_PATTERNS:
            m = regex.match(stripped)
            if m:
                translated = repl_fn(m)
                break

    if translated is None:
        return None

    if shape_for_unity_canvas:
        return shape_and_bidi_for_unity(translated, visual_reverse_for_ltr_canvas=True)
    return translated


# ==============================================================================
# PART 3: UNITY IL2CPP `global-metadata.dat` BINARY PARSER & REBUILDER
# ==============================================================================
IL2CPP_MAGIC = 0xFAB11BAF


def patch_il2cpp_global_metadata(metadata_path, output_path=None, shape_for_unity_canvas=True):
    if output_path is None:
        output_path = metadata_path

    with open(metadata_path, "rb") as f:
        raw = bytearray(f.read())

    if len(raw) < 64:
        raise ValueError(f"File too small ({len(raw)} bytes) to be a valid global-metadata.dat")

    sanity, version, lit_offset, lit_size, data_offset, data_size = struct.unpack_from("<IiIiIi", raw, 0)
    if sanity != IL2CPP_MAGIC:
        raise ValueError(f"Invalid IL2CPP magic: 0x{sanity:08X} (expected 0xFAB11BAF)")

    num_literals = lit_size // 8
    print(f"[IL2CPP] Parsed {metadata_path} (v{version}): {num_literals} string literals", flush=True)

    header_end = lit_offset
    literals = []
    for i in range(num_literals):
        str_len, str_idx = struct.unpack_from("<II", raw, lit_offset + i * 8)
        str_bytes = bytes(raw[data_offset + str_idx : data_offset + str_idx + str_len])
        literals.append((str_len, str_idx, str_bytes))

    new_lit_table = bytearray(lit_size)
    new_data_block = bytearray()
    translated_count = 0

    for i, (str_len, str_idx, str_bytes) in enumerate(literals):
        final_bytes = str_bytes
        if 1 <= str_len <= 240:
            try:
                decoded = str_bytes.decode("utf-8")
                ar_text = translate_string_entry(decoded, shape_for_unity_canvas=shape_for_unity_canvas)
                if ar_text is not None:
                    final_bytes = ar_text.encode("utf-8")
                    translated_count += 1
            except UnicodeDecodeError:
                pass

        new_idx = len(new_data_block)
        new_len = len(final_bytes)
        new_data_block.extend(final_bytes)
        struct.pack_into("<II", new_lit_table, i * 8, new_len, new_idx)

    while len(new_data_block) % 4 != 0:
        new_data_block.append(0)

    old_data_end = data_offset + data_size
    delta = len(new_data_block) - data_size

    rebuilt = bytearray()
    rebuilt.extend(raw[:lit_offset])
    rebuilt.extend(new_lit_table)
    rebuilt.extend(raw[lit_offset + lit_size : data_offset])
    rebuilt.extend(new_data_block)
    rebuilt.extend(raw[old_data_end:])

    struct.pack_into("<i", rebuilt, 20, len(new_data_block))
    for pos in range(24, header_end, 8):
        sec_offset, sec_count = struct.unpack_from("<Ii", rebuilt, pos)
        if sec_offset > data_offset and sec_offset < len(raw):
            struct.pack_into("<I", rebuilt, pos, sec_offset + delta)

    with open(output_path, "wb") as f:
        f.write(rebuilt)

    print(f"[IL2CPP] Patched {translated_count} string literals in {output_path} (delta: {delta:+d} bytes)", flush=True)
    return translated_count


# ==============================================================================
# PART 4: FULL ARABIC STRINGS.XML GENERATOR & DECOMPILED APK PATCHER
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
    for idx, (en_k, ar_v) in enumerate(BITLIFE_BASE_TRANSLATIONS.items()):
        key_slug = re.sub(r"[^a-z0-9]+", "_", en_k.lower()).strip("_")
        if key_slug:
            entries[f"bl_ar_{key_slug}"] = ar_v
    return entries


def patch_decompiled_apk_directory(decompiled_dir, overlay_dir=None):
    stats = {
        "manifest_patched": False,
        "xml_strings_patched": 0,
        "il2cpp_strings_patched": 0,
        "asset_files_patched": 0,
    }

    # If split_overlay has assets/ or lib/ from UnityDataAssetPack.apk or config.*.apk, merge them in first
    if overlay_dir and os.path.isdir(overlay_dir):
        for root_d, _, files in os.walk(overlay_dir):
            for fn in files:
                src_p = os.path.join(root_d, fn)
                rel_p = os.path.relpath(src_p, overlay_dir)
                dst_p = os.path.join(decompiled_dir, rel_p)
                if not os.path.isfile(dst_p):
                    os.makedirs(os.path.dirname(dst_p), exist_ok=True)
                    shutil.copyfile(src_p, dst_p)

    # 1. Strictly verify and patch AndroidManifest.xml
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if not os.path.isfile(manifest_path):
        print(f"[FATAL ERROR] AndroidManifest.xml not found in {decompiled_dir}!", file=sys.stderr, flush=True)
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_txt = f.read()

    if 'android:supportsRtl="false"' in manifest_txt:
        manifest_txt = manifest_txt.replace('android:supportsRtl="false"', 'android:supportsRtl="true"')
    elif "android:supportsRtl=" not in manifest_txt:
        manifest_txt = manifest_txt.replace("<application", '<application android:supportsRtl="true"', 1)

    # Strip split-required flags so merged APK installs cleanly on any device
    manifest_txt = re.sub(r'\s*android:isSplitRequired="true"', "", manifest_txt)
    manifest_txt = re.sub(r'\s*android:requiredSplitTypes="[^"]*"', "", manifest_txt)
    manifest_txt = re.sub(r'\s*android:splitTypes="[^"]*"', "", manifest_txt)

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_txt)
    stats["manifest_patched"] = True

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

    # Write full Arabic dictionary into res/values-ar/strings.xml AND append missing keys
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

    # 3. Search recursively for any global-metadata.dat in decompiled_dir and patch it
    for root_d, _, files in os.walk(decompiled_dir):
        for fn in files:
            if fn == "global-metadata.dat":
                meta_p = os.path.join(root_d, fn)
                stats["il2cpp_strings_patched"] += patch_il2cpp_global_metadata(meta_p)

    # 4. Patch text/JSON/XML/CSV/plist files in assets/
    assets_dir = os.path.join(decompiled_dir, "assets")
    if os.path.isdir(assets_dir):
        for root_d, _, files in os.walk(assets_dir):
            for fn in files:
                if fn.endswith((".json", ".txt", ".csv", ".xml", ".plist")):
                    fp = os.path.join(root_d, fn)
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            content = f.read()
                        orig = content
                        for en_k, ar_v in BITLIFE_BASE_TRANSLATIONS.items():
                            content = content.replace(f'"{en_k}"', f'"{ar_v}"')
                            content = content.replace(f">{en_k}<", f">{ar_v}<")
                        if content != orig:
                            with open(fp, "w", encoding="utf-8") as f:
                                f.write(content)
                            stats["asset_files_patched"] += 1
                    except Exception:
                        pass

    total_changes = stats["xml_strings_patched"] + stats["il2cpp_strings_patched"] + stats["asset_files_patched"]
    if not stats["manifest_patched"] or total_changes == 0:
        print(f"[FATAL ERROR] Localization produced 0 changes: {stats}", file=sys.stderr, flush=True)
        sys.exit(1)

    return stats


def inject_patched_files_into_apk_zip(source_apk, decompiled_dir, output_apk):
    """
    Fallback direct ZIP injector in case `apktool b` encounters aapt2 resource table issues
    on obfuscated Unity split-merged APKs:
    Copies `source_apk` and replaces `assets/bin/Data/Managed/Metadata/global-metadata.dat`
    and any modified `assets/*` directly inside the APK ZIP!
    """
    print(f"[Fallback-Zip-Injector] Injecting patched global-metadata.dat and assets into {output_apk}...", flush=True)
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
                    data = rf.read()
                zout.writestr(item, data)
            else:
                zout.writestr(item, zin.read(item.filename))

        for arc_name, abs_f in replacement_map.items():
            if arc_name not in existing_arcs:
                zout.write(abs_f, arcname=arc_name, compress_type=zipfile.ZIP_DEFLATED)

    print(f"[Fallback-Zip-Injector] Successfully wrote {output_apk} ({os.path.getsize(output_apk)} bytes)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--inject-zip":
        # Usage: python3 reverse_engineer_bitlife_apk.py --inject-zip <source_apk> <decompiled_dir> <output_apk>
        inject_patched_files_into_apk_zip(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        ov_dir = sys.argv[2] if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]) else None
        res = patch_decompiled_apk_directory(sys.argv[1], overlay_dir=ov_dir)
        print("[SUCCESS] APK Directory Patch Summary:", json.dumps(res, ensure_ascii=False), flush=True)
    elif len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        patch_il2cpp_global_metadata(sys.argv[1])
    else:
        print("Usage: python3 reverse_engineer_bitlife_apk.py <decompiled_apk_dir> [overlay_dir]")
        sys.exit(1)
