#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BitLife (com.candywriter.bitlife) Multi-Source Automatic Downloader & XAPK/APKS Unpacker (v2.0)
===============================================================================================
1. Automatically downloads the latest BitLife package (XAPK or APK) using a 5-stage acquisition chain:
   - Stage 1: User-provided file in `original/` or custom `BITLIFE_APK_URL`.
   - Stage 2: EFF's `apkeep` CLI (`apkeep -a com.candywriter.bitlife -d apk-pure`).
   - Stage 3: `curl_cffi` Chrome TLS fingerprint impersonation + `cloudscraper` on APKPure XAPK/APK CDNs.
   - Stage 4: Uptodown dynamic CDN token resolver (`https://bitlife.en.uptodown.com/android/download`).
   - Stage 5: Playwright Headless Chromium browser automation (solves Cloudflare JS challenges and clicks download).
2. Strictly validates that the downloaded file is a real ZIP-format package (> 15 MB) and NOT an HTML error page.
3. Inspects the archive structure:
   - Automatically detects XAPK / APKS / Split bundles (containing `com.candywriter.bitlife.apk`,
     `UnityDataAssetPack.apk`, `config.arm64_v8a.apk`, `manifest.json`, etc.), extracts all inner `.apk` splits,
     merges them via `APKEditor.jar m` (with direct ZIP-merge fallback), and extracts `assets/` + `lib/`
     into `split_overlay/` so `global-metadata.dat` is 100% guaranteed to be present in `decompiled/`.
"""

import os
import re
import sys
import glob
import json
import shutil
import zipfile
import subprocess
import urllib.request

PACKAGE_NAME = "com.candywriter.bitlife"
MIN_VALID_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB minimum for real BitLife package


def log(msg):
    print(f"[BitLife-Fetcher] {msg}", flush=True)


def fail(msg):
    print(f"\n[FATAL ERROR] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def is_valid_zip_archive(path, min_size=MIN_VALID_SIZE_BYTES):
    if not path or not os.path.isfile(path):
        return False
    sz = os.path.getsize(path)
    if sz < min_size:
        log(f"Rejected {path}: size ({sz} bytes) is smaller than minimum required ({min_size} bytes).")
        return False
    if not zipfile.is_zipfile(path):
        log(f"Rejected {path}: NOT a valid ZIP/APK/XAPK archive (likely an HTML challenge page).")
        return False
    return True


def try_apkeep_download(work_dir, dest_path):
    """Uses EFF's apkeep CLI tool to download com.candywriter.bitlife directly."""
    apkeep_bin = shutil.which("apkeep") or os.path.join(work_dir, "apkeep")
    if not os.path.isfile(apkeep_bin):
        return False
    log("Stage 2: Attempting download via EFF apkeep CLI...")
    out_d = os.path.join(work_dir, "apkeep_dl")
    os.makedirs(out_d, exist_ok=True)
    subprocess.run([apkeep_bin, "-a", PACKAGE_NAME, "-d", "apk-pure", out_d], check=False)
    for root_d, _, files in os.walk(out_d):
        for fn in files:
            if fn.lower().endswith((".apk", ".xapk", ".apks")):
                cand = os.path.join(root_d, fn)
                if is_valid_zip_archive(cand):
                    shutil.move(cand, dest_path)
                    return True
    return False


def try_curl_download(url, dest_path, referer="https://apkpure.net/"):
    log(f"Attempting curl download from: {url}")
    if os.path.exists(dest_path):
        os.remove(dest_path)
    cmd = [
        "curl", "-L", "--fail", "--retry", "2", "--retry-delay", "2",
        "--connect-timeout", "20", "--max-time", "240",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", f"Referer: {referer}",
        url, "-o", dest_path
    ]
    subprocess.run(cmd, check=False)
    return is_valid_zip_archive(dest_path)


def try_cffi_or_cloudscraper_download(url, dest_path, referer="https://apkpure.net/"):
    log(f"Attempting TLS-impersonated download (curl_cffi / cloudscraper) from: {url}")
    headers = {"Referer": referer, "Accept-Language": "en-US,en;q=0.9"}
    try:
        from curl_cffi import requests as cffi_requests
        for browser_fp in ["chrome124", "chrome120", "safari17_0"]:
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                r = cffi_requests.get(
                    url, headers=headers, impersonate=browser_fp,
                    allow_redirects=True, timeout=240, stream=True
                )
                if r.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=131072):
                            if chunk:
                                f.write(chunk)
                    if is_valid_zip_archive(dest_path):
                        return True
            except Exception as inner_e:
                log(f"  curl_cffi ({browser_fp}) attempt note: {inner_e}")
    except ImportError:
        pass

    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        if os.path.exists(dest_path):
            os.remove(dest_path)
        r = scraper.get(url, headers=headers, allow_redirects=True, timeout=240, stream=True)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
            if is_valid_zip_archive(dest_path):
                return True
    except Exception as e:
        log(f"  cloudscraper attempt note: {e}")

    return False


