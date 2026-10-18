#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

echo "========================================================================"
echo " BitLife (com.candywriter.bitlife) Strict Reverse-Engineering Pipeline "
echo " (v4.0 - 3-Stage SHA-256 Audit + Unconditional Injection + Canary Gate)"
echo "========================================================================"

REPO_ROOT="$(pwd)"
WORK_DIR="$REPO_ROOT/build_reverse_eng"
mkdir -p "$WORK_DIR"

echo "[+] Step 0/6: Installing Lightweight Downloader & Reverse-Engineering Tools..."
pip3 install --quiet curl_cffi cloudscraper || true

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

echo "[+] Step 1/6: Acquiring & Unpacking Official BitLife Package (APK / XAPK)..."
python3 -u "$REPO_ROOT/tools/fetch_and_prepare_bitlife_apk.py" "$WORK_DIR" "$REPO_ROOT" "$WORK_DIR/APKEditor.jar"

if [ ! -f "$WORK_DIR/prepared_apk_info.json" ]; then
    echo "[FATAL ERROR] prepared_apk_info.json was not generated! Halting build." >&2
    exit 1
fi

TARGET_APK=$(python3 -c "import json; print(json.load(open('$WORK_DIR/prepared_apk_info.json'))['prepared_apk'])")
OVERLAY_DIR=$(python3 -c "import json; print(json.load(open('$WORK_DIR/prepared_apk_info.json'))['overlay_dir'])")

# Free intermediate raw download and split_apks to maximize available RAM & disk
rm -rf "$WORK_DIR/bitlife_raw_package.zip" "$WORK_DIR/split_apks"

if [ ! -f "$TARGET_APK" ]; then
    echo "[FATAL ERROR] Prepared single APK ($TARGET_APK) does not exist!" >&2
    exit 1
fi

echo "[+] Step 2/6: Decompiling BitLife APK via Apktool (-s / --no-src for fast resource & IL2CPP access)..."
rm -rf "$WORK_DIR/decompiled"
java -Xmx4096m -jar "$WORK_DIR/apktool.jar" d -f -s "$TARGET_APK" -o "$WORK_DIR/decompiled"

if [ ! -f "$WORK_DIR/decompiled/AndroidManifest.xml" ]; then
    echo "[FATAL ERROR] Decompilation failed: AndroidManifest.xml is missing in $WORK_DIR/decompiled!" >&2
    ls -la "$WORK_DIR/decompiled" || true
    exit 1
fi

# Ensure global-metadata.dat from OVERLAY_DIR is placed in decompiled/ before taking BEFORE hash
CANONICAL_META="$WORK_DIR/decompiled/assets/bin/Data/Managed/Metadata/global-metadata.dat"
if [ -n "$OVERLAY_DIR" ] && [ -f "$OVERLAY_DIR/assets/bin/Data/Managed/Metadata/global-metadata.dat" ]; then
    mkdir -p "$(dirname "$CANONICAL_META")"
    cp -f "$OVERLAY_DIR/assets/bin/Data/Managed/Metadata/global-metadata.dat" "$CANONICAL_META"
fi

if [ ! -f "$CANONICAL_META" ]; then
    FOUND_META=$(find "$WORK_DIR/decompiled" -name "global-metadata.dat" | head -n 1 || true)
    if [ -z "$FOUND_META" ]; then
        echo "[FATAL ERROR] global-metadata.dat not found in $WORK_DIR/decompiled or $OVERLAY_DIR!" >&2
        exit 1
    fi
    mkdir -p "$(dirname "$CANONICAL_META")"
    cp -f "$FOUND_META" "$CANONICAL_META"
fi

SHA256_BEFORE=$(sha256sum "$CANONICAL_META" | awk '{print $1}')
echo "$SHA256_BEFORE" > "$WORK_DIR/sha256_before.txt"
echo "========================================================================"
echo " [SHA-256 CHECK 1/3 - BEFORE PATCHING]"
echo " File:   $CANONICAL_META ($(stat -c%s "$CANONICAL_META") bytes)"
echo " SHA256: $SHA256_BEFORE"
echo "========================================================================"

echo "[+] Step 3/6: Applying v4.0 Batch-Streaming Binary IL2CPP (global-metadata.dat) & Resource Localization..."
PATCHED_META_COPY="$WORK_DIR/global-metadata.patched.dat"
python3 -u "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" "$WORK_DIR/decompiled" "$OVERLAY_DIR" "$PATCHED_META_COPY"

