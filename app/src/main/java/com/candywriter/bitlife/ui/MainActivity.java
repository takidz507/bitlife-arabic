package com.candywriter.bitlife.ui;

import android.content.res.ColorStateList;
import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.candywriter.bitlife.R;
import com.candywriter.bitlife.engine.BitLifeArabicRTLFormatter;
import com.candywriter.bitlife.engine.BitLifeSimulationEngine;
import com.candywriter.bitlife.models.AssetItem;
import com.candywriter.bitlife.models.CharacterState;
import com.candywriter.bitlife.models.EventScenario;
import com.candywriter.bitlife.models.JobItem;
import com.candywriter.bitlife.models.NpcPerson;
import com.candywriter.bitlife.ui.adapters.LifeLogAdapter;
import com.candywriter.bitlife.utils.OriginalApkPatcherInfo;
import com.candywriter.bitlife.utils.SaveGameManager;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.UUID;

public class MainActivity extends AppCompatActivity {

    private BitLifeSimulationEngine engine;
    private SaveGameManager saveManager;
    private CharacterState currentLife;
    private final Random random = new Random();

    private TextView tvCharacterName;
    private TextView tvCharacterOccupation;
    private TextView tvBankBalance;
    private RecyclerView rvLifeLog;
    private LifeLogAdapter lifeLogAdapter;

    private MaterialButton btnMainMenu;
    private MaterialButton btnHeirloom;
    private MaterialButton btnTabOccupation;
    private MaterialButton btnTabAssets;
    private MaterialButton btnAgeUp;
    private MaterialButton btnTabRelationships;
    private MaterialButton btnTabActivities;

    private ProgressBar pbHappiness;
    private ProgressBar pbHealth;
    private ProgressBar pbSmarts;
    private ProgressBar pbLooks;
    private TextView tvHappinessPct;
    private TextView tvHealthPct;
    private TextView tvSmartsPct;
    private TextView tvLooksPct;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        engine = new BitLifeSimulationEngine();
        saveManager = new SaveGameManager(this);

        initViews();

