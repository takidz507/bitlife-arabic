package com.candywriter.bitlife.utils;

import android.content.Context;
import android.content.SharedPreferences;

import com.candywriter.bitlife.models.CharacterState;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.lang.reflect.Type;
import java.util.ArrayList;
import java.util.List;

public class SaveGameManager {
    private static final String PREFS_NAME = "bitlife_arabic_saves_v1";
    private static final String KEY_ACTIVE_LIFE = "active_life_json";
    private static final String KEY_CEMETERY = "cemetery_list_json";
    private static final String KEY_RIBBONS = "unlocked_ribbons_json";

    private final SharedPreferences prefs;
    private final Gson gson = new Gson();

    public SaveGameManager(Context context) {
        this.prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    public void saveActiveLife(CharacterState state) {
        if (state == null) return;
        prefs.edit().putString(KEY_ACTIVE_LIFE, gson.toJson(state)).apply();
    }

    public CharacterState loadActiveLife() {
        String json = prefs.getString(KEY_ACTIVE_LIFE, null);
        if (json == null || json.isEmpty()) return null;
        try {
            return gson.fromJson(json, CharacterState.class);
        } catch (Exception e) {
            return null;
        }
    }

    public void recordDeceasedInCemetery(CharacterState state) {
        if (state == null) return;
        List<String> list = getCemeteryEntries();
        String entry = state.countryFlag + " " + state.getFullName() + " (" + state.age + " سنة) — "
                + state.causeOfDeathArabic + " | الوسام: " + state.earnedRibbonArabic;
        if (!list.contains(entry)) {
            list.add(0, entry);
            prefs.edit().putString(KEY_CEMETERY, gson.toJson(list)).apply();
        }
        if (state.earnedRibbonArabic != null && !state.earnedRibbonArabic.isEmpty()) {
            List<String> ribbons = getUnlockedRibbons();
            if (!ribbons.contains(state.earnedRibbonArabic)) {
                ribbons.add(state.earnedRibbonArabic);
                prefs.edit().putString(KEY_RIBBONS, gson.toJson(ribbons)).apply();
            }
        }
    }

    public List<String> getCemeteryEntries() {
        String json = prefs.getString(KEY_CEMETERY, null);
        if (json == null || json.isEmpty()) return new ArrayList<>();
        try {
            Type t = new TypeToken<ArrayList<String>>() {}.getType();
            List<String> list = gson.fromJson(json, t);
            return list != null ? list : new ArrayList<>();
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }

    public List<String> getUnlockedRibbons() {
        String json = prefs.getString(KEY_RIBBONS, null);
        if (json == null || json.isEmpty()) return new ArrayList<>();
        try {
            Type t = new TypeToken<ArrayList<String>>() {}.getType();
            List<String> list = gson.fromJson(json, t);
            return list != null ? list : new ArrayList<>();
        } catch (Exception e) {
            return new ArrayList<>();
        }
    }
}
