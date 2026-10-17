package com.candywriter.bitlife.models;

public class JobItem {
    public String titleArabic;
    public String companyName;
    public String categoryArabic;
    public long annualSalary;
    public int minSmarts;
    public boolean requiresUniversity;

    public JobItem() {}

    public JobItem(String titleArabic, String companyName, String categoryArabic, long annualSalary, int minSmarts, boolean requiresUniversity) {
        this.titleArabic = titleArabic;
        this.companyName = companyName;
        this.categoryArabic = categoryArabic;
        this.annualSalary = annualSalary;
        this.minSmarts = minSmarts;
        this.requiresUniversity = requiresUniversity;
    }
}
