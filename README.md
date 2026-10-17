# BitLife - محاكي الحياة (النسخة العربية الكاملة — مشروع Android Studio جاهز للبناء عبر GitHub Actions)

مشروع **Android Studio** متكامل وجاهز للبناء الفوري عبر **GitHub Actions** من أول مرة بدون أي أخطاء (`gradle assembleDebug`).

## القاعدة الذهبية المطبقة في التعريب

1. **الترجمة اللغوية النقية 100%**: جميع القوائم، الأزرار، الأحداث، المهن، العلاقات، الأصول، والأنشطة مترجمة إلى العربية الفصحى الواضحة مع الحفاظ على الطرافة الساخرة للنص الأصلي.
2. **الحفاظ على المحتوى الأصلي دون تكييف ثقافي**:
   - الأسماء تبقى كما هي بالحروف الأصلية (`John Smith`, `Sophia Martinez`, `Brandon Miller`).
   - العملة تبقى هي الدولار الأمريكي (`$`) دون استبدال.
   - الدول والمدن والمناسبات والمهن تبقى كما هي في اللعبة الأصلية.
3. **دعم اتجاه اليمين-إلى-اليسار (RTL) وعزل المتغيرات (BiDi)**:
   - تفعيل `android:supportsRtl="true"` و `android:layoutDirection="rtl"` في الواجهة.
   - حماية جميع المبالغ المالية (`$1,500`) والأسماء اللاتينية والمتغيرات (`%1$d`, `{name}`) برموز العزل القياسية `U+2066` ... `U+2069` عبر `BitLifeArabicRTLFormatter.java`.

## طريقة البناء التلقائي عبر GitHub Actions

1. ارفع جميع ملفات هذا المشروع إلى مستودع GitHub جديد.
2. سيعمل ملف `.github/workflows/build-apk.yml` تلقائياً باستخدام:
   - `actions/checkout@v4`
   - `actions/setup-java@v4` (JDK 17 Temurin)
   - Android SDK (`platforms;android-34` + `build-tools;34.0.0`)
   - `gradle/actions/setup-gradle@v3` (Gradle 8.4)
   - `gradle assembleDebug`
3. بعد انتهاء البناء، حمّل ملف الـ APK الجاهز من قسم **Artifacts** باسم **`bitlife-arabic-debug-apk`**.
