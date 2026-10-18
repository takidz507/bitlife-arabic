package com.candywriter.bitlife.engine;

import com.candywriter.bitlife.models.AssetItem;
import com.candywriter.bitlife.models.CharacterState;
import com.candywriter.bitlife.models.EventScenario;
import com.candywriter.bitlife.models.JobItem;
import com.candywriter.bitlife.models.NpcPerson;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;

/**
 * Pure Arabic BitLife Simulation Engine (v5.0 Standalone Native 64-Bit Edition).
 * Strictly preserves all original Western names, countries, cities, and USD ($) currency values,
 * while integrating the expanded v5.0 Arabic vocabulary (1,671 terms + 44 sentence patterns).
 */
public class BitLifeSimulationEngine {
    private final Random random = new Random();

    private static final String[] MALE_FIRST_NAMES = {
            "John", "Michael", "Brandon", "Liam", "Noah", "Ethan", "Mason", "Lucas", "Oliver", "Jake", "Ryan", "Tyler", "Alexander", "Daniel"
    };
    private static final String[] FEMALE_FIRST_NAMES = {
            "Emily", "Sophia", "Olivia", "Emma", "Ava", "Chloe", "Madison", "Jessica", "Ashley", "Hannah", "Sarah", "Mia", "abella", "Charlotte"
    };
    private static final String[] LAST_NAMES = {
            "Smith", "Johnson", "Williams", "Miller", "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Martinez", "Clark", "Vance", "Sterling"
    };

    private static final String[][] COUNTRIES_AND_CITIES = {
            {"🇺🇸", "United States", "Los Angeles"},
            {"🇺🇸", "United States", "New York"},
            {"🇺🇸", "United States", "Miami"},
            {"🇬🇧", "United Kingdom", "London"},
            {"🇬🇧", "United Kingdom", "Manchester"},
            {"🇨🇦", "Canada", "Toronto"},
            {"🇨🇦", "Canada", "Vancouver"},
            {"🇦🇺", "Australia", "Sydney"},
            {"🇫🇷", "France", "Paris"},
            {"🇩🇪", "Germany", "Berlin"},
            {"🇯🇵", "Japan", "Tokyo"},
            {"🇧🇷", "Brazil", "Rio de Janeiro"},
            {"🇪🇸", "Spain", "Madrid"},
            {"🇮🇹", "Italy", "Rome"},
            {"🇨🇭", "Switzerland", "Zurich"}
    };

    private static final String[] OCCUPATIONS_PARENTS = {
            "محاسب (Accountant)", "معلم مدرسة (School Teacher)", "مهندس برمجيات (Software Engineer)",
            "طبيب أسنان (Dentist)", "مهندس معماري (Architect)", "المستشار المالي (Financial Advisor)",
            "ممرض قانوني (Registered Nurse)", "ضابط شرطة (Police Officer)", "طيّار خطوط جوية (Airline Pilot)",
            "محامٍ (Lawyer)", "جرّاح قلب (Heart Surgeon)", "عالِم بيانات (Data Scientist)"
    };

    private static final String[] HEIRLOOM_POOL = {
            "ساعة جيب جدك العتيقة (Grandfather's Pocket Watch) — القيمة: $450",
            "خاتم ألماس عائلي نادر (Family Diamond Ring) — القيمة: $14,500",
            "الكأس المقدسة الأسطورية (The Holy Grail) — القيمة: $1,250,000,000",
            "لوحة فنية أصلية لـ Banksy — القيمة: $850,000",
            "عملة تذكارية من سفينة Titanic — القيمة: $22,000",
            "ميكروفون قديم لـ Freddie Mercury — القيمة: $65,000",
            "تاج ملكي مرصع بالجواهر (Royal Crown) — القيمة: $4,200,000",
            "درع تاريخي نادر (Antique Armor) — القيمة: $180,000"
    };

