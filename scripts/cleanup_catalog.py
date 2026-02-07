"""Clean up catalog - remove entries for files that don't exist (deduped).
Also updates README.md stats to match current catalog."""
import json
import re
from pathlib import Path

# Category ID -> display name mapping
CATEGORY_NAMES = {
    "diy-repair": "DIY & Repair",
    "education": "Education & Reference",
    "food-agriculture": "Food & Agriculture",
    "medicine": "Medicine & First Aid",
    "military": "Military Manuals",
    "navigation": "Navigation & Communication",
    "nuclear-cbrn": "Nuclear / CBRN",
    "preparedness": "Preparedness & Planning",
    "reference": "Quick Reference",
    "shelter-construction": "Shelter & Construction",
    "survival": "Survival",
    "water-sanitation": "Water & Sanitation",
}

CATEGORY_DESCRIPTIONS = {
    "diy-repair": "Construction, repair, practical skills",
    "education": "General knowledge, homesteading, and educational materials",
    "food-agriculture": "Food preservation, foraging, trapping, agriculture",
    "medicine": "Medical knowledge, first aid, field medicine",
    "military": "Military field manuals, tactics, fieldcraft",
    "navigation": "Map reading, compass use, radio communication",
    "nuclear-cbrn": "Nuclear, chemical, biological threat preparation",
    "preparedness": "Emergency planning, checklists, bug-out preparation",
    "reference": "Checklists, charts, and quick-reference cards",
    "shelter-construction": "Building shelters, fortifications, emergency structures",
    "survival": "Wilderness survival, bushcraft, general survival skills",
    "water-sanitation": "Water purification, hygiene, sanitation",
}


def cleanup_catalog():
    """Remove catalog entries for missing files and recalculate stats."""
    with open("catalog/catalog.json") as f:
        catalog = json.load(f)

    pdfs_dir = Path("pdfs")
    clean = []
    removed = []

    for item in catalog["items"]:
        path = item.get("path", "")
        if path and Path(path).exists():
            clean.append(item)
        else:
            # Try to find it
            cat_path = pdfs_dir / item["category"] / item["filename"]
            if cat_path.exists():
                item["path"] = str(cat_path).replace("\\", "/")
                clean.append(item)
            else:
                removed.append(item["title"])

    if removed:
        print(f"Removed {len(removed)} entries with missing files:")
        for r in removed:
            print(f"  - {r}")
    else:
        print("No missing files found.")

    # Recalculate stats
    cc = {}
    tc = {"essential": 0, "standard": 0, "comprehensive": 0}
    for item in clean:
        cc[item["category"]] = cc.get(item["category"], 0) + 1
        tc[item["tier"]] = tc.get(item["tier"], 0) + 1

    catalog["items"] = clean
    catalog["stats"]["total_pdfs"] = len(clean)
    catalog["stats"]["categories"] = cc
    catalog["stats"]["tiers"] = tc
    ts = sum(i["size_bytes"] for i in clean)
    catalog["stats"]["total_size_mb"] = round(ts / (1024 * 1024), 2)

    with open("catalog/catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\nFinal catalog: {len(clean)} PDFs, {catalog['stats']['total_size_mb']} MB")
    print(f"Tiers: {tc}")
    print(f"Categories: {cc}")

    return catalog["stats"], cc, tc


def update_readme(stats, category_counts, tier_counts):
    """Update README.md with current catalog stats."""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("\nNo README.md found, skipping update.")
        return

    readme = readme_path.read_text(encoding="utf-8")
    total = stats["total_pdfs"]
    size_mb = stats["total_size_mb"]

    # 1. Update Library Stats table
    stats_table = (
        "| Metric | Value |\n"
        "|--------|-------|\n"
        f"| Total PDFs | {total} |\n"
        f"| Total Size | ~{round(size_mb)} MB |\n"
        f"| Essential Tier | {tier_counts['essential']} |\n"
        f"| Standard Tier | {tier_counts['standard']} |\n"
        f"| Comprehensive Tier | {tier_counts['comprehensive']} |\n"
        f"| Categories | {len(category_counts)} |"
    )
    readme = re.sub(
        r"\| Metric \| Value \|.*?\| Categories \| \d+ \|",
        stats_table,
        readme,
        flags=re.DOTALL,
    )

    # 2. Update Categories table (sorted by count descending)
    sorted_cats = sorted(category_counts.items(), key=lambda x: -x[1])
    cat_rows = ["| Category | Count | Description |", "|----------|-------|-------------|"]
    for cat_id, count in sorted_cats:
        name = CATEGORY_NAMES.get(cat_id, cat_id)
        desc = CATEGORY_DESCRIPTIONS.get(cat_id, "")
        cat_rows.append(f"| {name} | {count} | {desc} |")
    cat_table = "\n".join(cat_rows)

    readme = re.sub(
        r"\| Category \| Count \| Description \|.*?(?=\n\n)",
        cat_table,
        readme,
        flags=re.DOTALL,
    )

    # 3. Update directory tree PDF counts
    for cat_id, count in category_counts.items():
        pattern = rf"(│   [├└]── {re.escape(cat_id)}/)(\s+# )\d+( PDFs?)"
        readme = re.sub(pattern, rf"\g<1>\g<2>{count}\3", readme)

    readme_path.write_text(readme, encoding="utf-8")
    print(f"\nREADME.md updated with current stats.")


if __name__ == "__main__":
    stats, cc, tc = cleanup_catalog()
    update_readme(stats, cc, tc)
