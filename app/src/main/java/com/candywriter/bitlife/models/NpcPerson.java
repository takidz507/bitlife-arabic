package com.candywriter.bitlife.models;

public class NpcPerson {
    public String id;
    public String fullName;
    public String roleArabic;
    public String occupationArabic;
    public int age;
    public int relationship;
    public boolean isAlive = true;
    public boolean isPartner = false;
    public boolean isMarried = false;
    public boolean hasPrenup = false;

    public NpcPerson() {}

    public NpcPerson(String id, String fullName, String roleArabic, String occupationArabic, int age, int relationship) {
        this.id = id;
        this.fullName = fullName;
        this.roleArabic = roleArabic;
        this.occupationArabic = occupationArabic;
        this.age = age;
        this.relationship = relationship;
    }
}
