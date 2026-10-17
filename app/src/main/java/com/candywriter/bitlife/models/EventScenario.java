package com.candywriter.bitlife.models;

public class EventScenario {
    public String titleArabic;
    public String descriptionArabic;
    public String option1Text;
    public String option2Text;
    public String option3Text;

    public String outcome1Text;
    public String outcome2Text;
    public String outcome3Text;

    public int[] deltaHappiness;
    public int[] deltaHealth;
    public int[] deltaSmarts;
    public int[] deltaLooks;
    public int[] deltaKarma;
    public long[] deltaMoney;

    public EventScenario(
            String titleArabic,
            String descriptionArabic,
            String option1Text, String outcome1Text, int dHap1, int dHlt1, int dSmt1, int dLks1, int dKrm1, long dMon1,
            String option2Text, String outcome2Text, int dHap2, int dHlt2, int dSmt2, int dLks2, int dKrm2, long dMon2,
            String option3Text, String outcome3Text, int dHap3, int dHlt3, int dSmt3, int dLks3, int dKrm3, long dMon3
    ) {
        this.titleArabic = titleArabic;
        this.descriptionArabic = descriptionArabic;
        this.option1Text = option1Text;
        this.option2Text = option2Text;
        this.option3Text = option3Text;
        this.outcome1Text = outcome1Text;
        this.outcome2Text = outcome2Text;
        this.outcome3Text = outcome3Text;
        this.deltaHappiness = new int[]{dHap1, dHap2, dHap3};
        this.deltaHealth = new int[]{dHlt1, dHlt2, dHlt3};
        this.deltaSmarts = new int[]{dSmt1, dSmt2, dSmt3};
        this.deltaLooks = new int[]{dLks1, dLks2, dLks3};
        this.deltaKarma = new int[]{dKrm1, dKrm2, dKrm3};
        this.deltaMoney = new long[]{dMon1, dMon2, dMon3};
    }
}