if [ ! -f "$PATCHED_META_COPY" ]; then
    echo "[FATAL ERROR] Patched metadata copy ($PATCHED_META_COPY) was not created!" >&2
    exit 1
fi

SHA256_AFTER=$(sha256sum "$PATCHED_META_COPY" | awk '{print $1}')
echo "$SHA256_AFTER" > "$WORK_DIR/sha256_after.txt"
echo "========================================================================"
echo " [SHA-256 CHECK 2/3 - AFTER PATCHING]"
echo " File:   $PATCHED_META_COPY ($(stat -c%s "$PATCHED_META_COPY") bytes)"
echo " SHA256: $SHA256_AFTER"
echo "========================================================================"

if [ "$SHA256_BEFORE" = "$SHA256_AFTER" ]; then
    echo "[FATAL ERROR] SHA-256 did NOT change after patching ($SHA256_BEFORE == $SHA256_AFTER)!" >&2
    exit 1
fi

echo "[+] Step 4/6: Rebuilding Modified Arabic BitLife APK & Force-Injecting Patched global-metadata.dat..."
UNALIGNED_APK="$WORK_DIR/bitlife-arabic-unaligned.apk"
if ! java -Xmx4096m -jar "$WORK_DIR/apktool.jar" b --use-aapt2 "$WORK_DIR/decompiled" -o "$UNALIGNED_APK"; then
    echo "[!] apktool b --use-aapt2 encountered split-resource conflict; using Direct ZIP Binary Injector fallback..."
    python3 -u "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" --inject-zip "$TARGET_APK" "$WORK_DIR/decompiled" "$UNALIGNED_APK"
fi

# Unconditionally force-inject the verified patched global-metadata.dat into UNALIGNED_APK (ZIP_STORED)
# so apktool b can NEVER drop, compress, or overwrite it with an unpatched copy!
python3 -u "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" --force-inject-metadata "$UNALIGNED_APK" "$PATCHED_META_COPY"

rm -rf "$WORK_DIR/decompiled" "$TARGET_APK"

if [ ! -f "$UNALIGNED_APK" ] || [ $(stat -c%s "$UNALIGNED_APK") -lt 10000000 ]; then
    echo "[FATAL ERROR] Rebuilt APK ($UNALIGNED_APK) is missing or invalid!" >&2
    exit 1
fi

echo "[+] Step 5/6: Zipaligning & Signing APK (V1 + V2 + V3)..."
BUILD_TOOLS_DIR="$ANDROID_HOME/build-tools/34.0.0"
ALIGNED_APK="$WORK_DIR/bitlife-arabic-aligned.apk"
"$BUILD_TOOLS_DIR/zipalign" -p -f 4 "$UNALIGNED_APK" "$ALIGNED_APK"
rm -f "$UNALIGNED_APK"

if [ ! -f "$ALIGNED_APK" ]; then
    echo "[FATAL ERROR] zipalign failed to produce $ALIGNED_APK!" >&2
    exit 1
fi

if [ ! -f "$WORK_DIR/debug.keystore" ]; then
    keytool -genkey -v -keystore "$WORK_DIR/debug.keystore" -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
fi

FINAL_APK="$REPO_ROOT/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p "$(dirname "$FINAL_APK")"
rm -f "$FINAL_APK"
"$BUILD_TOOLS_DIR/apksigner" sign --ks "$WORK_DIR/debug.keystore" --ks-pass pass:android --key-pass pass:android --out "$FINAL_APK" "$ALIGNED_APK"
"$BUILD_TOOLS_DIR/apksigner" verify "$FINAL_APK"
rm -f "$ALIGNED_APK"

if [ ! -f "$FINAL_APK" ]; then
    echo "[FATAL ERROR] Final signed APK ($FINAL_APK) was not created!" >&2
    exit 1
fi

echo "[+] Step 6/6: Running SHA-256 Check 3/3 & Canary Gate ('العمر') on Final Signed APK..."
python3 -u "$REPO_ROOT/tools/reverse_engineer_bitlife_apk.py" --verify-apk-canary "$FINAL_APK" "$SHA256_AFTER" "$SHA256_BEFORE"

echo "========================================================================"
echo " [SUCCESS] Canary-Verified Signed Arabic BitLife APK Ready:"
echo " $FINAL_APK ($(stat -c%s "$FINAL_APK") bytes)"
echo "========================================================================"
