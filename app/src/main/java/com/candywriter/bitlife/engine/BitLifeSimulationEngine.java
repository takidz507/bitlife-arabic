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
 * Pure Arabic BitLife Simulation Engine.
 * Strictly preserves all original Western names, countries, cities, and USD ($) currency values.
 */
public class BitLifeSimulationEngine {
    private final Random random = new Random();

    private static final String[] MALE_FIRST_NAMES = {
            "John", "Michael", "Brandon", "Liam", "Noah", "Ethan", "Mason", "Lucas", "Oliver", "Jake", "Ryan", "Tyler"
    };
    private static final String[] FEMALE_FIRST_NAMES = {
            "Emily", "Sophia", "Olivia", "Emma", "Ava", "Chloe", "Madison", "Jessica", " Ashley", "Hannah", "Sarah", "Mia"
    };
    private static final String[] LAST_NAMES = {
            "Smith", "Johnson", "Williams", "Miller", "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Martinez", "Clark"
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
            {"🇧🇷", "Brazil", "Rio de Janeiro"}
    };

    private static final String[] OCCUPATIONS_PARENTS = {
            "محاسب (Accountant)", "معلم مدرسة (School Teacher)", "مهندس برمجيات (Software Engineer)",
            "طبيب أسنان (Dentist)", "مهندس معماري (Architect)", "مدير مبيعات (Sales Manager)",
            "ممرض (Nurse)", "ضابط شرطة (Police Officer)", "طيار (Pilot)", "محامٍ (Lawyer)"
    };

