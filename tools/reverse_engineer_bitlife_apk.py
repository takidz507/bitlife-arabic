#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLife - Life Simulator (com.candywriter.bitlife)
Ultra Reverse-Engineering & Pure Linguistic Arabic Localization Engine
=====================================================================
1. Decompiles & patches Android resources (AndroidManifest.xml, res/values/strings.xml, res/values-ar/strings.xml).
2. Parses & patches Unity IL2CPP `global-metadata.dat` (Magic 0xFAB11BAF, v24–v31) string literal table
   without breaking binary offsets or game logic.
3. Applies Pure-Python Arabic Contextual Shaping (Presentation Forms-B + Lam-Alef ligatures + BiDi ordering)
   so Unity's UGUI / TextMeshPro renders connected, right-to-left Arabic strings while preserving:
   - Proper names (John Smith, Los Angeles, etc.)
   - Currency symbols ($1,500, $1.5M)
   - Format specifiers & variables ({0}, {1}, {name}, %d, %s, %@)
"""

import os
import re
import sys
import json
import struct
import xml.etree.ElementTree as ET

# ==============================================================================
# PART 1: PURE-PYTHON ARABIC CONTEXTUAL SHAPER & BIDI ENGINE FOR UNITY
# ==============================================================================
ARABIC_FORMS = {
    '\u0621': ('\uFE80', '\uFE80', '\uFE80', '\uFE80'),  # ء
    '\u0622': ('\uFE81', '\uFE82', '\uFE81', '\uFE82'),  # آ
    '\u0623': ('\uFE83', '\uFE84', '\uFE83', '\uFE84'),  # أ
    '\u0624': ('\uFE85', '\uFE86', '\uFE85', '\uFE86'),  # ؤ
    '\u0625': ('\uFE87', '\uFE88', '\uFE87', '\uFE88'),  # إ
    '\u0626': ('\uFE89', '\uFE8A', '\uFE8B', '\uFE8C'),  # ئ
    '\u0627': ('\uFE8D', '\uFE8E', '\uFE8D', '\uFE8E'),  # ا
    '\u0628': ('\uFE8F', '\uFE90', '\uFE91', '\uFE92'),  # ب
    '\u0629': ('\uFE93', '\uFE94', '\uFE93', '\uFE94'),  # ة
    '\u062A': ('\uFE95', '\uFE96', '\uFE97', '\uFE98'),  # ت
    '\u062B': ('\uFE99', '\uFE9A', '\uFE9B', '\uFE9C'),  # ث
    '\u062C': ('\uFE9D', '\uFE9E', '\uFE9F', '\uFEA0'),  # ج
    '\u062D': ('\uFEA1', '\uFEA2', '\uFEA3', '\uFEA4'),  # ح
    '\u062E': ('\uFEA5', '\uFEA6', '\uFEA7', '\uFEA8'),  # خ
    '\u062F': ('\uFEA9', '\uFEAA', '\uFEA9', '\uFEAA'),  # د
    '\u0630': ('\uFEAB', '\uFEAC', '\uFEAB', '\uFEAC'),  # ذ
    '\u0631': ('\uFEAD', '\uFEAE', '\uFEAD', '\uFEAE'),  # ر
    '\u0632': ('\uFEAF', '\uFEB0', '\uFEAF', '\uFEB0'),  # ز
    '\u0633': ('\uFEB1', '\uFEB2', '\uFEB3', '\uFEB4'),  # س
    '\u0634': ('\uFEB5', '\uFEB6', '\uFEB7', '\uFEB8'),  # ش
    '\u0635': ('\uFEB9', '\uFEBA', '\uFEBB', '\uFEBC'),  # ص
    '\u0636': ('\uFEBD', '\uFEBE', '\uFEBF', '\uFEC0'),  # ض
    '\u0637': ('\uFEC1', '\uFEC2', '\uFEC3', '\uFEC4'),  # ط
    '\u0638': ('\uFEC5', '\uFEC6', '\uFEC7', '\uFEC8'),  # ظ
    '\u0639': ('\uFEC9', '\uFECA', '\uFECB', '\uFECC'),  # ع
    '\u063A': ('\uFECD', '\uFECE', '\uFECF', '\uFED0'),  # غ
    '\u0641': ('\uFED1', '\uFED2', '\uFED3', '\uFED4'),  # ف
    '\u0642': ('\uFED5', '\uFED6', '\uFED7', '\uFED8'),  # ق
    '\u0643': ('\uFED9', '\uFEDA', '\uFEDB', '\uFEDC'),  # ك
    '\u0644': ('\uFEDD', '\uFEDE', '\uFEDF', '\uFEE0'),  # ل
    '\u0645': ('\uFEE1', '\uFEE2', '\uFEE3', '\uFEE4'),  # م
    '\u0646': ('\uFEE5', '\uFEE6', '\uFEE7', '\uFEE8'),  # ن
    '\u0647': ('\uFEE9', '\uFEEA', '\uFEEB', '\uFEEC'),  # ه
    '\u0648': ('\uFEED', '\uFEEE', '\uFEED', '\uFEEE'),  # و
    '\u0649': ('\uFEEF', '\uFEF0', '\uFEEF', '\uFEF0'),  # ى
    '\u064A': ('\uFEF1', '\uFEF2', '\uFEF3', '\uFEF4'),  # ي
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


TOKEN_SPLIT_RE = re.compile(r"(\{[0-9a-zA-Z_:]+\}|%[0-9]*[@dfsu]|\$[-]?[0-9,.\w]+|[A-Za-z0-9][A-Za-z0-9_.\-',:/ ]*[A-Za-z0-9]|[A-Za-z0-9])")


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
# PART 2: COMPREHENSIVE PURE ARABIC DICTIONARY FOR BITLIFE (EXACT MATCHING)
# ==============================================================================
BITLIFE_EXACT_TRANSLATIONS = {
    "Age": "العمر",
    "+ Age": "+ العمر",
    "Occupation": "المهنة",
    "Occupations": "المهن",
    "Assets": "الأصول",
    "Relationships": "العلاقات",
    "Activities": "الأنشطة",
    "Bank Balance": "الرصيد البنكي",
    "Net Worth": "صافي الثروة",
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
    "Boyfriend": "الحبيب (Boyfriend)",
    "Girlfriend": "الحبيبة (Girlfriend)",
    "Fiancé": "الخطيب",
    "Fiancée": "الخطيبة",
    "Husband": "الزوج",
    "Wife": "الزوجة",
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

REGEX_SENTENCE_PATTERNS = [
    (
        re.compile(r"^Age:\s*(\d+)\s*years?$"),
        lambda m: f"العمر: {m.group(1)} سنة"
    ),
    (
        re.compile(r"^You were born a (male|female) in ([^\.]+)\.$"),
        lambda m: f"وُلدت كـ {'ذكر' if m.group(1) == 'male' else 'أنثى'} في {m.group(2)}."
    ),
    (
        re.compile(r"^Your birthday is ([^\.]+)\.$"),
        lambda m: f"تاريخ ميلادك هو {m.group(1)}."
    ),
]


def translate_string_entry(original_text, shape_for_unity_canvas=False):
    if not original_text:
        return None
    stripped = original_text.strip()
    translated = None

    if stripped in BITLIFE_EXACT_TRANSLATIONS:
        translated = BITLIFE_EXACT_TRANSLATIONS[stripped]
    else:
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


IL2CPP_MAGIC = 0xFAB11BAF


def patch_il2cpp_global_metadata(metadata_path, output_path=None, shape_for_unity_canvas=True):
    if output_path is None:
        output_path = metadata_path

    with open(metadata_path, "rb") as f:
        raw = bytearray(f.read())

    if len(raw) < 64:
        raise ValueError("File too small to be a valid global-metadata.dat")

    sanity, version, lit_offset, lit_size, data_offset, data_size = struct.unpack_from("<IiIiIi", raw, 0)
    if sanity != IL2CPP_MAGIC:
        raise ValueError(f"Invalid IL2CPP magic: 0x{sanity:08X} (expected 0xFAB11BAF)")

    num_literals = lit_size // 8
    print(f"[IL2CPP] Parsed global-metadata.dat (v{version}): {num_literals} string literals")

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

    print(f"[IL2CPP] Patched {translated_count} string literals in {output_path} (delta: {delta:+d} bytes)")
    return translated_count


def patch_decompiled_apk_directory(decompiled_dir):
    stats = {
        "manifest_patched": False,
        "xml_strings_patched": 0,
        "il2cpp_strings_patched": 0,
        "asset_files_patched": 0,
    }

    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_txt = f.read()
        if 'android:supportsRtl="false"' in manifest_txt:
            manifest_txt = manifest_txt.replace('android:supportsRtl="false"', 'android:supportsRtl="true"')
        elif "android:supportsRtl=" not in manifest_txt:
            manifest_txt = manifest_txt.replace("<application ", '<application android:supportsRtl="true" ', 1)
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest_txt)
        stats["manifest_patched"] = True

    values_dir = os.path.join(decompiled_dir, "res", "values")
    values_ar_dir = os.path.join(decompiled_dir, "res", "values-ar")
    os.makedirs(values_ar_dir, exist_ok=True)

    strings_xml_path = os.path.join(values_dir, "strings.xml")
    if os.path.isfile(strings_xml_path):
        tree = ET.parse(strings_xml_path)
        root = tree.getroot()
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
        tree.write(strings_xml_path, encoding="utf-8", xml_declaration=True)
        tree.write(os.path.join(values_ar_dir, "strings.xml"), encoding="utf-8", xml_declaration=True)

    metadata_path = os.path.join(
        decompiled_dir, "assets", "bin", "Data", "Managed", "Metadata", "global-metadata.dat"
    )
    if os.path.isfile(metadata_path):
        stats["il2cpp_strings_patched"] = patch_il2cpp_global_metadata(metadata_path)

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
                        for en_k, ar_v in BITLIFE_EXACT_TRANSLATIONS.items():
                            content = content.replace(f'"{en_k}"', f'"{ar_v}"')
                            content = content.replace(f">{en_k}<", f">{ar_v}<")
                        if content != orig:
                            with open(fp, "w", encoding="utf-8") as f:
                                f.write(content)
                            stats["asset_files_patched"] += 1
                    except Exception:
                        pass

    return stats


if __name__ == "__main__":
    if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        res = patch_decompiled_apk_directory(sys.argv[1])
        print("[SUCCESS] APK Directory Patch Summary:", json.dumps(res, ensure_ascii=False))
    elif len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        patch_il2cpp_global_metadata(sys.argv[1])
    else:
        print("Usage: python3 reverse_engineer_bitlife_apk.py <decompiled_apk_dir | global-metadata.dat>")
