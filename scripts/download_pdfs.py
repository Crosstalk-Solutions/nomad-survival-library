"""
NOMAD Survival Library - PDF Downloader
Downloads all PDFs from master URL list, deduplicates by SHA-256 hash,
and generates a download manifest.
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

# Add scripts dir to path for import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_urls import get_all_urls

# Directories
BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "pdfs" / "_downloads"
MANIFEST_FILE = BASE_DIR / "catalog" / "download_manifest.json"
LOG_FILE = BASE_DIR / "catalog" / "download_log.txt"

# Create SSL context that doesn't verify (some old sites have bad certs)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# User agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def sanitize_filename(name):
    """Create a safe filename from a title."""
    # Remove/replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')
    # Truncate to reasonable length
    if len(name) > 120:
        name = name[:120]
    return name


def convert_gdocs_url(url):
    """Convert Google Docs/Drive URL to direct download URL."""
    # Format: https://docs.google.com/open?id=XXXXX
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://docs.google.com/uc?export=download&id={file_id}"

    # Format: https://docs.google.com/file/d/XXXXX/edit
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://docs.google.com/uc?export=download&id={file_id}"

    return url


def sha256_file(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def download_file(url, dest_path, max_retries=2):
    """Download a file with retries. Returns (success, filesize, error_msg)."""
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as response:
                content_type = response.headers.get('Content-Type', '')

                # Check if Google is asking for confirmation (large file warning)
                if 'text/html' in content_type and 'docs.google.com' in url:
                    # Read and check for confirmation page
                    data = response.read()
                    # Try to find direct download link in HTML
                    confirm_match = re.search(rb'confirm=([a-zA-Z0-9_-]+)', data)
                    if confirm_match:
                        confirm_code = confirm_match.group(1).decode()
                        new_url = url + f"&confirm={confirm_code}"
                        req2 = urllib.request.Request(new_url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(req2, context=SSL_CTX, timeout=60) as resp2:
                            with open(dest_path, 'wb') as f:
                                data2 = resp2.read()
                                f.write(data2)
                                return True, len(data2), None
                    else:
                        # It might still be the actual PDF despite content-type header
                        # Check if data starts with PDF magic bytes
                        if data[:4] == b'%PDF':
                            with open(dest_path, 'wb') as f:
                                f.write(data)
                            return True, len(data), None
                        else:
                            # Save the HTML anyway for debugging, but mark as failed
                            return False, 0, f"Got HTML instead of PDF (content-type: {content_type})"

                # Normal download
                with open(dest_path, 'wb') as f:
                    total = 0
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        total += len(chunk)

                # Verify it's actually a PDF (or at least not tiny HTML error page)
                if total < 100:
                    with open(dest_path, 'rb') as f:
                        header = f.read(50)
                    if b'%PDF' not in header:
                        os.remove(dest_path)
                        return False, 0, f"Downloaded file too small ({total} bytes) and not a PDF"

                return True, total, None

        except urllib.error.HTTPError as e:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return False, 0, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return False, 0, f"URL Error: {e.reason}"
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            return False, 0, str(e)

    return False, 0, "Max retries exceeded"


def main():
    # Create download directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    all_urls = get_all_urls()
    total = len(all_urls)

    print(f"=" * 60)
    print(f"NOMAD Survival Library - PDF Downloader")
    print(f"Total URLs to process: {total}")
    print(f"Download directory: {DOWNLOAD_DIR}")
    print(f"=" * 60)

    manifest = {
        "download_date": datetime.now().isoformat(),
        "total_urls": total,
        "successful": 0,
        "failed": 0,
        "duplicates": 0,
        "items": [],
        "failures": [],
        "duplicate_map": {}
    }

    seen_hashes = {}  # hash -> first file info
    log_lines = []

    for i, entry in enumerate(all_urls, 1):
        url = entry["url"]
        title = entry["title"]
        source = entry["source"]

        # Convert Google Docs URLs
        download_url = url
        is_gdocs = False
        if "docs.google.com" in url:
            download_url = convert_gdocs_url(url)
            is_gdocs = True

        # Create filename
        filename = sanitize_filename(title) + ".pdf"
        dest_path = DOWNLOAD_DIR / filename

        # Skip if already downloaded (resume support)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            file_hash = sha256_file(dest_path)
            file_size = dest_path.stat().st_size

            if file_hash in seen_hashes:
                manifest["duplicates"] += 1
                manifest["duplicate_map"][filename] = seen_hashes[file_hash]["filename"]
                log_msg = f"[{i}/{total}] SKIP DUP: {title} (dup of {seen_hashes[file_hash]['title']})"
                print(log_msg)
                log_lines.append(log_msg)
                os.remove(dest_path)
            else:
                seen_hashes[file_hash] = {"filename": filename, "title": title}
                manifest["successful"] += 1
                manifest["items"].append({
                    "filename": filename,
                    "title": title,
                    "source": source,
                    "original_url": url,
                    "sha256": file_hash,
                    "size_bytes": file_size,
                    "is_gdocs": is_gdocs
                })
                log_msg = f"[{i}/{total}] CACHED: {title} ({file_size:,} bytes)"
                print(log_msg)
                log_lines.append(log_msg)
            continue

        # Download
        print(f"[{i}/{total}] Downloading: {title}...")
        success, file_size, error = download_file(download_url, dest_path)

        if success:
            file_hash = sha256_file(dest_path)

            # Check for duplicate
            if file_hash in seen_hashes:
                manifest["duplicates"] += 1
                manifest["duplicate_map"][filename] = seen_hashes[file_hash]["filename"]
                log_msg = f"[{i}/{total}] DUP: {title} (dup of {seen_hashes[file_hash]['title']})"
                print(log_msg)
                log_lines.append(log_msg)
                os.remove(dest_path)
            else:
                seen_hashes[file_hash] = {"filename": filename, "title": title}
                manifest["successful"] += 1
                manifest["items"].append({
                    "filename": filename,
                    "title": title,
                    "source": source,
                    "original_url": url,
                    "sha256": file_hash,
                    "size_bytes": file_size,
                    "is_gdocs": is_gdocs
                })
                log_msg = f"[{i}/{total}] OK: {title} ({file_size:,} bytes)"
                print(log_msg)
                log_lines.append(log_msg)
        else:
            manifest["failed"] += 1
            manifest["failures"].append({
                "title": title,
                "url": url,
                "download_url": download_url,
                "source": source,
                "error": error
            })
            log_msg = f"[{i}/{total}] FAIL: {title} - {error}"
            print(log_msg)
            log_lines.append(log_msg)

        # Small delay to be polite
        if is_gdocs:
            time.sleep(1.5)  # Google rate limiting
        else:
            time.sleep(0.5)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"DOWNLOAD COMPLETE")
    print(f"  Successful: {manifest['successful']}")
    print(f"  Failed:     {manifest['failed']}")
    print(f"  Duplicates: {manifest['duplicates']}")
    print(f"{'=' * 60}")

    # Calculate total size
    total_size = sum(item["size_bytes"] for item in manifest["items"])
    manifest["total_size_bytes"] = total_size
    manifest["total_size_mb"] = round(total_size / (1024 * 1024), 2)
    print(f"  Total size: {manifest['total_size_mb']} MB")

    # Save manifest
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nManifest saved to: {MANIFEST_FILE}")

    # Save log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    print(f"Log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