    private static final String[] HEIRLOOM_POOL = {
            "ساعة جيب جدك العتيقة (Grandfather's Pocket Watch) — القيمة: $450",
            "خاتم ألماس عائلي نادر (Family Diamond Ring) — القيمة: $14,500",
            "كأس Святой Graal المقدس (The Holy Grail) — القيمة: $1,250,000,000",
            "لوحة فنية أصلية لـ Banksy — القيمة: $850,000",
            "عملة تذكارية من سفينة Titanic — القيمة: $22,000",
            "ميكروفون قديم لـ Freddie Mercury — القيمة: $65,000"
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
                    bro ? "الأخ الأكبر (Brother)" : "الأخت الكبرى (Sister)",
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
                "والدك هو " + fatherFirst + " " + state.lastName + " (العمر " + fatherAge + " سنة، يعمل كـ " + fatherJob + ") ووالدتك هي " + motherFirst + " " + state.lastName + " (العمر " + motherAge + " سنة، تعمل كـ " + motherJob + ")."
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
                            ? (15000L + random.nextInt(85000))
                            : 0L;
                    if (inheritance > 0) {
                        state.bankBalance += inheritance;
                        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "توفي " + npc.roleArabic + " " + npc.fullName + " عن عمر يناهز " + npc.age + " عاماً، وترك لك ميراثاً قدره " + BitLifeArabicRTLFormatter.formatCurrency(inheritance) + "."
                        ));
                    } else {
                        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "توفي " + npc.roleArabic + " " + npc.fullName + " عن عمر يناهز " + npc.age + " عاماً."
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
                state.addLogEvent("أنهيت محكوميتك في السجن وتم إطلاق سراحك! أنت حر طليق الآن.");
            } else {
                state.addLogEvent("قضيت عاماً آخر خلف القضبان. تبقى من حكمك " + state.prisonYearsLeft + " سنوات.");
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
                state.addLogEvent("انتقلت إلى المرحلة الإعدادية (Middle School).");
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
                state.smarts += 10;
                state.addLogEvent("تخرجت من الجامعة وحصلت على درجة البكالوريوس في " + state.universityMajorArabic + "!");
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
            asset.currentValue = Math.round(asset.currentValue * 1.03);
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
        if (state.age >= 85 && random.nextInt(100) < 28) {
            triggerDeath(state, "أسباب طبيعية أثناء النوم (Natural Causes)");
            return null;
        }
        if (state.health <= 0) {
            triggerDeath(state, "مضاعفات صحية حادة (Severe Health Failure)");
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
                "☠️ ارقد في سلام (R.I.P.): توفي " + state.getFullName() + " عن عمر يناهز " + state.age + " عاماً بسبب: " + causeArabic + "."
        ));
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "🏅 الوسام الممنوح على شاهد القبر: " + state.earnedRibbonArabic + " | صافي الثروة النهائي: " + BitLifeArabicRTLFormatter.formatCurrency(state.calculateNetWorth()) + "."
        ));
    }

    public String evaluateRibbon(CharacterState state) {
        long netWorth = state.calculateNetWorth();
        if (netWorth >= 5_000_000L) return "ثري فاحش (Loaded)";
        if (state.prisonEscapes >= 1) return "هوديني - سيّد الهروب (Houdini)";
        if (state.crimesCommitted >= 3) return "نزيل سجون معتاد (Jailbird)";
        if (state.fame >= 70) return "مشهور عالمي (Famous)";
        if (state.countriesEmigrated >= 2) return "رحّالة عالمي (Globetrotter)";
        if (state.graduatedUniversity && state.smarts >= 85) return "أكاديمي (Academic)";
        if (state.karma >= 85) return "ربّ عائلة مثالي (Family Guy)";
        return "مواطن عادي ( Mediocre )";
    }

    private EventScenario generateAgeAppropriateScenario(CharacterState state) {
        if (state.age <= 5) {
            return new EventScenario(
                    "موعد اللقاح في العيادة",
                    "أخذتك والدتك إلى عيادة الطبيب في " + state.cityName + " لتلقي اللقاح السنوي للأطفال.",
                    "الجلوس بهدوء كالأبطال",
                    "ابتسم الطبيب وأعطاك مصاصة مجانية بعد الحقنة!", +6, +8, +2, 0, +4, 0,
                    "الصراخ والبكاء بصوت عالٍ",
                    "ملأ صراخك العيادة بأكملها، لكنك تلقيت اللقاح في النهاية.", -2, +6, 0, 0, 0, 0,
                    "عضّ يد الطبيب والهرب",
                    "صرخ الطبيب من الألم ووبّختك والدتك بشدة في طريق العودة!", +4, 0, 0, 0, -8, 0
            );
        } else if (state.age <= 17) {
            int pick = random.nextInt(3);
            if (pick == 0) {
                return new EventScenario(
                        "زميل متنمّر في المدرسة!",
                        "قام زميلك Brandon Miller بدفعك نحو الخزائن في الممر وسخر من حذائك أمام الجميع!",
                        "إبلاغ مدير المدرسة فوراً",
                        "عاقب المدير Brandon Miller بالاحتجاز وأشاد بانضباطك.", +4, 0, +3, 0, +5, 0,
                        "الرد عليه بإهانة ساخرة",
                        "ضحك جميع الطلاب على ردك الذكي وانصرف المتنمّر خجلاً!", +10, 0, +4, +2, 0, 0,
                        "تجاهل الأمر والمضي قدماً",
                        "تجنبت المشاكل وواصلت يومك الدراسي بهدوء.", +2, 0, +2, 0, +3, 0
                );
            } else if (pick == 1) {
                return new EventScenario(
                        "اختبار مفاجئ في الرياضيات",
                        "أعلن المعلم فجأة عن اختبار صعب في مادة الجبر دون إشعار مسبق!",
                        "الاعتماد على مجهودك والتركيز",
                        "أجبت عن معظم الأسئلة بنجاح وحصلت على علامة ممتازة!", +6, 0, +7, 0, +4, 0,
                        "محاولة الغش من ورقة زميلك",
                        "لم ينتبه المعلم وحصلت على درجة عالية، لكن ضميرك أنبك قليلاً.", +5, 0, +2, 0, -6, 0,
                        "تخمين الإجابات عشوائياً",
                        "حصلت على درجة متوسطة ولكنك أنهيت الورقة في خمس دقائق!", 0, 0, -3, 0, 0, 0
                );
            } else {
                return new EventScenario(
                        "مصروف الجيب الأسبوعي",
                        "عرض عليك والدك $150 إضافية إذا قمت بتنظيف مرآب المنزل وغسل سيارته.",
                        "قبول العرض والعمل بجد",
                        "نظفت المرآب وغسلت السيارة حتى لمعت، وأعطاك والدك $150 نقداً!", +7, +2, +2, 0, +6, 150L,
                        "التفاوض لطلب $300 بدلاً من ذلك",
                        "أعجب والدك بمهارتك في التفاوض ووافق على إعطائك $250!", +9, 0, +5, 0, +2, 250L,
                        "رفض العرض واللعب بألعاب الفيديو",
                        "قضيت عطلة نهاية الأسبوع في اللعب، لكنك لم تحصل على أي نقود.", +4, 0, -2, 0, -3, 0L
                );
            }
        } else {
            int pick = random.nextInt(3);
            if (pick == 0) {
                return new EventScenario(
                        "محفظة مفقودة في الشارع!",
                        "أثناء مشيك في وسط مدينة " + state.cityName + "، عثرت على محفظة جلدية فاخرة بداخلها $2,500 وبطاقة هوية باسم Richard Vance.",
                        "إعادة المحفظة كاملة إلى صاحبها",
                        "شكرَك Richard Vance بحرارة وكافأك بمبلغ $500 تقديراً لأمانتك!", +10, 0, +2, 0, +15, 500L,
                        "الاحتفاظ بمبلغ $2,500 لنفسك",
                        "وضعت النقود في جيبك وغادرت المكان بسرعة دون أن يراك أحد.", +8, 0, 0, 0, -18, 2500L,
                        "تسليم المحفظة إلى مركز الشرطة",
                        "سجل الضابط اسمك في لوحة الشرف للمواطنين الصالحين.", +6, 0, +2, 0, +12, 0L
                );
            } else if (pick == 1) {
                return new EventScenario(
                        "شائعات في مكان العمل",
                        "أخبرك زميلك أن المشرف المباشر يخطط لاختيار موظف واحد لتمثيل القسم في مؤتمر دولي.",
                        "تقديم عرض تقديمي احترافي",
                        "أبهر عرضك الإدارة وحصلت على مكافأة تشجيعية قدرها $3,000!", +10, 0, +6, 0, +5, 3000L,
                        "إهداء المشرف قهوة الصباح",
                        "ابتسم المشرف وتحسنت علاقتكما المهنية في المكتب.", +5, 0, +2, 0, +2, -25L,
                        "التركيز على مهامك المعتادة فقط",
                        "مرّ الأسبوع بهدوء دون أي توتر إضافي.", +2, +2, 0, 0, 0, 0L
                );
            } else {
                return new EventScenario(
                        "فرصة استثمارية سريعة",
                        "عرض عليك صديقك القديم استثمار مبلغ $5,000 في مشروع تطبيق تقني ناشئ في Silicon Valley.",
                        "المخاطرة واستثمار $5,000",
                        "نجح التطبيق نجاحاً باهراً وحققت عائداً فورياً قدره $25,000!", +14, 0, +5, 0, +2, 20000L,
                        "استثمار مبلغ صغير ($1,000 فقط)",
                        "حقق المشروع أرباحاً جيدة وعاد عليك بمبلغ $4,000 صافية!", +8, 0, +4, 0, 0, 3000L,
                        "الاعتذار والاحتفاظ بأموالك في البنك",
                        "فضّلت الأمان المالي وعدم المخاطرة بمدخراتك.", +2, 0, +2, 0, 0, 0L
                );
            }
        }
    }

    public List<JobItem> getAvailableFullTimeJobs() {
        List<JobItem> list = new ArrayList<>();
        list.add(new JobItem("جرّاح مخ وأعصاب (Brain Surgeon)", "Cedars-Sinai Medical Center", "الطب", 385_000L, 85, true));
        list.add(new JobItem("مهندس برمجيات أول (Sr. Software Engineer)", "TechCorp Silicon Valley", "التقنية", 165_000L, 75, true));
        list.add(new JobItem("محامي شركات (Corporate Lawyer)", "Pearson & Specter Law Firm", "القانون", 190_000L, 78, true));
        list.add(new JobItem("طيّار خطوط جوية (Airline Pilot)", "Global Airways", "الطيران", 145_000L, 70, true));
        list.add(new JobItem("ضابط شرطة (Police Officer)", "City Police Department", "الأمن", 68_000L, 50, false));
        list.add(new JobItem("رجل إطفاء (Firefighter)", "Metro Fire & Rescue", "الطوارئ", 62_000L, 45, false));
        list.add(new JobItem("طاهٍ تنفيذي (Executive Chef)", "Le Bistro Restaurant", "الضيافة", 74_000L, 50, false));
        list.add(new JobItem("مسؤول تسويق رقمي (Marketing Specialist)", "Creative Media LLC", "الأعمال", 82_000L, 60, false));
        return list;
    }

    public List<JobItem> getAvailableSpecialCareers() {
        List<JobItem> list = new ArrayList<>();
        list.add(new JobItem("ممثل سينمائي في هوليوود (Hollywood Actor)", "Universal Studios", "المهن الخاصة", 450_000L, 50, false));
        list.add(new JobItem("رياضي كرة قدم محترف (Pro Athlete)", "Premier League FC", "المهن الخاصة", 620_000L, 40, false));
        list.add(new JobItem("مغنّي بوب منفرد (Pop Star Musician)", "Atlantic Records", "المهن الخاصة", 390_000L, 45, false));
        list.add(new JobItem("رائد فضاء (Astronaut)", "Space Agency (NASA)", "المهن الخاصة", 210_000L, 82, true));
        list.add(new JobItem("عمدة المدينة (Mayor / Politician)", "City Hall", "المهن الخاصة", 175_000L, 70, false));
        list.add(new JobItem("عضو في عائلة المافيا (Mafia Associate)", "The Gambino Family", "المهن الخاصة", 120_000L, 35, false));
        return list;
    }

    public List<AssetItem> getRealEstateCatalog() {
        List<AssetItem> list = new ArrayList<>();
        list.add(new AssetItem(UUID.randomUUID().toString(), "شقة استوديو حديثة (Modern Studio Condo)", "عقار سكني", 145_000L, 90, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "منزل عائلي في الضواحي (Suburban Family Home)", "عقار سكني", 420_000L, 92, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "قصر فيكتوري مسكون بالأشباح (Haunted Victorian Mansion)", "عقار مسكون 👻", 890_000L, 65, true));
        list.add(new AssetItem(UUID.randomUUID().toString(), "فيلا فاخرة على الشاطئ (Malibu Beachfront Villa)", "عقار فاخر", 3_400_000L, 98, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "قصر ملكي تاريخي (Royal Palace Estate)", "عقار أسطوري", 18_500_000L, 100, false));
        return list;
    }

    public List<AssetItem> getVehicleCatalog() {
        List<AssetItem> list = new ArrayList<>();
        list.add(new AssetItem(UUID.randomUUID().toString(), "Toyota Corolla Sedan", "سيارة", 24_500L, 95, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "Tesla Model S Plaid", "سيارة كهربائية", 108_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "Ferrari 488 Spider", "سيارة رياضية خارقة", 325_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "Bugatti Chiron Pur Sport", "سيارة أسطورية", 3_600_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "Gulfstream G650 Private Jet", "طائرة خاصة ✈️", 14_000_000L, 100, false));
        list.add(new AssetItem(UUID.randomUUID().toString(), "Luxury Superyacht 60m", "يخت فاخر 🛥️", 9_500_000L, 100, false));
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
            state.bankBalance += 2_500L;
        }
        state.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "🎁 عثرت في علّية المنزل على مقتنى موروث (Heirloom): " + picked + "!"
        ));
        return picked;
    }

    public String[][] getCountriesAndCities() {
        return COUNTRIES_AND_CITIES;
    }
}