    public CharacterState createNewRandomLife(String customFirst, String customLast, String customGender, int countryIdx) {
        CharacterState state = new CharacterState();
        boolean isMale = (customGender != null) ? "ذكر".equals(customGender) : random.nextBoolean();
        state.genderArabic = isMale ? "ذكر" : "أنثى";

        String[] loc = COUNTRIES_AND_CITIES[
                (countryIdx >= 0 && countryIdx < COUNTRIES_AND_CITIES.length)
                        ? countryIdx
                        : random.nextInt(COUNTRIES_AND_CITIES.length)
        ];
        state.countryFlag = loc[0];
        state.countryName = loc[1];
        state.cityName = loc[2];

        state.firstName = (customFirst != null && !customFirst.trim().isEmpty())
                ? customFirst.trim()
                : (isMale ? MALE_FIRST_NAMES[random.nextInt(MALE_FIRST_NAMES.length)] : FEMALE_FIRST_NAMES[random.nextInt(FEMALE_FIRST_NAMES.length)]).trim();
        state.lastName = (customLast != null && !customLast.trim().isEmpty())
                ? customLast.trim()
                : LAST_NAMES[random.nextInt(LAST_NAMES.length)];

        state.age = 0;
        state.bankBalance = 0L;
        state.occupationTitleArabic = "رضيع";
        state.happiness = 75 + random.nextInt(25);
        state.health = 80 + random.nextInt(20);
        state.smarts = 45 + random.nextInt(55);
        state.looks = 45 + random.nextInt(55);
        state.karma = 50 + random.nextInt(40);

        // Generate Parents
        String fatherFirst = MALE_FIRST_NAMES[random.nextInt(MALE_FIRST_NAMES.length)].trim();
        String motherFirst = FEMALE_FIRST_NAMES[random.nextInt(FEMALE_FIRST_NAMES.length)].trim();
        int fatherAge = 22 + random.nextInt(18);
        int motherAge = 21 + random.nextInt(15);
        String fatherJob = OCCUPATIONS_PARENTS[random.nextInt(OCCUPATIONS_PARENTS.length)];
        String motherJob = OCCUPATIONS_PARENTS[random.nextInt(OCCUPATIONS_PARENTS.length)];

        state.relationships.add(new NpcPerson(
                UUID.randomUUID().toString(),
                fatherFirst + " " + state.lastName,
                "الأب (Father)",
                fatherJob,
                fatherAge,
                80 + random.nextInt(20)
        ));
        state.relationships.add(new NpcPerson(
                UUID.randomUUID().toString(),
                motherFirst + " " + state.lastName,
                "الأم (Mother)",
                motherJob,
                motherAge,
                82 + random.nextInt(18)
        ));

        // Optional Sibling
        if (random.nextBoolean()) {
            boolean bro = random.nextBoolean();
            String sibName = (bro ? MALE_FIRST_NAMES[random.nextInt(MALE_FIRST_NAMES.length)] : FEMALE_FIRST_NAMES[random.nextInt(FEMALE_FIRST_NAMES.length)]).trim() + " " + state.lastName;
            state.relationships.add(new NpcPerson(
                    UUID.randomUUID().toString(),
                    sibName,
                    bro ? "الأخ (Brother)" : "الأخت (Sister)",
                    "طالب مدرسة",
                    2 + random.nextInt(5),
                    65 + random.nextInt(30)
            ));
        }

        // Birth Log
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "وُلدت كـ " + state.genderArabic + " في " + state.cityName + ", " + state.countryName + ". اسمك هو " + state.getFullName() + "."
        ));
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "والدك هو " + fatherFirst + " " + state.lastName + " (العمر: " + fatherAge + " سنة، يعمل كـ " + fatherJob + ") ووالدتك هي " + motherFirst + " " + state.lastName + " (العمر: " + motherAge + " سنة، تعمل كـ " + motherJob + ")."
        ));
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "تاريخ ميلادك هو " + state.birthMonthDay + ". برجك الفلكي هو " + state.zodiacArabic + "."
        ));

        return state;
    }

    public EventScenario ageUpOneYear(CharacterState state) {
        if (!state.isAlive) return null;

        state.age++;
        state.lifeLogs.add(new CharacterState.LifeYearLog(state.age));

        // Age all NPCs & check elderly mortality
        for (NpcPerson npc : state.relationships) {
            if (npc.isAlive) {
                npc.age++;
                if (npc.age > 78 && random.nextInt(100) < 18) {
                    npc.isAlive = false;
                    long inheritance = (npc.roleArabic.contains("الأب") || npc.roleArabic.contains("الأم"))
                            ? (25000L + random.nextInt(120000))
                            : 0L;
                    if (inheritance > 0) {
                        state.bankBalance += inheritance;
                        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "توفي " + npc.roleArabic + " " + npc.fullName + " عن عمر يناهز " + npc.age + " سنة، وترك لك ميراثاً (Inheritance) قدره " + BitLifeArabicRTLFormatter.formatCurrency(inheritance) + "."
                        ));
                    } else {
                        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "توفي " + npc.roleArabic + " " + npc.fullName + " عن عمر يناهز " + npc.age + " سنة."
                        ));
                    }
                    state.happiness -= 15;
                }
            }
        }

        // Prison countdown
        if (state.inPrison) {
            state.prisonYearsLeft--;
            if (state.prisonYearsLeft <= 0) {
                state.inPrison = false;
                state.occupationTitleArabic = "عاطل عن العمل";
                state.addLogEvent("تم الإفراج عنك من السجن بعد انتهاء الحكم القضائي! أنت حر طليق الآن.");
            } else {
                state.addLogEvent("قضيت عاماً آخر في السجن. السنوات المتبقية: " + state.prisonYearsLeft + ".");
                state.happiness -= 6;
                state.health -= 3;
            }
        }

        // School Milestones
        if (!state.inPrison) {
            if (state.age == 6) {
                state.occupationTitleArabic = "طالب في المدرسة الابتدائية";
                state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                        "بدأت الدراسة في المدرسة الابتدائية في " + state.cityName + "."
                ));
            } else if (state.age == 11) {
                state.occupationTitleArabic = "طالب في المدرسة الإعدادية";
                state.addLogEvent("بدأت الدراسة في المدرسة الإعدادية (Middle School).");
            } else if (state.age == 14) {
                state.occupationTitleArabic = "طالب في المدرسة الثانوية";
                state.addLogEvent("بدأت الدراسة في المدرسة الثانوية (High School).");
            } else if (state.age == 18 && "طالب في المدرسة الثانوية".equals(state.occupationTitleArabic)) {
                state.graduatedHighSchool = true;
                state.occupationTitleArabic = "خريج ثانوية (عاطل عن العمل)";
                state.addLogEvent("تخرجت من المدرسة الثانوية! يمكنك الآن التقديم على الجامعة أو البحث عن وظيفة بدوام كامل.");
            } else if (state.inUniversity && state.age == 22) {
                state.inUniversity = false;
                state.graduatedUniversity = true;
                state.occupationTitleArabic = "خريج جامعي (" + state.universityMajorArabic + ")";
                state.smarts += 12;
                state.addLogEvent("تخرجت من الجامعة وحصلت على الشهادة الجامعية في " + state.universityMajorArabic + "!");
            }
        }

        // Yearly Salary & Rental Income
        if (!state.inPrison && state.annualSalary > 0) {
            long netIncome = Math.round(state.annualSalary * 0.76);
            state.bankBalance += netIncome;
            state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                    "تقاضيت صافي راتبك السنوي البالغ " + BitLifeArabicRTLFormatter.formatCurrency(netIncome) + " بعد الضرائب من عملك كـ " + state.occupationTitleArabic + "."
            ));
        }

        long totalRentCollected = 0L;
        for (AssetItem asset : state.assets) {
            asset.currentValue = Math.round(asset.currentValue * 1.04);
            if (asset.isRentedOut) {
                totalRentCollected += (asset.monthlyRent * 12L);
            }
        }
        if (totalRentCollected > 0) {
            state.bankBalance += totalRentCollected;
            state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                    "حصّلت إيجارات عقارية سنوية بقيمة " + BitLifeArabicRTLFormatter.formatCurrency(totalRentCollected) + " من المستأجرين."
            ));
        }

        // Natural Mortality Check
        if (state.age >= 88 && random.nextInt(100) < 28) {
            triggerDeath(state, "أسباب طبيعية أثناء النوم (Died in Sleep)");
            return null;
        }
        if (state.health <= 0) {
            triggerDeath(state, "نوبة قلبية حادة (Massive Heart Attack)");
            return null;
        }

        state.clampStats();
        return generateAgeAppropriateScenario(state);
    }

    public void triggerDeath(CharacterState state, String causeArabic) {
        state.isAlive = false;
        state.causeOfDeathArabic = causeArabic;
        state.occupationTitleArabic = "متوفى (R.I.P.)";
        state.earnedRibbonArabic = evaluateRibbon(state);
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "☠️ ارقد في سلام (R.I.P.): توفيت عن عمر يناهز " + state.age + " سنة. سبب الوفاة: " + causeArabic + "."
        ));
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "🏅 الوسام الممنوح على شاهد القبر: " + state.earnedRibbonArabic + " | صافي الثروة: " + BitLifeArabicRTLFormatter.formatCurrency(state.calculateNetWorth()) + "."
        ));
    }

    public String evaluateRibbon(CharacterState state) {
        long netWorth = state.calculateNetWorth();
        if (netWorth >= 5_000_000L) return "ثري فاحش (Loaded)";
        if (state.prisonEscapes >= 1) return "هوديني - سيّد الهروب (Houdini)";
        if (state.crimesCommitted >= 3) return "نزيل سجون معتاد (Jailbird)";
        if (state.fame >= 70) return "مشهور (Famous)";
        if (state.countriesEmigrated >= 2) return "رحّالة عالمي (Globetrotter)";
        if (state.graduatedUniversity && state.smarts >= 85) return "أكاديمي (Academic)";
        if (state.karma >= 85) return "ربّ عائلة مثالي (Family Guy)";
        return "مواطن عادي (Mediocre)";
    }

    private EventScenario generateAgeAppropriateScenario(CharacterState state) {
        if (state.age <= 5) {
            return new EventScenario(
                    "موعد اللقاح في العيادة",
                    "أخذتك والدتك إلى عيادة الطبيب في " + state.cityName + " لتلقي اللقاح السنوي للأطفال.",
                    "الجلوس بهدوء كالأبطال",
                    "ابتسم الطبيب وأعطاك حلوى مجانية بعد الحقنة!", +6, +8, +2, 0, +4, 0,
                    "الصراخ والبكاء بصوت عالٍ",
                    "ملأ صراخك العيادة بأكملها، لكنك تلقيت اللقاح في النهاية.", -2, +6, 0, 0, 0, 0,
                    "عضّ يد الطبيب والهرب",
                    "صرخ الطبيب من الألم ووبّختك والدتك بشدة في طريق العودة!", +4, 0, 0, 0, -8, 0
            );
        } else if (state.age <= 17) {
            int pick = random.nextInt(4);
            if (pick == 0) {
                return new EventScenario(
                        "زميل متنمّر في المدرسة!",
                        "قام زميلك Brandon Miller بدفعك نحو الخزائن في الممر وسخر من حذائك أمام الجميع!",
                        "إبلاغ مدير المدرسة",
                        "عاقب مدير المدرسة Brandon Miller بالاحتجاز وأشاد بانضباطك.", +4, 0, +3, 0, +5, 0,
                        "الرد عليه بإهانة ساخرة",
                        "ضحك جميع زملاء الصف على ردك الذكي وانصرف المتنمّر خجلاً!", +10, 0, +4, +2, 0, 0,
                        "تجاهل الأمر والمضي قدماً",
                        "تجنبت المشاكل وواصلت يومك الدراسي بهدوء.", +2, 0, +2, 0, +3, 0
                );
            } else if (pick == 1) {
                return new EventScenario(
                        "الأندية المدرسية والأنشطة اللاصفية",
                        "أعلنت إدارة المدرسة عن فتح باب الانضمام إلى الأندية المدرسية والفرق الرياضية لهذا العام.",
                        "الانضمام إلى نادي البرمجة والروبوتات",
                        "طورت مهاراتك التقنية وفزت بالمركز الأول في مسابقة العلوم!", +8, 0, +10, 0, +4, 0,
                        "الانضمام إلى فريق كرة القدم",
                        "تألقت في المباريات المدرسية وارتفعت لياقتك البدنية وشعبيتك!", +10, +8, 0, +6, +2, 0,
                        "الانضمام إلى نادي المسرح والتمثيل",
                        "أديت دور البطولة في المسرحية المدرسية وسط تصفيق الجميع!", +9, 0, +4, +5, +3, 0
                );
            } else if (pick == 2) {
                return new EventScenario(
                        "اختبار مفاجئ في الرياضيات",
                        "أعلن المعلم فجأة عن اختبار صعب في مادة الرياضيات دون إشعار مسبق!",
                        "الاعتماد على مجهودك والتركيز",
                        "أجبت عن معظم الأسئلة بنجاح وحصلت على علامة ممتازة في الدرجات الدراسية!", +6, 0, +7, 0, +4, 0,
                        "محاولة الغش من ورقة زميل دراسة",
                        "لم ينتبه المعلم وحصلت على درجة عالية، لكن ضميرك أنبك قليلاً.", +5, 0, +2, 0, -6, 0,
                        "تخمين الإجابات عشوائياً",
                        "حصلت على درجة متوسطة ولكنك أنهيت الورقة في خمس دقائق!", 0, 0, -3, 0, 0, 0
                );
            } else {
                return new EventScenario(
                        "اختبار رخصة القيادة",
                        "بلغت السن القانوني للتقدم لاختبار القيادة (Driving Test) والحصول على رخصة القيادة!",
                        "المذاكرة الجيدة والقيادة بحذر",
                        "تهانينا! اجتزت اختبار القيادة وحصلت على رخصة القيادة الرسمية وأهداك والداك $500!", +12, 0, +5, 0, +4, 500L,
                        "القيادة بسرعة مفرطة أثناء الفحص",
                        "شعر الفاحص بالذعر ورسبت في اختبار القيادة لهذا العام!", -6, 0, -2, 0, -2, 0L,
                        "تأجيل الاختبار للعام القادم",
                        "قررت التريث والتدرب أكثر قبل التقدم للاختبار.", +2, 0, +1, 0, 0, 0L
                );
            }
        } else {
            int pick = random.nextInt(4);
            if (pick == 0) {
                return new EventScenario(
                        "محفظة مفقودة في الشارع!",
                        "أثناء مشيك في وسط مدينة " + state.cityName + "، عثرت على محفظة جلدية فاخرة بداخلها $2,500 وبطاقة هوية باسم Richard Vance.",
                        "إعادة المحفظة كاملة إلى صاحبها",
                        "شكرَك Richard Vance بحرارة وكافأك بمبلغ $500 تقديراً لأمانتك!", +10, 0, +2, 0, +15, 500L,
                        "الاحتفاظ بمبلغ $2,500 لنفسك",
                        "وضعت النقود في جيبك وغادرت المكان بسرعة دون أن يراك أحد.", +8, 0, 0, 0, -18, 2500L,
                        "تسليم المحفظة إلى مركز الشرطة",
                        "سجل ضابط الشرطة اسمك في لوحة الشرف للمواطنين الصالحين.", +6, 0, +2, 0, +12, 0L
                );
            } else if (pick == 1) {
                return new EventScenario(
                        "تحديات وأخلاقيات العمل",
                        "أخبرك زميلك أن المدير التنفيذي (CEO) يبحث عن صاحب أفضل خطة لتطوير الشركة هذا العام.",
                        "تقديم دراسة شاملة ومبتكرة",
                        "أبهرت خطتك مجلس الإدارة وحصلت على مكافأة إضافية قدرها $4,500!", +12, 0, +7, 0, +6, 4500L,
                        "التعاون مع زملاء العمل في مشروع مشترك",
                        "نجح الفريق في إنجاز المهمة وحصل كل فرد على مكافأة قدرها $1,500!", +8, 0, +4, 0, +8, 1500L,
                        "الالتزام بساعات العمل الرسمية فقط",
                        "حافظت على توازنك النفسي ومرّ العام الوظيفي بهدوء.", +3, +3, 0, 0, 0, 0L
                );
            } else if (pick == 2) {
                return new EventScenario(
                        "فرصة في سوق الأسهم والعملات الرقمية",
                        "أشارت الصحيفة الاقتصادية إلى صعود قوي مرتقب في أسهم شركات التقنية الحيوية والعملات الرقمية المشفرة.",
                        "استثمار $5,000 في المحفظة الاستثمارية",
                        "قفزت قيمة السهم وحققت عائداً استثمارياً صافياً قدره $22,000!", +14, 0, +6, 0, +2, 22000L,
                        "شراء سندات مالية آمنة بـ $2,000",
                        "حققت السندات المالية أرباحاً مستقرة وعادت عليك بـ $3,500!", +7, 0, +4, 0, +2, 3500L,
                        "الاحتفاظ بالسيولة النقدية في الرصيد البنكي",
                        "تجنبت تقلبات البورصة وحافظت على مدخراتك بأمان.", +2, 0, +2, 0, 0, 0L
                );
            } else {
                return new EventScenario(
                        "وعكة صحية طارئة",
                        "شعرت بصداع نصفي حاد وإرهاق شديد بعد أسبوع طويل من العمل المتواصل.",
                        "مراجعة الطبيب المختص في المستشفى ($250)",
                        "وصف لك الطبيب العلاج المناسب وتماثلت للشفاء التام بسرعة!", +8, +14, +2, 0, +2, -250L,
                        "أخذ إجازة للراحة والنوم في المنزل",
                        "تحسنت حالتك تدريجياً بعد أخذ قسط كافٍ من الراحة.", +5, +6, 0, 0, 0, 0L,
                        "تجاهل الأعراض الصحية ومواصلة السهر",
                        "زاد مستوى التوتر لديك وتراجعت صحتك بسبب الإرهاق.", -6, -10, 0, -2, 0, 0L
                );
            }
        }
    }

    public String[] getUniversityMajors() {
        return new String[]{
                "تخصص علوم الحاسوب (Computer Science)",
                "تخصص المالية (Finance)",
                "تخصص الاقتصاد (Economics)",
                "تخصص الأحياء والطب التمهيدي (Biology)",
                "تخصص العلوم السياسية (Political Science)",
                "تخصص علم النفس (Psychology)",
                "تخصص الهندسة المعمارية (Architecture)",
                "تخصص الهندسة الميكانيكية (Mechanical Engineering)",
                "تخصص الهندسة الكهربائية (Electrical Engineering)",
                "تخصص الهندسة الكيميائية (Chemical Engineering)",
                "تخصص الأمن السيبراني (Cybersecurity)",
                "تخصص المحاسبة (Accounting)",
                "تخصص التمريض (Nursing)",
                "تخصص الصحافة والإعلام (Journalism)",
                "تخصص التصميم الجرافيكي (Graphic Design)",
                "تخصص العدالة الجنائية (Criminal Justice)",
                "تخصص التسويق والإدارة (Marketing & Management)",
                "تخصص الفيزياء والرياضيات (Physics & Mathematics)"
        };
    }

    public List<JobItem> getAvailableFullTimeJobs() {
        List<JobItem> list = new ArrayList<>();
        list.add(new JobItem("جرّاح مخ وأعصاب (Brain Surgeon)", "Cedars-Sinai Medical Center", "الطب", 395_000L, 85, true));
        list.add(new JobItem("جرّاح قلب (Heart Surgeon)", "Mayo Clinic Hospital", "الطب", 360_000L, 82, true));
        list.add(new JobItem("جرّاح تجميل (Plastic Surgeon)", "Beverly Hills Aesthetics", "الطب", 330_000L, 80, true));
        list.add(new JobItem("طبيب نفسي (Psychiatrist)", "Metropolitan Health", "الطب", 215_000L, 76, true));
        list.add(new JobItem("مهندس برمجيات أول (Sr. Software Engineer)", "TechCorp Silicon Valley", "التقنية", 175_000L, 72, true));
        list.add(new JobItem("عالِم بيانات (Data Scientist)", "AI Analytics Corp", "التقنية", 168_000L, 75, true));
        list.add(new JobItem("محلل أمن سيبراني (Cybersecurity Analyst)", "Global Cyber Defense", "التقنية", 142_000L, 70, true));
        list.add(new JobItem("قاضي المحكمة العليا (Supreme Court Justice)", "High Court of Justice", "القانون", 265_000L, 85, true));
        list.add(new JobItem("محامي شركات (Corporate Lawyer)", "Pearson & Specter Law Firm", "القانون", 195_000L, 76, true));
        list.add(new JobItem("مصرفي استثماري (Investment Banker)", "Wall Street Capital", "المالية", 210_000L, 75, true));
        list.add(new JobItem("المستشار المالي (Financial Advisor)", "Sterling Wealth Group", "المالية", 125_000L, 68, true));
        list.add(new JobItem("طيّار خطوط جوية (Airline Pilot)", "Global Airways", "الطيران", 155_000L, 70, true));
        list.add(new JobItem("مهندس معماري (Architect)", "Skyline Design Studio", "الهندسة", 118_000L, 68, true));
        list.add(new JobItem("ضابط شرطة (Police Officer)", "City Police Department", "الأمن", 72_000L, 50, false));
        list.add(new JobItem("محقق خاص (Private Investigator)", "Vance Investigations", "الأمن", 84_000L, 58, false));
        list.add(new JobItem("رجل إطفاء (Firefighter)", "Metro Fire & Rescue", "الطوارئ", 66_000L, 45, false));
        list.add(new JobItem("كبير الطهاة (Head Chef)", "Le Bistro Fine Dining", "الضيافة", 82_000L, 50, false));
        list.add(new JobItem("مراسل صحفي (News Reporter)", "Daily Chronicle Network", "الإعلام", 76_000L, 60, false));
        return list;
    }

    public List<JobItem> getAvailableSpecialCareers() {
        List<JobItem> list = new ArrayList<>();
        list.add(new JobItem("نجم سينمائي في هوليوود (Movie Star Actor)", "Universal Studios", "المهن الخاصة", 550_000L, 50, false));
        list.add(new JobItem("رياضي محترف (Pro Athlete Champion)", "Premier League FC", "المهن الخاصة", 680_000L, 40, false));
        list.add(new JobItem("نجم غناء عالمي (Pop Star Musician)", "Atlantic Records", "المهن الخاصة", 460_000L, 45, false));
        list.add(new JobItem("رائد فضاء (Astronaut)", "Space Agency (NASA)", "المهن الخاصة", 240_000L, 80, true));
        list.add(new JobItem("عمدة المدينة / حاكم الولاية (Governor Politician)", "State Capitol", "المهن الخاصة", 195_000L, 70, false));
        list.add(new JobItem("الزعيم التنفيذي لشركة ناشئة (Startup CEO)", "Unicorn Ventures", "المهن الخاصة", 420_000L, 72, false));
        list.add(new JobItem("العرّاب - زعيم المافيا (Mafia Godfather)", "The Sicilian Syndicate", "المهن الخاصة", 350_000L, 35, false));
        return list;
    }

    public List<AssetItem> getRealEstateCatalog() {
        List<AssetItem> list = new ArrayList<>();
        list.add(new AssetItem(UUID.randomUUID().toString(), "شقة تمليك حديثة (Modern Studio Condo)", "عقار سكني", 145_000L, 90, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "منزل متلاصق عائلي (Suburban Townhouse)", "عقار سكني", 320_000L, 92, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "كوخ خشبي في الجبال (Mountain Cabin)", "عقار ريفي", 260_000L, 88, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "قصر فيكتوري مسكون بالأشباح (Haunted Victorian Mansion)", "عقار مسكون 👻", 890_000L, 65, true));
        list.add(new AssetItem(UUID.randomUUID().toString(), "شقة بنتهاوس فاخرة (Luxury Penthouse)", "عقار فاخر", 2_100_000L, 96, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "فيلا فاخرة على الشاطئ (Malibu Beachfront Villa)", "عقار فاخر", 3_800_000L, 98, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "قصر ملكي تاريخي (Royal Palace Castle)", "عقار أسطوري", 18_500_000L, 100, false));
        return list;
    }

    public List<AssetItem> getVehicleCatalog() {
        List<AssetItem> list = new ArrayList<>();
        list.add(new AssetItem(UUID.randomUUID().toString(), "سيارة سيدان اقتصادية (Toyota Corolla Sedan)", "سيارة", 24_500L, 95, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "سيارة دفع رباعي فاخرة (Range Rover SUV)", "سيارة دفع رباعي", 96_000L, 98, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "سيارة كهربائية (Tesla Model S Plaid)", "سيارة كهربائية", 108_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "سيارة رياضية خارقة (Ferrari 488 Spider)", "سيارة خارقة", 325_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "سيارة أسطورية (Bugatti Chiron Pur Sport)", "سيارة خارقة", 3_600_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "خاتم ألماس 5 قيراط (5-Carat Diamond Ring)", "مجوهرات 💎", 85_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "يخت فاخر عملاق (Superyacht 60m)", "قوارب ويخوت 🛥️", 9_500_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "طائرة نفاثة خاصة (Gulfstream G650 Private Jet)", "طائرة خاصة ✈️", 14_000_000L, 100, false));
        return list;
    }

    public String drawRandomHeirloom(CharacterState state) {
        String picked = HEIRLOOM_POOL[random.nextInt(HEIRLOOM_POOL.length)];
        if (!state.heirlooms.contains(picked)) {
            state.heirlooms.add(picked);
        }
        if (picked.contains("$1,250,000,000")) {
            state.bankBalance += 1_000_000L;
        } else {
            state.bankBalance += 5_000L;
        }
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "🎁 عثرت في خزانة المقتنيات الموروثة (Heirlooms) على: " + picked + "!"
        ));
        return picked;
    }

    public String[][] getCountriesAndCities() {
        return COUNTRIES_AND_CITIES;
    }
}
