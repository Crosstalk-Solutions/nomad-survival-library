"""
NOMAD Survival Library - PDF Summary Generator
Extracts text from PDFs and generates concise content summaries.
Also validates and refines categorization and scoring.
"""

import json
import re
from pathlib import Path
from PyPDF2 import PdfReader

BASE_DIR = Path(__file__).parent.parent
CATALOG_FILE = BASE_DIR / "catalog" / "catalog.json"


def extract_text(pdf_path, max_pages=5):
    """Extract text from the first N pages of a PDF."""
    try:
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        text_parts = []

        for i in range(min(max_pages, num_pages)):
            try:
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception:
                continue

        full_text = "\n".join(text_parts)
        # Clean up
        full_text = re.sub(r'\s+', ' ', full_text)
        return full_text.strip(), num_pages
    except Exception as e:
        return "", 0


def generate_summary(title, text, num_pages, category, size_bytes):
    """Generate a concise summary from extracted text."""
    size_mb = round(size_bytes / (1024 * 1024), 2)

    if not text or len(text) < 50:
        return f"{title}. {num_pages}-page document ({size_mb} MB). Text extraction was limited; manual review recommended for accurate content summary."

    # Try to identify key topics from the text
    text_lower = text.lower()

    # Build summary based on what we can extract
    summary_parts = []

    # Detect document type
    if "field manual" in text_lower or "fm " in text_lower[:200]:
        summary_parts.append(f"U.S. military field manual")
    elif "department of the army" in text_lower[:500]:
        summary_parts.append(f"U.S. Army publication")
    elif "marine corps" in text_lower[:500] or "usmc" in text_lower[:500]:
        summary_parts.append(f"U.S. Marine Corps publication")
    elif "fema" in text_lower[:500]:
        summary_parts.append(f"FEMA publication")

    # Look for table of contents or chapter topics
    toc_keywords = []
    important_topics = [
        "water", "fire", "shelter", "food", "navigation", "first aid",
        "signaling", "survival", "medical", "weapons", "trapping",
        "hunting", "fishing", "plants", "knots", "radio", "nuclear",
        "decontamination", "evacuation", "emergency", "wounds",
        "fractures", "burns", "cpr", "bleeding", "shock",
        "canning", "preserving", "garden", "seeds", "soil",
        "cold weather", "desert", "tropical", "sea survival",
        "urban", "evasion", "concealment", "camouflage"
    ]

    for topic in important_topics:
        if topic in text_lower:
            toc_keywords.append(topic)

    # Build the summary
    if summary_parts:
        base = summary_parts[0]
    else:
        base = f"Reference document"

    topics_str = ""
    if toc_keywords:
        # Take top 5 most relevant
        topics_str = f" Covers topics including {', '.join(toc_keywords[:6])}."

    pages_str = f" {num_pages} pages, {size_mb} MB."

    return f"{title}. {base} providing guidance on {category.replace('-', ' ')} topics.{topics_str}{pages_str}"


def refine_category(title, text, current_category):
    """Refine category based on actual content."""
    text_lower = (text or "").lower()
    title_lower = title.lower()

    # Strong overrides based on content
    if any(k in text_lower[:1000] for k in ["nuclear", "radiological", "fallout", "detonation"]):
        if current_category not in ["nuclear-cbrn"]:
            if "nuclear" in title_lower or "nbc" in title_lower or "cbrn" in title_lower:
                return "nuclear-cbrn"

    if any(k in text_lower[:1000] for k in ["first aid", "medical", "wound", "patient", "treatment"]):
        if current_category not in ["medicine"]:
            if any(k in title_lower for k in ["medical", "medicine", "first aid", "doctor", "dentist"]):
                return "medicine"

    return current_category


def refine_score(title, text, current_score, num_pages, size_bytes):
    """Refine the tier score based on actual content analysis."""
    title_lower = title.lower()
    size_mb = size_bytes / (1024 * 1024)

    # Very small checklists/reference cards should be essential if practical
    if size_mb < 0.5 and ("checklist" in title_lower or "kit" in title_lower):
        return "essential"

    # Comprehensive military manuals (large, detailed)
    if size_mb > 15 and any(k in title_lower for k in ["encyclopedia", "cyclopedia", "complete guide"]):
        return "comprehensive"

    # Core survival documents should always be essential
    essential_titles = [
        "where there is no doctor", "where there is no dentist",
        "fm 21-76", "nuclear war survival skills", "first aid",
        "special forces medical", "survival and austere medicine",
        "field hygiene", "preventive medicine", "citizen preparedness",
        "bug out bag", "emergency plan", "survival kit"
    ]
    for et in essential_titles:
        if et in title_lower:
            return "essential"

    return current_score


def main():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    print(f"Generating summaries for {len(catalog['items'])} PDFs...")
    print("=" * 60)

    updated = 0
    errors = 0

    for i, item in enumerate(catalog["items"], 1):
        title = item["title"]
        path = item.get("path", "")

        if not path:
            path = f"pdfs/{item['category']}/{item['filename']}"

        pdf_path = BASE_DIR / path

        if not pdf_path.exists():
            print(f"[{i}/{len(catalog['items'])}] MISSING: {title}")
            errors += 1
            continue

        # Extract text
        text, num_pages = extract_text(pdf_path)

        # Update page count
        item["pages"] = num_pages

        # Refine category
        new_category = refine_category(title, text, item["category"])
        if new_category != item["category"]:
            print(f"  Category: {item['category']} -> {new_category}")
            item["category"] = new_category

        # Refine score
        new_score = refine_score(title, text, item["tier"], num_pages, item["size_bytes"])
        if new_score != item["tier"]:
            print(f"  Tier: {item['tier']} -> {new_score}")
            item["tier"] = new_score

        # Generate summary
        summary = generate_summary(title, text, num_pages, item["category"], item["size_bytes"])
        item["summary"] = summary

        updated += 1
        size_mb = round(item["size_bytes"] / (1024 * 1024), 2)
        print(f"[{i}/{len(catalog['items'])}] {title} ({num_pages}pp, {size_mb}MB)")

    # Recalculate stats
    cc = {}
    tc = {"essential": 0, "standard": 0, "comprehensive": 0}
    for item in catalog["items"]:
        cc[item["category"]] = cc.get(item["category"], 0) + 1
        tc[item["tier"]] = tc.get(item["tier"], 0) + 1

    catalog["stats"]["categories"] = cc
    catalog["stats"]["tiers"] = tc

    # Save updated catalog
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"SUMMARY GENERATION COMPLETE")
    print(f"  Updated:  {updated}")
    print(f"  Errors:   {errors}")
    print(f"\n  By Tier:")
    for tier, count in sorted(tc.items()):
        print(f"    {tier:>15}: {count}")
    print(f"\n  By Category:")
    for cat, count in sorted(cc.items()):
        print(f"    {cat:>25}: {count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
