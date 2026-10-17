#!/usr/bin/env bash
set -euo pipefail

echo "========================================================================"
echo " BitLife (com.candywriter.bitlife) Strict Reverse-Engineering Pipeline "
echo "========================================================================"

REPO_ROOT="$(pwd)"
WORK_DIR="$REPO_ROOT/build_reverse_eng"
mkdir -p "$WORK_DIR"

echo "[+] Step 0/5: Installing Downloader Dependencies & Reverse-Engineering Tools..."
pip3 install --quiet curl_cffi cloudscraper playwright || true
playwright install chromium 2>/dev/null || true

# Download Apktool v2.9.3
curl -sL --fail --retry 3 "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar" -o "$WORK_DIR/apktool.jar"
if [ ! -f "$WORK_DIR/apktool.jar" ] || [ $(stat -c%s "$WORK_DIR/apktool.jar") -lt 5000000 ]; then
    echo "[FATAL ERROR] Failed to download a valid apktool.jar!" >&2
    exit 1
fi

# Download APKEditor (for XAPK / Split APK merging)
curl -sL --retry 3 "https://github.com/REAndroid/APKEditor/releases/download/V1.3.9/APKEditor-1.3.9.jar" -o "$WORK_DIR/APKEditor.jar" || true
if [ ! -f "$WORK_DIR/APKEditor.jar" ] || [ $(stat -c%s "$WORK_DIR/APKEditor.jar" 2>/dev/null || echo 0) -lt 100000 ]; then
    APKEDITOR_URL=$(curl -sL https://api.github.com/repos/REAndroid/APKEditor/releases/latest | python3 -c "import sys, json; data=json.load(sys.stdin); print(next((a['browser_download_url'] for a in data.get('assets', []) if a['name'].endswith('.jar')), ''))" 2>/dev/null || true)
    if [ -n "$APKEDITOR_URL" ]; then
        curl -sL "$APKEDITOR_URL" -o "$WORK_DIR/APKEditor.jar" || true
    fi
fi

# Download EFF apkeep CLI binary if available
APKEEP_URL=$(curl -sL https://api.github.com/repos/EFForg/apkeep/releases/latest | python3 -c "import sys, json; data=json.load(sys.stdin); print(next((a['browser_download_url'] for a in data.get('assets', []) if 'x86_64-unknown-linux-gnu' in a['name']), ''))" 2>/dev/null || true)
if [ -n "$APKEEP_URL" ]; then
    curl -sL "$APKEEP_URL" -o "$WORK_DIR/apkeep" && chmod +x "$WORK_DIR/apkeep" || true
fi

echo "[+] Step 1/5: Acquiring & Unpacking Official BitLife Package (APK / XAPK)..."
python3 "$REPO_ROOT/tools/fetch_and_prepare_bitlife_apk.py" "$WORK_DIR" "$REPO_ROOT" "$WORK_DIR/APKEditor.jar"

if [ ! -f "$WORK_DIR/prepared_apk_info.json" ]; then
    echo "[FATAL ERROR] prepared_apk_info.json was not generated! Halting build." >&2
    exit 1
fi

TARGET_APK=$(python3 -c "import json; print(json.load(open('$WORK_DIR/prepared_apk_info.json'))['prepared_apk'])")
OVERLAY_DIR=$(python3 -c "import json; print(json.load(open('$WORK_DIR/prepared_apk_info.json'))['overlay_dir'])")

if [ ! -f "$TARGET_APK" ]; then
    echo "[FATAL ERROR] Prepared single APK ($TARGET_APK) does not exist!" >&2
    exit 1
fi

echo "[+] Step 2/5: Decompiling BitLife APK via Apktool (-s / --no-src for fast resource & IL2CPP access)..."
rm -rf "$WORK_DIR/decompiled"
java -Xmx4096m -jar "$WORK_DIR/apktool.jar" d -f -s "$TARGET_APK" -o "$WORK_DIR/decompiled"

# STRICT CHECK: Verify AndroidManifest.xml exists in decompiled directory
if [ ! -f "$WORK_DIR/decompiled/AndroidManifest.xml" ]; then
    echo "[FATAL ERROR] Decompilation failed: AndroidManifest.xml is missing in $WORK_DIR/decompiled!" >&2
    ls -la "$WORK_DIR/decompiled" || true
    exit 1
fi

echo "[+] Step 3/5: Applying Binary IL2CPP (global-metadata.dat) & Resource Arabic Localization..."
python3 "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" "$WORK_DIR/decompiled" "$OVERLAY_DIR"

echo "[+] Step 4/5: Rebuilding Modified Arabic BitLife APK..."
UNALIGNED_APK="$WORK_DIR/bitlife-arabic-unaligned.apk"
if ! java -Xmx4096m -jar "$WORK_DIR/apktool.jar" b --use-aapt2 "$WORK_DIR/decompiled" -o "$UNALIGNED_APK"; then
    echo "[!] apktool b --use-aapt2 encountered split-resource conflict; using Direct ZIP Binary Injector fallback..."
    python3 "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" --inject-zip "$TARGET_APK" "$WORK_DIR/decompiled" "$UNALIGNED_APK"
fi

if [ ! -f "$UNALIGNED_APK" ] || [ $(stat -c%s "$UNALIGNED_APK") -lt 10000000 ]; then
    echo "[FATAL ERROR] Rebuilt APK ($UNALIGNED_APK) is missing or invalid!" >&2
    exit 1
fi

echo "[+] Step 5/5: Zipaligning & Signing APK (V1 + V2 + V3)..."
BUILD_TOOLS_DIR="$ANDROID_HOME/build-tools/34.0.0"
ALIGNED_APK="$WORK_DIR/bitlife-arabic-aligned.apk"
"$BUILD_TOOLS_DIR/zipalign" -p -f 4 "$UNALIGNED_APK" "$ALIGNED_APK"

if [ ! -f "$ALIGNED_APK" ]; then
    echo "[FATAL ERROR] zipalign failed to produce $ALIGNED_APK!" >&2
    exit 1
fi

if [ ! -f "$WORK_DIR/debug.keystore" ]; then
    keytool -genkey -v -keystore "$WORK_DIR/debug.keystore" -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi

FINAL_APK="$REPO_ROOT/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p "$(dirname "$FINAL_APK")"
"$BUILD_TOOLS_DIR/apksigner" sign --ks "$WORK_DIR/debug.keystore" --ks-pass pass:android --key-pass pass:android --out "$FINAL_APK" "$ALIGNED_APK"
"$BUILD_TOOLS_DIR/apksigner" verify "$FINAL_APK"

if [ ! -f "$FINAL_APK" ]; then
    echo "[FATAL ERROR] Final signed APK ($FINAL_APK) was not created!" >&2
    exit 1
fi

echo "========================================================================"
echo " [SUCCESS] Signed Arabic BitLife APK Ready: $FINAL_APK ($(stat -c%s "$FINAL_APK") bytes)"
echo "========================================================================"
