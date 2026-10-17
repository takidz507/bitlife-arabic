package com.candywriter.bitlife.models;

public class AssetItem {
    public String id;
    public String name;
    public String categoryArabic;
    public long purchasePrice;
    public long currentValue;
    public int condition;
    public boolean isHaunted;
    public boolean isRentedOut;
    public long monthlyRent;

    public AssetItem() {}

    public AssetItem(String id, String name, String categoryArabic, long price, int condition, boolean isHaunted) {
        this.id = id;
        this.name = name;
        this.categoryArabic = categoryArabic;
        this.purchasePrice = price;
        this.currentValue = price;
        this.condition = condition;
        this.isHaunted = isHaunted;
        this.isRentedOut = false;
        this.monthlyRent = Math.max(250, price / 120);
    }
}