        currentLife = saveManager.loadActiveLife();
        if (currentLife == null) {
            currentLife = engine.createNewRandomLife(null, null, null, -1);
            saveManager.saveActiveLife(currentLife);
        }
        refreshUI();
    }

    private void initViews() {
        tvCharacterName = findViewById(R.id.tvCharacterName);
        tvCharacterOccupation = findViewById(R.id.tvCharacterOccupation);
        tvBankBalance = findViewById(R.id.tvBankBalance);
        rvLifeLog = findViewById(R.id.rvLifeLog);

        btnMainMenu = findViewById(R.id.btnMainMenu);
        btnHeirloom = findViewById(R.id.btnHeirloom);
        btnTabOccupation = findViewById(R.id.btnTabOccupation);
        btnTabAssets = findViewById(R.id.btnTabAssets);
        btnAgeUp = findViewById(R.id.btnAgeUp);
        btnTabRelationships = findViewById(R.id.btnTabRelationships);
        btnTabActivities = findViewById(R.id.btnTabActivities);

        pbHappiness = findViewById(R.id.pbHappiness);
        pbHealth = findViewById(R.id.pbHealth);
        pbSmarts = findViewById(R.id.pbSmarts);
        pbLooks = findViewById(R.id.pbLooks);

        tvHappinessPct = findViewById(R.id.tvHappinessPct);
        tvHealthPct = findViewById(R.id.tvHealthPct);
        tvSmartsPct = findViewById(R.id.tvSmartsPct);
        tvLooksPct = findViewById(R.id.tvLooksPct);

        LinearLayoutManager lm = new LinearLayoutManager(this);
        lm.setStackFromEnd(true);
        rvLifeLog.setLayoutManager(lm);
        lifeLogAdapter = new LifeLogAdapter();
        rvLifeLog.setAdapter(lifeLogAdapter);

        btnMainMenu.setOnClickListener(v -> showMainMenuDialog());
        btnHeirloom.setOnClickListener(v -> onHeirloomClicked());
        btnAgeUp.setOnClickListener(v -> onAgeUpClicked());
        btnTabOccupation.setOnClickListener(v -> showOccupationMenu());
        btnTabAssets.setOnClickListener(v -> showAssetsMenu());
        btnTabRelationships.setOnClickListener(v -> showRelationshipsMenu());
        btnTabActivities.setOnClickListener(v -> showActivitiesMenu());
    }

    private void refreshUI() {
        if (currentLife == null) return;
        currentLife.clampStats();

        tvCharacterName.setText(currentLife.countryFlag + " " + currentLife.getFullName());
        String roleLine = currentLife.occupationTitleArabic + " (" + currentLife.age + " سنة) • "
                + currentLife.cityName + ", " + currentLife.countryName;
        tvCharacterOccupation.setText(BitLifeArabicRTLFormatter.protectBiDi(roleLine));

        tvBankBalance.setText(BitLifeArabicRTLFormatter.formatCurrency(currentLife.bankBalance));
        int balColor = currentLife.bankBalance >= 0
                ? ContextCompat.getColor(this, R.color.stat_high)
                : ContextCompat.getColor(this, R.color.stat_low);
        tvBankBalance.setTextColor(balColor);

        updateStatBar(pbHappiness, tvHappinessPct, currentLife.happiness);
        updateStatBar(pbHealth, tvHealthPct, currentLife.health);
        updateStatBar(pbSmarts, tvSmartsPct, currentLife.smarts);
        updateStatBar(pbLooks, tvLooksPct, currentLife.looks);

        btnAgeUp.setText(currentLife.isAlive ? "+ العمر" : "حياة جديدة");

        lifeLogAdapter.submitList(currentLife.lifeLogs);
        if (!currentLife.lifeLogs.isEmpty()) {
            rvLifeLog.scrollToPosition(currentLife.lifeLogs.size() - 1);
        }
        saveManager.saveActiveLife(currentLife);
    }

    private void updateStatBar(ProgressBar pb, TextView tv, int value) {
        pb.setProgress(value);
        tv.setText(value + "%");
        int colorRes = value >= 65 ? R.color.stat_high : (value >= 35 ? R.color.stat_medium : R.color.stat_low);
        pb.setProgressTintList(ColorStateList.valueOf(ContextCompat.getColor(this, colorRes)));
    }

    private void onAgeUpClicked() {
        if (!currentLife.isAlive) {
            currentLife = engine.createNewRandomLife(null, null, null, -1);
            refreshUI();
            return;
        }

        EventScenario scenario = engine.ageUpOneYear(currentLife);
        if (!currentLife.isAlive) {
            saveManager.recordDeceasedInCemetery(currentLife);
            refreshUI();
            showDeathSummaryDialog();
            return;
        }

        refreshUI();
        if (scenario != null) {
            showScenarioPopup(scenario);
        }
    }

    private void showScenarioPopup(EventScenario sc) {
        String[] options = new String[]{sc.option1Text, sc.option2Text, sc.option3Text};
        new MaterialAlertDialogBuilder(this)
                .setTitle(sc.titleArabic + "\n\n" + BitLifeArabicRTLFormatter.protectBiDi(sc.descriptionArabic))
                .setCancelable(false)
                .setItems(options, (dialog, which) -> {
                    String outcome = (which == 0) ? sc.outcome1Text : (which == 1 ? sc.outcome2Text : sc.outcome3Text);
                    currentLife.happiness += sc.deltaHappiness[which];
                    currentLife.health += sc.deltaHealth[which];
                    currentLife.smarts += sc.deltaSmarts[which];
                    currentLife.looks += sc.deltaLooks[which];
                    currentLife.karma += sc.deltaKarma[which];
                    currentLife.bankBalance += sc.deltaMoney[which];

                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(outcome));
                    refreshUI();
                })
                .show();
    }

    private void onHeirloomClicked() {
        String heirloom = engine.drawRandomHeirloom(currentLife);
        refreshUI();
        new MaterialAlertDialogBuilder(this)
                .setTitle("🎁 المقتنيات الموروثة (Heirlooms)")
                .setMessage(BitLifeArabicRTLFormatter.protectBiDi("حصلت اليوم على مقتنى عائلي موروث:\n\n" + heirloom))
                .setPositiveButton("رائع!", null)
                .show();
    }

    private void showOccupationMenu() {
        if (!currentLife.isAlive) return;
        List<String> items = new ArrayList<>();
        if (currentLife.age < 18) {
            items.add(getString(R.string.occ_school_study_harder));
            items.add(getString(R.string.occ_school_skip));
        } else {
            if (!currentLife.graduatedUniversity && !currentLife.inUniversity) {
                items.add(getString(R.string.occ_apply_university));
            }
            if (currentLife.annualSalary > 0) {
                items.add(getString(R.string.occ_work_harder));
                items.add(getString(R.string.occ_ask_raise));
                items.add(getString(R.string.occ_resign));
            }
            items.add(getString(R.string.occ_full_time_jobs));
            items.add(getString(R.string.occ_special_careers));
        }

        new MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.occ_title))
                .setItems(items.toArray(new String[0]), (d, which) -> {
                    String chosen = items.get(which);
                    if (chosen.equals(getString(R.string.occ_school_study_harder))) {
                        currentLife.smarts += 6;
                        currentLife.addLogEvent("بذلت جهداً مضاعفاً في الدراسة هذا العام وارتفعت درجاتك المدرسية.");
                        refreshUI();
                    } else if (chosen.equals(getString(R.string.occ_school_skip))) {
                        currentLife.happiness += 5;
                        currentLife.smarts -= 5;
                        currentLife.addLogEvent("تغيبت عن المدرسة لقضاء اليوم في التجول، وعلم مدير المدرسة بذلك!");
                        refreshUI();
                    } else if (chosen.equals(getString(R.string.occ_apply_university))) {
                        showUniversityMajorsDialog();
                    } else if (chosen.equals(getString(R.string.occ_work_harder))) {
                        currentLife.happiness -= 2;
                        currentLife.addLogEvent("عملت بجهد إضافي في وظيفتك كـ " + currentLife.occupationTitleArabic + " ونلت إعجاب المشرف.");
                        refreshUI();
                    } else if (chosen.equals(getString(R.string.occ_ask_raise))) {
                        long raise = Math.round(currentLife.annualSalary * 0.12);
                        currentLife.annualSalary += raise;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "وافقت الإدارة على منحك علاوة سنوية! أصبح راتبك الجديد " + BitLifeArabicRTLFormatter.formatCurrency(currentLife.annualSalary) + "."
                        ));
                        refreshUI();
                    } else if (chosen.equals(getString(R.string.occ_resign))) {
                        currentLife.addLogEvent("قدمت استقالتك من وظيفتك كـ " + currentLife.occupationTitleArabic + ".");
                        currentLife.occupationTitleArabic = "عاطل عن العمل";
                        currentLife.annualSalary = 0L;
                        refreshUI();
                    } else if (chosen.equals(getString(R.string.occ_full_time_jobs))) {
                        showJobListDialog(engine.getAvailableFullTimeJobs(), "وظائف بدوام كامل");
                    } else if (chosen.equals(getString(R.string.occ_special_careers))) {
                        showJobListDialog(engine.getAvailableSpecialCareers(), "المهن الخاصة (Special Careers)");
                    }
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showUniversityMajorsDialog() {
        String[] majors = engine.getUniversityMajors();
        new MaterialAlertDialogBuilder(this)
                .setTitle("🎓 اختر التخصص الجامعي (University Major)")
                .setItems(majors, (d, w) -> {
                    currentLife.inUniversity = true;
                    currentLife.universityMajorArabic = majors[w];
                    currentLife.occupationTitleArabic = "طالب جامعي (" + majors[w] + ")";
                    currentLife.addLogEvent("تم قبولك في الجامعة لدراسة تخصص " + majors[w] + " بمنحة دراسية كاملة!");
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_cancel), null)
                .show();
    }

    private void showJobListDialog(List<JobItem> jobs, String title) {
        String[] labels = new String[jobs.size()];
        for (int i = 0; i < jobs.size(); i++) {
            JobItem j = jobs.get(i);
            labels[i] = j.titleArabic + " — " + j.companyName + " (" + BitLifeArabicRTLFormatter.formatCurrency(j.annualSalary) + "/سنة)";
        }
        new MaterialAlertDialogBuilder(this)
                .setTitle(title)
                .setItems(labels, (d, which) -> {
                    JobItem selected = jobs.get(which);
                    if (selected.requiresUniversity && !currentLife.graduatedUniversity) {
                        Toast.makeText(this, "يتطلب هذا المنصب شهادة جامعية أولاً!", Toast.LENGTH_LONG).show();
                        return;
                    }
                    if (currentLife.smarts < selected.minSmarts) {
                        Toast.makeText(this, "لم تجتز المقابلة الوظيفية (تحتاج لمستوى ذكاء أعلى)!", Toast.LENGTH_LONG).show();
                        return;
                    }
                    currentLife.occupationTitleArabic = selected.titleArabic;
                    currentLife.employerName = selected.companyName;
                    currentLife.annualSalary = selected.annualSalary;
                    if (selected.categoryArabic.contains("المهن الخاصة")) {
                        currentLife.fame = Math.min(100, currentLife.fame + 45);
                    }
                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                            "تهانينا! تم تعيينك في منصب " + selected.titleArabic + " لدى " + selected.companyName + " براتب سنوي قدره " + BitLifeArabicRTLFormatter.formatCurrency(selected.annualSalary) + "!"
                    ));
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_back), null)
                .show();
    }

    private void showAssetsMenu() {
        if (!currentLife.isAlive) return;
        String[] options = {
                getString(R.string.assets_finances_summary),
                getString(R.string.assets_real_estate),
                getString(R.string.assets_cars),
                getString(R.string.assets_my_properties) + " (" + currentLife.assets.size() + ")"
        };
        new MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.assets_title))
                .setItems(options, (d, which) -> {
                    if (which == 0) {
                        String msg = "صافي الثروة الإجمالي: " + BitLifeArabicRTLFormatter.formatCurrency(currentLife.calculateNetWorth())
                                + "\nالرصيد البنكي السائل: " + BitLifeArabicRTLFormatter.formatCurrency(currentLife.bankBalance)
                                + "\nالراتب السنوي الحالي: " + BitLifeArabicRTLFormatter.formatCurrency(currentLife.annualSalary)
                                + "\nعدد العقارات والمركبات: " + currentLife.assets.size();
                        new MaterialAlertDialogBuilder(this)
                                .setTitle("💰 الشؤون المالية (Finances)")
                                .setMessage(BitLifeArabicRTLFormatter.protectBiDi(msg))
                                .setPositiveButton(getString(R.string.btn_ok), null)
                                .show();
                    } else if (which == 1) {
                        showAssetCatalogDialog(engine.getRealEstateCatalog(), "🏠 وسطاء العقارات (Real Estate)");
                    } else if (which == 2) {
                        showAssetCatalogDialog(engine.getVehicleCatalog(), "🚗 وكالات السيارات والطائرات");
                    } else if (which == 3) {
                        showOwnedAssetsDialog();
                    }
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showAssetCatalogDialog(List<AssetItem> catalog, String title) {
        String[] labels = new String[catalog.size()];
        for (int i = 0; i < catalog.size(); i++) {
            AssetItem a = catalog.get(i);
            labels[i] = a.name + " — السعر: " + BitLifeArabicRTLFormatter.formatCurrency(a.purchasePrice);
        }
        new MaterialAlertDialogBuilder(this)
                .setTitle(title)
                .setItems(labels, (d, which) -> {
                    AssetItem item = catalog.get(which);
                    if (currentLife.bankBalance < item.purchasePrice) {
                        Toast.makeText(this, "رصيدك البنكي غير كافٍ لشراء " + item.name + "!", Toast.LENGTH_LONG).show();
                        return;
                    }
                    currentLife.bankBalance -= item.purchasePrice;
                    currentLife.assets.add(item);
                    currentLife.happiness += 8;
                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                            "اشتريت " + item.name + " مقابل " + BitLifeArabicRTLFormatter.formatCurrency(item.purchasePrice) + " نقداً!"
                    ));
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_back), null)
                .show();
    }

    private void showOwnedAssetsDialog() {
        if (currentLife.assets.isEmpty()) {
            Toast.makeText(this, "لا تمتلك أي عقارات أو مركبات حالياً.", Toast.LENGTH_SHORT).show();
            return;
        }
        String[] labels = new String[currentLife.assets.size()];
        for (int i = 0; i < currentLife.assets.size(); i++) {
            AssetItem a = currentLife.assets.get(i);
            String status = a.isRentedOut ? " [مؤجّر]" : (a.isHaunted ? " [مسكون 👻]" : "");
            labels[i] = a.name + status + " — القيمة: " + BitLifeArabicRTLFormatter.formatCurrency(a.currentValue);
        }
        new MaterialAlertDialogBuilder(this)
                .setTitle("🔑 ممتلكاتي الحالية")
                .setItems(labels, (d, idx) -> {
                    AssetItem asset = currentLife.assets.get(idx);
                    String[] actions = {
                            "💵 بيع الممتلكات مقابل " + BitLifeArabicRTLFormatter.formatCurrency(asset.currentValue),
                            asset.isRentedOut ? "🏠 إلغاء التأجير" : "🔑 تأجير العقار للمستأجرين (" + BitLifeArabicRTLFormatter.formatCurrency(asset.monthlyRent) + "/شهر)",
                            "🛠️ ترميم وصيانة (+15% للحالة)"
                    };
                    new MaterialAlertDialogBuilder(this)
                            .setTitle(asset.name)
                            .setItems(actions, (d2, actIdx) -> {
                                if (actIdx == 0) {
                                    currentLife.bankBalance += asset.currentValue;
                                    currentLife.assets.remove(idx);
                                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                            "بعت " + asset.name + " مقابل " + BitLifeArabicRTLFormatter.formatCurrency(asset.currentValue) + "."
                                    ));
                                } else if (actIdx == 1) {
                                    asset.isRentedOut = !asset.isRentedOut;
                                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                            asset.isRentedOut
                                                    ? ("قمت بتأجير " + asset.name + " بمبلغ شهري قدره " + BitLifeArabicRTLFormatter.formatCurrency(asset.monthlyRent) + ".")
                                                    : ("أنهيت عقد تأجير " + asset.name + ".")
                                    ));
                                } else {
                                    long cost = Math.max(500L, asset.currentValue / 20);
                                    currentLife.bankBalance -= cost;
                                    asset.condition = Math.min(100, asset.condition + 15);
                                    asset.currentValue = Math.round(asset.currentValue * 1.08);
                                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                            "رممت " + asset.name + " بتكلفة " + BitLifeArabicRTLFormatter.formatCurrency(cost) + "."
                                    ));
                                }
                                refreshUI();
                            })
                            .show();
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showRelationshipsMenu() {
        if (!currentLife.isAlive) return;
        List<NpcPerson> aliveNpcs = new ArrayList<>();
        for (NpcPerson p : currentLife.relationships) {
            if (p.isAlive) aliveNpcs.add(p);
        }

        String[] items = new String[aliveNpcs.size() + 1];
        items[0] = getString(R.string.rel_spend_time_all);
        for (int i = 0; i < aliveNpcs.size(); i++) {
            NpcPerson p = aliveNpcs.get(i);
            items[i + 1] = p.fullName + " — " + p.roleArabic + " (العلاقة: " + p.relationship + "%)";
        }

        new MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.rel_title))
                .setItems(items, (d, which) -> {
                    if (which == 0) {
                        for (NpcPerson p : aliveNpcs) {
                            p.relationship = Math.min(100, p.relationship + 8);
                        }
                        currentLife.happiness += 8;
                        currentLife.addLogEvent("قضيت وقتاً ممتعاً مع جميع أفراد عائلتك وأصدقائك.");
                        refreshUI();
                    } else {
                        showSingleRelationshipActions(aliveNpcs.get(which - 1));
                    }
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showSingleRelationshipActions(NpcPerson person) {
        List<String> acts = new ArrayList<>();
        acts.add(getString(R.string.rel_act_conversation));
        acts.add(getString(R.string.rel_act_compliment));
        acts.add(getString(R.string.rel_act_spend_time));
        acts.add(getString(R.string.rel_act_give_gift));
        acts.add(getString(R.string.rel_act_ask_money));
        acts.add(getString(R.string.rel_act_argue));
        if (person.isPartner) {
            acts.add(getString(R.string.rel_act_make_love));
            if (!person.isMarried) {
                acts.add(getString(R.string.rel_act_propose));
            }
            acts.add(getString(R.string.rel_act_divorce));
        }

        new MaterialAlertDialogBuilder(this)
                .setTitle(person.fullName + " (" + person.roleArabic + ")")
                .setItems(acts.toArray(new String[0]), (d, idx) -> {
                    String act = acts.get(idx);
                    if (act.equals(getString(R.string.rel_act_conversation))) {
                        person.relationship = Math.min(100, person.relationship + 8);
                        currentLife.happiness += 4;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "دارت بينك وبين " + person.fullName + " محادثة ممتعة للغاية."
                        ));
                    } else if (act.equals(getString(R.string.rel_act_compliment))) {
                        person.relationship = Math.min(100, person.relationship + 10);
                        currentLife.happiness += 5;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "وجهت إطراءً لطيفاً إلى " + person.fullName + " وأدخلت السرور على قلبه."
                        ));
                    } else if (act.equals(getString(R.string.rel_act_spend_time))) {
                        person.relationship = Math.min(100, person.relationship + 12);
                        currentLife.happiness += 6;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "قضيت يوماً رائعاً برفقة " + person.fullName + "."
                        ));
                    } else if (act.equals(getString(R.string.rel_act_give_gift))) {
                        currentLife.bankBalance -= 150L;
                        person.relationship = Math.min(100, person.relationship + 15);
                        currentLife.karma += 5;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "قدمت هدية بقيمة $150 إلى " + person.fullName + " وأحبها كثيراً!"
                        ));
                    } else if (act.equals(getString(R.string.rel_act_ask_money))) {
                        long gift = 100L + random.nextInt(900);
                        currentLife.bankBalance += gift;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "طلبت المال من " + person.fullName + " فأعطاك " + BitLifeArabicRTLFormatter.formatCurrency(gift) + "!"
                        ));
                    } else if (act.equals(getString(R.string.rel_act_argue))) {
                        person.relationship = Math.max(0, person.relationship - 18);
                        currentLife.happiness -= 5;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "دخلت في جدال حاد مع " + person.fullName + "."
                        ));
                    } else if (act.equals(getString(R.string.rel_act_make_love))) {
                        currentLife.happiness += 12;
                        if (currentLife.age >= 18 && currentLife.age <= 45 && random.nextBoolean()) {
                            boolean boy = random.nextBoolean();
                            String childFirst = boy ? "Noah" : "Sophia";
                            String childFull = childFirst + " " + currentLife.lastName;
                            currentLife.relationships.add(new NpcPerson(
                                    UUID.randomUUID().toString(),
                                    childFull,
                                    boy ? "الابن (Son)" : "الابنة (Daughter)",
                                    "رضيع",
                                    0,
                                    95
                            ));
                            currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                    "👶 رُزقت بمولود جديد من " + person.fullName + "! أسميتماه " + childFull + "."
                            ));
                        } else {
                            currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                    "قضيت أوقاتاً رومانسية سعيدة مع شريكك " + person.fullName + "."
                            ));
                        }
                    } else if (act.equals(getString(R.string.rel_act_propose))) {
                        person.isMarried = true;
                        person.roleArabic = person.roleArabic.contains("Girlfriend") ? "الزوجة (Wife)" : "الزوج (Husband)";
                        currentLife.happiness += 18;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "💍 تقدمت لطلب الزواج من " + person.fullName + " ووافق فوراً! أقمتما حفل زفاف رائع."
                        ));
                    } else if (act.equals(getString(R.string.rel_act_divorce))) {
                        currentLife.relationships.remove(person);
                        currentLife.happiness -= 12;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "💔 انفصلت رسمياً عن " + person.fullName + "."
                        ));
                    }
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_back), null)
                .show();
    }

    private void showActivitiesMenu() {
        if (!currentLife.isAlive) return;
        String[] acts = {
                getString(R.string.act_mind_body),
                getString(R.string.act_doctor),
                getString(R.string.act_plastic_surgery),
                getString(R.string.act_love_dating),
                getString(R.string.act_crime),
                getString(R.string.act_casino_lottery),
                getString(R.string.act_emigrate),
                getString(R.string.act_social_media),
                getString(R.string.act_surrender)
        };

        new MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.act_title))
                .setItems(acts, (d, which) -> {
                    switch (which) {
                        case 0:
                            currentLife.health += 8;
                            currentLife.happiness += 7;
                            currentLife.smarts += 6;
                            currentLife.looks += 5;
                            currentLife.addLogEvent("ذهبت إلى النادي الرياضي، مارست التأمل (Meditation)، وقرأت كتاباً في المكتبة العامة.");
                            refreshUI();
                            break;
                        case 1:
                            currentLife.bankBalance -= 200L;
                            currentLife.health = Math.min(100, currentLife.health + 20);
                            currentLife.addLogEvent("زرت الطبيب لإجراء فحص شامل وتلقي العلاج ($200). تحسنت صحتك بشكل ملحوظ!");
                            refreshUI();
                            break;
                        case 2:
                            currentLife.bankBalance -= 4500L;
                            currentLife.looks = Math.min(100, currentLife.looks + 22);
                            currentLife.addLogEvent("أجريت عملية تجميلية ناجحة بتكلفة $4,500 وازدادت جاذبيتك!");
                            refreshUI();
                            break;
                        case 3:
                            findNewPartner();
                            break;
                        case 4:
                            showCrimeMenu();
                            break;
                        case 5:
                            playLotteryOrCasino();
                            break;
                        case 6:
                            showEmigrateDialog();
                            break;
                        case 7:
                            currentLife.fame = Math.min(100, currentLife.fame + 12);
                            currentLife.happiness += 5;
                            currentLife.addLogEvent("نشرت مقطع فيديو رائجاً (Viral Video) على وسائل التواصل الاجتماعي وحصدت آلاف المتابعين!");
                            refreshUI();
                            break;
                        case 8:
                            confirmSurrender();
                            break;
                    }
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void findNewPartner() {
        if (currentLife.age < 16) {
            Toast.makeText(this, "يجب أن يكون عمرك 16 سنة على الأقل للمواعدة!", Toast.LENGTH_SHORT).show();
            return;
        }
        boolean femalePartner = "ذكر".equals(currentLife.genderArabic);
        String partnerName = femalePartner ? "Chloe Davis" : "Ryan Anderson";
        String role = femalePartner ? "الحبيبة (Girlfriend)" : "الحبيب (Boyfriend)";
        NpcPerson partner = new NpcPerson(
                UUID.randomUUID().toString(),
                partnerName,
                role,
                "مصمم جرافيك (Graphic Designer)",
                currentLife.age,
                85
        );
        partner.isPartner = true;
        currentLife.relationships.add(partner);
        currentLife.happiness += 12;
        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                "💘 تعرفت على " + partnerName + " وبدأت بينكما علاقة عاطفية!"
        ));
        refreshUI();
    }

    private void showCrimeMenu() {
        String[] crimes = {
                "👜 نشل الجيوب (Pickpocket)",
                "🚗 سرقة سيارات فاخرة (Grand Theft Auto)",
                "🏦 سطو مسلح على بنك (Bank Robbery)",
                "🔓 الهروب من السجن (Prison Escape)"
        };
        new MaterialAlertDialogBuilder(this)
                .setTitle("🕵️ الجريمة (Crime)")
                .setItems(crimes, (d, which) -> {
                    if (which == 3) {
                        if (!currentLife.inPrison) {
                            Toast.makeText(this, "أنت لست في السجن حالياً!", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        currentLife.inPrison = false;
                        currentLife.prisonYearsLeft = 0;
                        currentLife.prisonEscapes++;
                        currentLife.addLogEvent("🔓 نجحت في التسلل عبر أنفاق الصرف والهروب من السجن ببراعة!");
                        refreshUI();
                        return;
                    }

                    currentLife.crimesCommitted++;
                    boolean success = random.nextInt(100) < 60;
                    if (success) {
                        long loot = (which == 0) ? 650L : (which == 1 ? 28_000L : 240_000L);
                        currentLife.bankBalance += loot;
                        currentLife.karma -= 15;
                        currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                                "🕵️ نفذت العملية بنجاح دون أن تترك أثراً وغنمت " + BitLifeArabicRTLFormatter.formatCurrency(loot) + "!"
                        ));
                    } else {
                        int years = (which == 0) ? 2 : (which == 1 ? 5 : 12);
                        currentLife.inPrison = true;
                        currentLife.prisonYearsLeft = years;
                        currentLife.occupationTitleArabic = "سجين";
                        currentLife.annualSalary = 0L;
                        currentLife.happiness -= 25;
                        currentLife.addLogEvent("🚓 ألقت الشرطة القبض عليك متلبساً! حكمت المحكمة بسجنك لمدة " + years + " سنوات.");
                    }
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_back), null)
                .show();
    }

    private void playLotteryOrCasino() {
        String[] opts = {
                "🎟️ شراء10 تذاكر يانصيب ($100) — الجائزة الكبرى $5,000,000",
                "🃏 طاولة البلاك جاك في الكازينو — رهان $1,000"
        };
        new MaterialAlertDialogBuilder(this)
                .setTitle("🎰 الكازينو واليانصيب")
                .setItems(opts, (d, which) -> {
                    if (which == 0) {
                        currentLife.bankBalance -= 100L;
                        if (random.nextInt(100) < 25) {
                            currentLife.bankBalance += 5_000_000L;
                            currentLife.happiness = 100;
                            currentLife.addLogEvent("🎉 يا للروعة! فزت بالجائزة الكبرى في اليانصيب بقيمة $5,000,000!");
                        } else {
                            currentLife.addLogEvent("اشتريت تذاكر اليانصيب بـ $100 ولم يحالفك الحظ هذه المرة.");
                        }
                    } else {
                        if (random.nextBoolean()) {
                            currentLife.bankBalance += 1000L;
                            currentLife.happiness += 8;
                            currentLife.addLogEvent("🃏 فزت على موزع الورق في لعبة Blackjack بـ $1,000!");
                        } else {
                            currentLife.bankBalance -= 1000L;
                            currentLife.happiness -= 5;
                            currentLife.addLogEvent("🃏 خسرت رهانك البالغ $1,000 على طاولة Blackjack.");
                        }
                    }
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showEmigrateDialog() {
        String[][] locs = engine.getCountriesAndCities();
        String[] labels = new String[locs.length];
        for (int i = 0; i < locs.length; i++) {
            labels[i] = locs[i][0] + " " + locs[i][2] + ", " + locs[i][1];
        }
        new MaterialAlertDialogBuilder(this)
                .setTitle("✈️ الهجرة إلى دولة أخرى (Emigrate)")
                .setItems(labels, (d, which) -> {
                    currentLife.countryFlag = locs[which][0];
                    currentLife.countryName = locs[which][1];
                    currentLife.cityName = locs[which][2];
                    currentLife.countriesEmigrated++;
                    currentLife.addLogEvent(BitLifeArabicRTLFormatter.protectBiDi(
                            "✈️ تمت الموافقة على طلب الهجرة الخاص بك! انتقلت للعيش في " + currentLife.cityName + ", " + currentLife.countryName + "."
                    ));
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_cancel), null)
                .show();
    }

    private void confirmSurrender() {
        new MaterialAlertDialogBuilder(this)
                .setTitle("🏳️ الاستسلام وإنهاء الحياة؟")
                .setMessage("هل أنت متأكد من رغبتك في إنهاء حياة " + currentLife.getFullName() + " الحالية والانتقال إلى شاشة الوفاة والأوسمة؟")
                .setPositiveButton("نعم، استسلام", (d, w) -> {
                    engine.triggerDeath(currentLife, "الاستسلام المبكر (Surrendered)");
                    saveManager.recordDeceasedInCemetery(currentLife);
                    refreshUI();
                    showDeathSummaryDialog();
                })
                .setNegativeButton(getString(R.string.btn_cancel), null)
                .show();
    }

    private void showDeathSummaryDialog() {
        String msg = "توفي " + currentLife.getFullName() + " عن عمر يناهز " + currentLife.age + " عاماً.\n"
                + "• سبب الوفاة: " + currentLife.causeOfDeathArabic + "\n"
                + "• صافي الثروة عند الوفاة: " + BitLifeArabicRTLFormatter.formatCurrency(currentLife.calculateNetWorth()) + "\n"
                + "• الوسام الممنوح (Ribbon): " + currentLife.earnedRibbonArabic;

        new MaterialAlertDialogBuilder(this)
                .setTitle("☠️ ارقد في سلام (R.I.P.)")
                .setMessage(BitLifeArabicRTLFormatter.protectBiDi(msg))
                .setPositiveButton("بدء حياة جديدة", (d, w) -> {
                    currentLife = engine.createNewRandomLife(null, null, null, -1);
                    refreshUI();
                })
                .setNeutralButton("إعادة نفس الشخصية", (d, w) -> {
                    currentLife = engine.createNewRandomLife(currentLife.firstName, currentLife.lastName, currentLife.genderArabic, -1);
                    refreshUI();
                })
                .show();
    }

    private void showMainMenuDialog() {
        String[] menuItems = {
                "🆕 " + getString(R.string.menu_new_random_life),
                "✨ " + getString(R.string.menu_custom_life),
                "🪦 " + getString(R.string.menu_cemetery) + " (" + saveManager.getCemeteryEntries().size() + ")",
                "🏅 " + getString(R.string.menu_ribbons) + " (" + saveManager.getUnlockedRibbons().size() + ")",
                "🛠️ " + getString(R.string.menu_apk_patcher)
        };

        new MaterialAlertDialogBuilder(this)
                .setTitle(getString(R.string.menu_title))
                .setItems(menuItems, (d, which) -> {
                    if (which == 0) {
                        currentLife = engine.createNewRandomLife(null, null, null, -1);
                        refreshUI();
                    } else if (which == 1) {
                        showCustomLifeDialog();
                    } else if (which == 2) {
                        List<String> cem = saveManager.getCemeteryEntries();
                        String body = cem.isEmpty() ? "لا توجد شخصيات راحلة في المقبرة بعد." : String.join("\n\n", cem);
                        new MaterialAlertDialogBuilder(this)
                                .setTitle("🪦 المقبرة وسجل الراحلين")
                                .setMessage(BitLifeArabicRTLFormatter.protectBiDi(body))
                                .setPositiveButton(getString(R.string.btn_ok), null)
                                .show();
                    } else if (which == 3) {
                        List<String> ribs = saveManager.getUnlockedRibbons();
                        String body = ribs.isEmpty() ? "لم تفتح أي أوسمة بعد. أكمل حياة كاملة للحصول على أول وسام!" : String.join("\n• ", ribs);
                        new MaterialAlertDialogBuilder(this)
                                .setTitle("🏅 الأوسمة المفتوحة (Ribbons)")
                                .setMessage(BitLifeArabicRTLFormatter.protectBiDi(body))
                                .setPositiveButton(getString(R.string.btn_ok), null)
                                .show();
                    } else if (which == 4) {
                        String report = OriginalApkPatcherInfo.inspectAndExportPatchFiles(this);
                        new MaterialAlertDialogBuilder(this)
                                .setTitle("🛠️ أداة استخراج وتعريب BitLife")
                                .setMessage(report)
                                .setPositiveButton(getString(R.string.btn_ok), null)
                                .show();
                    }
                })
                .setNegativeButton(getString(R.string.btn_close), null)
                .show();
    }

    private void showCustomLifeDialog() {
        int pad = (int) (18 * getResources().getDisplayMetrics().density);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(pad, pad / 2, pad, 0);

        EditText etFirst = new EditText(this);
        etFirst.setHint("الاسم الأول (مثال: John أو Sophia)");
        layout.addView(etFirst);

        EditText etLast = new EditText(this);
        etLast.setHint("اسم العائلة (مثال: Smith أو Martinez)");
        layout.addView(etLast);

        Spinner spGender = new Spinner(this);
        spGender.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new String[]{"ذكر", "أنثى"}));
        layout.addView(spGender);

        String[][] locs = engine.getCountriesAndCities();
        String[] locNames = new String[locs.length];
        for (int i = 0; i < locs.length; i++) {
            locNames[i] = locs[i][0] + " " + locs[i][2] + ", " + locs[i][1];
        }
        Spinner spCountry = new Spinner(this);
        spCountry.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, locNames));
        layout.addView(spCountry);

        new MaterialAlertDialogBuilder(this)
                .setTitle("✨ تخصيص حياة جديدة (Custom Life)")
                .setView(layout)
                .setPositiveButton("بدء الحياة", (d, w) -> {
                    currentLife = engine.createNewRandomLife(
                            etFirst.getText().toString(),
                            etLast.getText().toString(),
                            spGender.getSelectedItem().toString(),
                            spCountry.getSelectedItemPosition()
                    );
                    refreshUI();
                })
                .setNegativeButton(getString(R.string.btn_cancel), null)
                .show();
    }
}
