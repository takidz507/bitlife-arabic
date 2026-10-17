#!/usr/bin/env bash
set -e
echo "=================================================================="
echo " BitLife (com.candywriter.bitlife) Ultra Reverse-Engineering Tool"
echo "=================================================================="
WORK_DIR="$(pwd)/build_reverse_eng"
mkdir -p "$WORK_DIR"
INPUT_APK=""
if [ -f "original/bitlife.apk" ]; then
    INPUT_APK="$(pwd)/original/bitlife.apk"
    echo "[+] Found user-provided original/bitlife.apk"
elif [ -f "original/bitlife.xapk" ]; then
    INPUT_APK="$(pwd)/original/bitlife.xapk"
    echo "[+] Found user-provided original/bitlife.xapk"
elif [ -n "$BITLIFE_APK_URL" ]; then
    echo "[+] Downloading BitLife APK from BITLIFE_APK_URL..."
    curl -L --fail -A "Mozilla/5.0" "$BITLIFE_APK_URL" -o "$WORK_DIR/downloaded.apk" && INPUT_APK="$WORK_DIR/downloaded.apk" || true
else
    echo "[+] Attempting automatic fetch of latest com.candywriter.bitlife APK..."
    curl -L --max-time 45 -A "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0" "https://d.apkpure.net/b/APK/com.candywriter.bitlife?version=latest" -o "$WORK_DIR/downloaded.apk" 2>/dev/null || true
    if [ -f "$WORK_DIR/downloaded.apk" ] && [ $(stat -c%s "$WORK_DIR/downloaded.apk" 2>/dev/null || echo 0) -gt 5000000 ]; then
        INPUT_APK="$WORK_DIR/downloaded.apk"
        echo "[+] Successfully downloaded official BitLife package"
    fi
fi
if [ -z "$INPUT_APK" ] || [ ! -f "$INPUT_APK" ]; then
    echo "[i] No external binary APK found or mirror required CAPTCHA; using Gradle-built Arabic BitLife APK."
    exit 0
fi
echo "[+] Preparing Apktool v2.9.3 & APKEditor v1.3.9..."
curl -sL "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar" -o "$WORK_DIR/apktool.jar"
curl -sL "https://github.com/REAndroid/APKEditor/releases/download/V1.3.9/APKEditor-1.3.9.jar" -o "$WORK_DIR/APKEditor.jar"
TARGET_APK="$INPUT_APK"
if unzip -l "$INPUT_APK" | grep -q "base.apk"; then
    echo "[+] Detected Split APK Bundle (XAPK/APKS). Merging splits via APKEditor..."
    java -jar "$WORK_DIR/APKEditor.jar" m -i "$INPUT_APK" -o "$WORK_DIR/merged_bitlife.apk"
    TARGET_APK="$WORK_DIR/merged_bitlife.apk"
fi
echo "[+] Step 1/4: Decompiling BitLife APK via Apktool..."
java -Xmx3072m -jar "$WORK_DIR/apktool.jar" d -f "$TARGET_APK" -o "$WORK_DIR/decompiled"
echo "[+] Step 2/4: Running Binary IL2CPP (global-metadata.dat) & Resource Arabic Localization..."
python3 tools/reverse_engineer_bitlife_apk.py "$WORK_DIR/decompiled"
echo "[+] Step 3/4: Rebuilding Modified Arabic BitLife APK..."
java -Xmx3072m -jar "$WORK_DIR/apktool.jar" b --use-aapt2 "$WORK_DIR/decompiled" -o "$WORK_DIR/bitlife-arabic-unaligned.apk"
echo "[+] Step 4/4: Zipaligning & Signing APK (V1 + V2 + V3)..."
BUILD_TOOLS_DIR="$ANDROID_HOME/build-tools/34.0.0"
"$BUILD_TOOLS_DIR/zipalign" -p -f 4 "$WORK_DIR/bitlife-arabic-unaligned.apk" "$WORK_DIR/bitlife-arabic-aligned.apk"
if [ ! -f "$WORK_DIR/debug.keystore" ]; then
    keytool -genkey -v -keystore "$WORK_DIR/debug.keystore" -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi
mkdir -p app/build/outputs/apk/debug
"$BUILD_TOOLS_DIR/apksigner" sign --ks "$WORK_DIR/debug.keystore" --ks-pass pass:android --key-pass pass:android --out app/build/outputs/apk/debug/app-debug.apk "$WORK_DIR/bitlife-arabic-aligned.apk"
echo "[SUCCESS] Patched & Signed Original BitLife Arabic APK -> app/build/outputs/apk/debug/app-debug.apk"
