package com.candywriter.bitlife.engine;

import java.text.NumberFormat;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Pure RTL & BiDi Formatter adhering to the Golden Rule:
 * - Keeps original Dollar currency ($) and Western numerals intact.
 * - Keeps original English proper names (John Smith, Los Angeles, United States) intact.
 * - Wraps LTR tokens in Unicode Left-to-Right Isolates (U+2066 ... U+2069) so they never flip inside Arabic RTL sentences.
 */
public class BitLifeArabicRTLFormatter {
    private static final Pattern LTR_TOKEN_PATTERN =
            Pattern.compile("(\\$[-]?[0-9,]+|[A-Za-z][A-Za-z0-9'\\-\\., ]*[A-Za-z0-9])");

    public static String formatCurrency(long amount) {
        NumberFormat nf = NumberFormat.getIntegerInstance(Locale.US);
        if (amount < 0) {
            return "\u2066-$" + nf.format(Math.abs(amount)) + "\u2069";
        }
        return "\u2066$" + nf.format(amount) + "\u2069";
    }

    public static String protectBiDi(String arabicText) {
        if (arabicText == null || arabicText.isEmpty()) return "";
        Matcher matcher = LTR_TOKEN_PATTERN.matcher(arabicText);
        StringBuffer sb = new StringBuffer();
        while (matcher.find()) {
            String token = matcher.group(1);
            matcher.appendReplacement(sb, "\u2066" + Matcher.quoteReplacement(token) + "\u2069");
        }
        matcher.appendTail(sb);
        return "\u2067" + sb.toString() + "\u2069";
    }
}
