package com.candywriter.bitlife.models;

import java.util.ArrayList;
import java.util.List;

public class CharacterState {
    public String firstName = "John";
    public String lastName = "Smith";
    public String genderArabic = "ذكر";
    public String countryFlag = "🇺🇸";
    public String countryName = "United States";
    public String cityName = "Los Angeles";
    public String birthMonthDay = "October 17";
    public String zodiacArabic = "الميزان (Libra)";

    public int age = 0;
    public long bankBalance = 0L;
    public long annualSalary = 0L;
    public String occupationTitleArabic = "رضيع";
    public String employerName = "";

    public int happiness = 90;
    public int health = 92;
    public int smarts = 78;
    public int looks = 82;
    public int fame = 0;
    public int karma = 60;

    public boolean graduatedHighSchool = false;
    public boolean inUniversity = false;
    public boolean graduatedUniversity = false;
    public String universityMajorArabic = "";

    public boolean inPrison = false;
    public int prisonYearsLeft = 0;
    public int crimesCommitted = 0;
    public int prisonEscapes = 0;
    public int countriesEmigrated = 0;

    public boolean isAlive = true;
    public String causeOfDeathArabic = "";
    public String earnedRibbonArabic = "";

    public List<NpcPerson> relationships = new ArrayList<>();
    public List<AssetItem> assets = new ArrayList<>();
    public List<String> heirlooms = new ArrayList<>();
    public List<LifeYearLog> lifeLogs = new ArrayList<>();

    public static class LifeYearLog {
        public int age;
        public List<String> events = new ArrayList<>();

        public LifeYearLog() {}

        public LifeYearLog(int age) {
            this.age = age;
        }
    }

    public String getFullName() {
        return firstName + " " + lastName;
    }

    public long calculateNetWorth() {
        long total = bankBalance;
        for (AssetItem a : assets) {
            total += a.currentValue;
        }
        return total;
    }

    public void clampStats() {
        happiness = Math.max(0, Math.min(100, happiness));
        health = Math.max(0, Math.min(100, health));
        smarts = Math.max(0, Math.min(100, smarts));
        looks = Math.max(0, Math.min(100, looks));
        fame = Math.max(0, Math.min(100, fame));
        karma = Math.max(0, Math.min(100, karma));
    }

    public void addLogEvent(String eventText) {
        if (lifeLogs.isEmpty() || lifeLogs.get(lifeLogs.size() - 1).age != this.age) {
            lifeLogs.add(new LifeYearLog(this.age));
        }
        lifeLogs.get(lifeLogs.size() - 1).events.add(eventText);
    }
}
