package com.candywriter.bitlife;

import android.app.Application;
import android.content.res.Configuration;

import java.util.Locale;

public class BitLifeApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        enforceArabicRtlLocale();
    }

    private void enforceArabicRtlLocale() {
        Locale locale = new Locale("ar");
        Locale.setDefault(locale);
        Configuration config = getResources().getConfiguration();
        config.setLocale(locale);
        config.setLayoutDirection(locale);
        getResources().updateConfiguration(config, getResources().getDisplayMetrics());
    }
}
