"""
Retry failed downloads with improved strategies:
- Google Docs: Try drive.google.com/uc format + cookie handling
- infobooks.org: Try with Referer header
- Dead domains: Try Wayback Machine
"""

import os
import sys
import json
import hashlib
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime
from http.cookiejar import CookieJar

BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "pdfs" / "_downloads"
MANIFEST_FILE = BASE_DIR / "catalog" / "download_manifest.json"
RETRY_MANIFEST = BASE_DIR / "catalog" / "retry_manifest.json"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    if len(name) > 120:
        name = name[:120]
    return name


def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def extract_gdocs_id(url):
    """Extract file ID from various Google Docs URL formats."""
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None


def try_gdocs_download(url, dest_path):
    """Try multiple strategies for Google Docs/Drive downloads."""
    file_id = extract_gdocs_id(url)
    if not file_id:
        return False, 0, "Could not extract file ID"

    strategies = [
        f"https://drive.google.com/uc?export=download&id={file_id}",
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
        f"https://docs.google.com/uc?export=download&id={file_id}&confirm=t",
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
    ]

    for i, download_url in enumerate(strategies):
        try:
            # Use cookie jar for Google's confirmation cookies
            cj = CookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj),
                urllib.request.HTTPSHandler(context=SSL_CTX)
            )

            req = urllib.request.Request(download_url, headers={
                "User-Agent": USER_AGENT,
            })

            response = opener.open(req, timeout=60)
            content_type = response.headers.get('Content-Type', '')

            data = response.read()

            # Check if it's a PDF
            if data[:4] == b'%PDF' or data[:5] == b'%PDF-':
                with open(dest_path, 'wb') as f:
                    f.write(data)
                return True, len(data), None

            # Check for download warning page (virus scan for large files)
            if b'confirm=' in data or b'download_warning' in data:
                # Try to extract confirm token
                confirm_match = re.search(rb'confirm=([a-zA-Z0-9_-]+)', data)
                if confirm_match:
                    confirm = confirm_match.group(1).decode()
                    confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm}"
                    req2 = urllib.request.Request(confirm_url, headers={"User-Agent": USER_AGENT})
                    resp2 = opener.open(req2, timeout=60)
                    data2 = resp2.read()
                    if data2[:4] == b'%PDF':
                        with open(dest_path, 'wb') as f:
                            f.write(data2)
                        return True, len(data2), None

        except Exception as e:
            continue

        time.sleep(1)

    return False, 0, "All Google Drive download strategies failed"


def try_infobooks_download(url, dest_path):
    """Try downloading from infobooks.org with proper headers."""
    strategies = [
        {"User-Agent": USER_AGENT, "Referer": "https://www.infobooks.org/free-pdf-books/self-improvement/survival/"},
        {"User-Agent": USER_AGENT, "Referer": "https://www.infobooks.org/", "Accept": "application/pdf,*/*"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0", "Referer": "https://www.infobooks.org/"},
    ]

    for headers in strategies:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as response:
                data = response.read()
                if data[:4] == b'%PDF' or len(data) > 5000:
                    with open(dest_path, 'wb') as f:
                        f.write(data)
                    return True, len(data), None
        except Exception as e:
            last_error = str(e)
            continue
        time.sleep(1)

    return False, 0, f"All infobooks strategies failed: {last_error}"


def try_wayback_download(url, dest_path):
    """Try downloading from Wayback Machine for dead domains."""
    dead_domains = ['ready4itall.org', 'kazvswild.com', 'landsurvival.com', 'survivorlibrary.com']
    domain = urllib.parse.urlparse(url).netloc.replace('www.', '')

    if domain not in dead_domains:
        return False, 0, "Not a dead domain"

    try:
        wb_url = f"https://web.archive.org/web/2024/{url}"
        req = urllib.request.Request(wb_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=90) as response:
            data = response.read()
            if data[:4] == b'%PDF':
                with open(dest_path, 'wb') as f:
                    f.write(data)
                return True, len(data), None
            else:
                return False, 0, "Wayback returned non-PDF content"
    except Exception as e:
        return False, 0, f"Wayback failed: {e}"


def main():
    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)

    failures = manifest["failures"]
    print(f"Retrying {len(failures)} failed downloads...")

    # Load existing hashes for dedup
    seen_hashes = {}
    for item in manifest["items"]:
        seen_hashes[item["sha256"]] = item["filename"]

    retry_results = {
        "retry_date": datetime.now().isoformat(),
        "total_retried": len(failures),
        "newly_successful": 0,
        "still_failed": 0,
        "new_items": [],
        "remaining_failures": []
    }

    for i, fail in enumerate(failures, 1):
        url = fail["url"]
        title = fail["title"]
        source = fail["source"]
        filename = sanitize_filename(title) + ".pdf"
        dest_path = DOWNLOAD_DIR / filename

        print(f"[{i}/{len(failures)}] Retrying: {title}...")

        success = False
        file_size = 0
        error = ""

        if source == "scp-gdocs":
            success, file_size, error = try_gdocs_download(url, dest_path)
        elif source == "infobooks":
            success, file_size, error = try_infobooks_download(url, dest_path)
        elif "ready4itall.org" in url or "kazvswild.com" in url or "landsurvival.com" in url or "survivorlibrary.com" in url:
            success, file_size, error = try_wayback_download(url, dest_path)
        else:
            # Generic retry with better headers
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as response:
                    data = response.read()
                    if data[:4] == b'%PDF':
                        with open(dest_path, 'wb') as f:
                            f.write(data)
                        success = True
                        file_size = len(data)
                    else:
                        error = "Not a PDF"
            except Exception as e:
                error = str(e)

        if success:
            file_hash = sha256_file(dest_path)
            if file_hash in seen_hashes:
                print(f"  -> DUP of {seen_hashes[file_hash]}")
                os.remove(dest_path)
            else:
                seen_hashes[file_hash] = filename
                retry_results["newly_successful"] += 1
                retry_results["new_items"].append({
                    "filename": filename,
                    "title": title,
                    "source": source,
                    "original_url": url,
                    "sha256": file_hash,
                    "size_bytes": file_size
                })
                print(f"  -> OK ({file_size:,} bytes)")
        else:
            retry_results["still_failed"] += 1
            retry_results["remaining_failures"].append({
                "title": title,
                "url": url,
                "source": source,
                "error": error
            })
            print(f"  -> FAIL: {error[:80]}")

        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"RETRY COMPLETE")
    print(f"  Newly successful: {retry_results['newly_successful']}")
    print(f"  Still failed:     {retry_results['still_failed']}")
    print(f"{'='*60}")

    # Save retry manifest
    with open(RETRY_MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(retry_results, f, indent=2, ensure_ascii=False)

    # Update main manifest with new items
    manifest["items"].extend(retry_results["new_items"])
    manifest["successful"] += retry_results["newly_successful"]
    manifest["failed"] = retry_results["still_failed"]
    manifest["failures"] = retry_results["remaining_failures"]
    manifest["retry_date"] = retry_results["retry_date"]

    total_size = sum(item["size_bytes"] for item in manifest["items"])
    manifest["total_size_bytes"] = total_size
    manifest["total_size_mb"] = round(total_size / (1024 * 1024), 2)

    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated manifest: {manifest['successful']} successful, {manifest['failed']} failed")
    print(f"Total library size: {manifest['total_size_mb']} MB")


if __name__ == "__main__":
    main()