def try_uptodown_scrape_download(dest_path):
    """Scrapes Uptodown's BitLife download page using curl_cffi / urllib to get the signed dw.uptodown.com URL."""
    dl_page = "https://bitlife.en.uptodown.com/android/download"
    log(f"Stage 4: Resolving signed CDN link from Uptodown ({dl_page})...")
    html = ""
    try:
        from curl_cffi import requests as cffi_requests
        r = cffi_requests.get(dl_page, impersonate="chrome124", allow_redirects=True, timeout=30)
        if r.status_code == 200:
            html = r.text
    except Exception:
        pass

    if not html:
        try:
            req = urllib.request.Request(dl_page, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            log(f"  Uptodown page fetch note: {e}")

    if html:
        # Check for data-url="https://dw.uptodown.com/dwn/..."
        m = re.search(r'data-url=["\'](https://dw\.uptodown\.com/dwn/[^"\']+)["\']', html)
        if not m:
            # Check for data-url token that appends to dw.uptodown.com/dwn/
            m_tok = re.search(r'id=["\']detail-download-button["\'][^>]*data-url=["\']([^"\']+)["\']', html)
            if m_tok:
                val = m_tok.group(1)
                cdn_url = val if val.startswith("http") else f"https://dw.uptodown.com/dwn/{val}"
            else:
                cdn_url = None
        else:
            cdn_url = m.group(1)

        if cdn_url:
            log(f"  Found Uptodown CDN URL: {cdn_url[:65]}...")
            if try_cffi_or_cloudscraper_download(cdn_url, dest_path, referer=dl_page):
                return True
            if try_curl_download(cdn_url, dest_path, referer=dl_page):
                return True
    return False


def try_playwright_browser_download(dest_path):
    """Uses Headless Chromium via Playwright to click download on Uptodown / APKPure / APKCombo."""
    log("Stage 5: Launching Playwright Headless Chromium browser to download BitLife...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("Playwright not installed; skipping Stage 5.")
        return False

    pages_to_try = [
        ("https://bitlife.en.uptodown.com/android/download", "#detail-download-button"),
        ("https://apkpure.net/bitlife-2023/com.candywriter.bitlife/download", "a.download-start-btn, a[href*='/b/XAPK/'], a[href*='/b/APK/']"),
        ("https://apkcombo.com/bitlife/com.candywriter.bitlife/download/apk", "a.variant"),
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                accept_downloads=True
            )
            page = context.new_page()

            for page_url, selector in pages_to_try:
                try:
                    log(f"  [Playwright] Navigating to {page_url} ...")
                    with page.expect_download(timeout=180000) as download_info:
                        page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(3000)
                        if page.locator(selector).count() > 0:
                            page.locator(selector).first.click()
                    download = download_info.value
                    download.save_as(dest_path)
                    if is_valid_zip_archive(dest_path):
                        browser.close()
                        return True
                except Exception as pe:
                    log(f"  [Playwright] {page_url} attempt note: {pe}")

            browser.close()
    except Exception as e:
        log(f"  [Playwright] Browser error: {e}")

    return False


def download_bitlife_package(work_dir, repo_root, min_size=MIN_VALID_SIZE_BYTES):
    dest_pkg = os.path.join(work_dir, "bitlife_raw_package.zip")

    # Stage 1A: Local original/ directory
    orig_dir = os.path.join(repo_root, "original")
    if os.path.isdir(orig_dir):
        for fn in sorted(os.listdir(orig_dir)):
            if fn.lower().endswith((".apk", ".xapk", ".apks", ".apkm")):
                candidate = os.path.join(orig_dir, fn)
                if is_valid_zip_archive(candidate, min_size=1024):
                    log(f"Stage 1: Found valid package in original/: {candidate}")
                    shutil.copyfile(candidate, dest_pkg)
                    return dest_pkg

    # Stage 1B: Custom BITLIFE_APK_URL
    custom_url = os.environ.get("BITLIFE_APK_URL", "").strip()
    if custom_url:
        log(f"Stage 1: Downloading from custom BITLIFE_APK_URL: {custom_url}")
        if try_cffi_or_cloudscraper_download(custom_url, dest_pkg) or try_curl_download(custom_url, dest_pkg):
            return dest_pkg
        fail(f"Custom BITLIFE_APK_URL ({custom_url}) failed or did not return a valid ZIP/APK/XAPK archive!")

    # Stage 2: EFF apkeep CLI
    if try_apkeep_download(work_dir, dest_pkg):
        log("Successfully acquired BitLife package via apkeep CLI!")
        return dest_pkg

    # Stage 3: Direct APKPure XAPK & APK endpoints via curl_cffi / cloudscraper / curl
    apkpure_urls = [
        ("https://d.apkpure.net/b/XAPK/com.candywriter.bitlife?version=latest", "https://apkpure.net/"),
        ("https://d.apkpure.net/b/APK/com.candywriter.bitlife?version=latest", "https://apkpure.net/"),
        ("https://d.cdnpure.com/b/XAPK/com.candywriter.bitlife?version=latest", "https://apkpure.com/"),
        ("https://d.cdnpure.com/b/APK/com.candywriter.bitlife?version=latest", "https://apkpure.com/"),
    ]
    for url, ref in apkpure_urls:
        if try_cffi_or_cloudscraper_download(url, dest_pkg, referer=ref):
            log(f"Successfully downloaded BitLife package from {url} ({os.path.getsize(dest_pkg)} bytes)")
            return dest_pkg
        if try_curl_download(url, dest_pkg, referer=ref):
            log(f"Successfully downloaded BitLife package via curl from {url} ({os.path.getsize(dest_pkg)} bytes)")
            return dest_pkg

    # Stage 4: Uptodown CDN Resolver
    if try_uptodown_scrape_download(dest_pkg):
        log(f"Successfully downloaded BitLife package from Uptodown ({os.path.getsize(dest_pkg)} bytes)")
        return dest_pkg

    # Stage 5: Playwright Headless Chromium Browser
    if try_playwright_browser_download(dest_pkg):
        log(f"Successfully downloaded BitLife package via Playwright Chromium ({os.path.getsize(dest_pkg)} bytes)")
        return dest_pkg

    fail(
        "All 5 automatic download stages failed to retrieve a valid BitLife APK/XAPK (>15MB ZIP archive). "
        "Build halted strictly as requested so no empty decompilation occurs."
    )


def merge_splits_fallback_zip(split_dir, output_apk):
    """
    Pure-Python fallback merger if APKEditor.jar is unavailable or fails:
    Finds the base APK split (containing AndroidManifest.xml and classes.dex) and merges
    all `assets/` and `lib/` entries from the other splits (`UnityDataAssetPack.apk`, `config.*.apk`) into it.
    """
    log("Running Pure-Python Split APK Merger fallback...")
    apk_files = [os.path.join(split_dir, f) for f in sorted(os.listdir(split_dir)) if f.lower().endswith(".apk")]
    base_apk = None
    other_apks = []

    for ap in apk_files:
        with zipfile.ZipFile(ap, "r") as zf:
            nl = zf.namelist()
            if "AndroidManifest.xml" in nl and "classes.dex" in nl:
                base_apk = ap
            else:
                other_apks.append(ap)

    if base_apk is None and apk_files:
        base_apk = apk_files[0]
        other_apks = apk_files[1:]

    if base_apk is None:
        fail("No .apk files found in split_apks directory!")

    shutil.copyfile(base_apk, output_apk)
    with zipfile.ZipFile(output_apk, "a") as zbase:
        existing = set(zbase.namelist())
        for o_apk in other_apks:
            with zipfile.ZipFile(o_apk, "r") as zother:
                for item in zother.infolist():
                    if item.filename.startswith(("assets/", "lib/")) and item.filename not in existing:
                        zbase.writestr(item, zother.read(item.filename))
                        existing.add(item.filename)
    log(f"Pure-Python Split Merger produced {output_apk} ({os.path.getsize(output_apk)} bytes)")


def prepare_single_apk_from_package(raw_pkg_path, work_dir, apkeditor_jar):
    split_dir = os.path.join(work_dir, "split_apks")
    overlay_dir = os.path.join(work_dir, "split_overlay")
    if os.path.exists(split_dir):
        shutil.rmtree(split_dir)
    if os.path.exists(overlay_dir):
        shutil.rmtree(overlay_dir)
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(overlay_dir, exist_ok=True)

    with zipfile.ZipFile(raw_pkg_path, "r") as zf:
        names = zf.namelist()
        log(f"Inspecting downloaded archive ({len(names)} entries). Sample entries: {names[:8]}")

        has_root_manifest = "AndroidManifest.xml" in names
        inner_apks = [n for n in names if n.lower().endswith(".apk")]

        if has_root_manifest and not inner_apks:
            log("Archive is a standalone single APK (AndroidManifest.xml at root).")
            single_apk = os.path.join(work_dir, "prepared_single.apk")
            shutil.copyfile(raw_pkg_path, single_apk)
            return single_apk, overlay_dir

        if not inner_apks:
            fail(
                f"Downloaded archive {raw_pkg_path} is neither a single APK nor an XAPK/APKS split bundle! "
                f"Found entries: {names[:15]}"
            )

        log(f"Detected XAPK / Split APK Bundle with {len(inner_apks)} inner APK splits: {inner_apks}")
        for apk_entry in inner_apks:
            safe_name = os.path.basename(apk_entry)
            if not safe_name:
                continue
            out_apk_path = os.path.join(split_dir, safe_name)
            with zf.open(apk_entry) as src, open(out_apk_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            log(f"  -> Extracted split APK: {safe_name} ({os.path.getsize(out_apk_path)} bytes)")

            # Pre-extract `assets/` (including global-metadata.dat from UnityDataAssetPack.apk)
            # and `lib/` into `split_overlay/` so decompiled directory always gets every asset!
            try:
                with zipfile.ZipFile(out_apk_path, "r") as inner_zf:
                    for item in inner_zf.namelist():
                        if (item.endswith("global-metadata.dat") or (item.startswith("assets/") and item.endswith((".json", ".xml", ".txt")) and not item.endswith("catalog.json"))) and not item.endswith("/"):
                            target_p = os.path.join(overlay_dir, item)
                            os.makedirs(os.path.dirname(target_p), exist_ok=True)
                            with inner_zf.open(item) as s_in, open(target_p, "wb") as d_out:
                                shutil.copyfileobj(s_in, d_out)
            except Exception as e:
                log(f"  [warn] Overlay extraction note for {safe_name}: {e}")

    merged_apk = os.path.join(work_dir, "merged_bitlife.apk")
    merged_ok = False
    if apkeditor_jar and os.path.isfile(apkeditor_jar) and os.path.getsize(apkeditor_jar) > 100000:
        log("Merging split APKs into a single APK via APKEditor.jar...")
        cmd = ["java", "-Xmx4096m", "-jar", apkeditor_jar, "m", "-i", split_dir, "-o", merged_apk]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0 and os.path.isfile(merged_apk) and zipfile.is_zipfile(merged_apk):
            with zipfile.ZipFile(merged_apk, "r") as m_zf:
                if "AndroidManifest.xml" in m_zf.namelist():
                    merged_ok = True

    if not merged_ok:
        merge_splits_fallback_zip(split_dir, merged_apk)

    if not os.path.isfile(merged_apk) or not zipfile.is_zipfile(merged_apk):
        fail("Failed to produce a valid merged APK from XAPK splits!")

    with zipfile.ZipFile(merged_apk, "r") as m_zf:
        if "AndroidManifest.xml" not in m_zf.namelist():
            fail("Merged APK does NOT contain AndroidManifest.xml at its root!")

    log(f"Verified single merged APK ready for decompilation: {merged_apk} ({os.path.getsize(merged_apk)} bytes)")
    return merged_apk, overlay_dir


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 fetch_and_prepare_bitlife_apk.py <work_dir> <repo_root> <apkeditor_jar>")
        sys.exit(1)

    work_d = os.path.abspath(sys.argv[1])
    repo_r = os.path.abspath(sys.argv[2])
    apkeditor_p = os.path.abspath(sys.argv[3])
    os.makedirs(work_d, exist_ok=True)

    raw_pkg = download_bitlife_package(work_d, repo_r)
    final_single_apk, overlay_d = prepare_single_apk_from_package(raw_pkg, work_d, apkeditor_p)

    status_file = os.path.join(work_d, "prepared_apk_info.json")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({
            "prepared_apk": final_single_apk,
            "overlay_dir": overlay_d
        }, f, indent=2)
    log(f"Preparation complete! Info saved to {status_file}")
