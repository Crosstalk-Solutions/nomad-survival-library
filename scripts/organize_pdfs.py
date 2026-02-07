"""
NOMAD Survival Library - Organize PDFs into category directories
Moves PDFs from _downloads into their assigned category folders.
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "pdfs" / "_downloads"
PDFS_DIR = BASE_DIR / "pdfs"
CATALOG_FILE = BASE_DIR / "catalog" / "catalog.json"


def main():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    moved = 0
    errors = 0

    for item in catalog["items"]:
        filename = item["filename"]
        category = item["category"]
        src = DOWNLOAD_DIR / filename
        dest_dir = PDFS_DIR / category
        dest = dest_dir / filename

        if not src.exists():
            # Check if already moved
            if dest.exists():
                continue
            print(f"  MISSING: {filename}")
            errors += 1
            continue

        # Ensure category dir exists
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(src), str(dest))
        moved += 1

        # Update catalog with relative path
        item["path"] = f"pdfs/{category}/{filename}"

    # Save updated catalog
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nOrganized {moved} PDFs into category directories")
    if errors:
        print(f"  {errors} files were missing")

    # Show directory structure
    print(f"\nDirectory structure:")
    for cat_dir in sorted(PDFS_DIR.iterdir()):
        if cat_dir.is_dir() and cat_dir.name != "_downloads":
            count = len(list(cat_dir.glob("*.pdf")))
            if count > 0:
                print(f"  pdfs/{cat_dir.name}/  ({count} PDFs)")


if __name__ == "__main__":
    main()
