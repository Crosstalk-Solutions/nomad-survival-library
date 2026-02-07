"""
NOMAD Survival Library - PDF Categorizer and Scorer
Assigns categories, scores (Essential/Standard/Comprehensive),
and generates summaries for each downloaded PDF.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "pdfs" / "_downloads"
MANIFEST_FILE = BASE_DIR / "catalog" / "download_manifest.json"
CATALOG_FILE = BASE_DIR / "catalog" / "catalog.json"

# Category definitions with keyword matching
CATEGORY_RULES = {
    "survival": {
        "keywords": ["survival manual", "survival guide", "survival skills", "wilderness survival",
                     "bushcraft", "woodcraft", "camping", "boy scout", "fieldcraft",
                     "backcountry", "outback", "woods", "evasion", "recovery",
                     "cold weather", "winter survival", "paleo-pocalypse", "worst case scenario",
                     "survive doomsday", "surviving in the city", "surviving terrorism",
                     "urban survival", "combat survival", "mountaineering", "antarctic",
                     "austere", "alpine", "debris hut", "flintknapping"],
        "priority": 2
    },
    "medicine": {
        "keywords": ["medical", "medicine", "first aid", "dentist", "doctor", "health care",
                     "preventive medicine", "wound closure", "war surgery", "hygiene",
                     "sanitation", "wilderness medicine", "medicinal plants", "herbal",
                     "nature cure", "anticancer", "healing pets", "pandemic",
                     "influenza", "medical kit", "hospital"],
        "priority": 1
    },
    "preparedness": {
        "keywords": ["preparedness", "emergency plan", "checklist", "bug out", "get home bag",
                     "inch bag", "wush bag", "scare kit", "survival kit", "disaster supply",
                     "crisis guide", "citizen preparedness", "lds prep", "self-sufficient",
                     "3 day emergency", "everyday carry", "car emergency", "bug out vehicle",
                     "family supply", "home survival", "crisis", "be prepared",
                     "basic emergency", "compact survival kit"],
        "priority": 3
    },
    "military": {
        "keywords": ["fm 21-76", "fm 31-70", "fm 3-06", "fm 3-25", "fm 5-103",
                     "fm 20-3", "fm 4-25", "stp 21-", "ranger handbook",
                     "army warrior", "military", "combatives", "martial arts",
                     "kill or get killed", "guerrilla", "art of war",
                     "camouflage", "concealment", "survivability", "urban operations",
                     "tm 31-210", "improvised munitions", "close quarters combat",
                     "hand to hand", "fieldcraft", "usmc", "marines"],
        "priority": 4
    },
    "nuclear-cbrn": {
        "keywords": ["nuclear", "nbc", "cbrn", "radiation", "fallout", "shelter design",
                     "emp", "decontamination", "contamination", "nuclear war",
                     "nuclear winter", "nuclear survival", "detonation"],
        "priority": 1
    },
    "food-agriculture": {
        "keywords": ["canning", "preserving", "food", "recipe", "garden", "farming",
                     "agriculture", "mushroom", "edible", "jerky", "dutch oven",
                     "cooking", "dehydrat", "drying", "fermented", "pickle",
                     "game meat", "fish", "trapping", "snare", "deadfall",
                     "hunting", "foraging", "berry", "baby food", "cookbook",
                     "food supply", "food storage", "soil", "composting",
                     "greenhouse", "vegetable", "tanning"],
        "priority": 5
    },
    "diy-repair": {
        "keywords": ["carpentry", "concrete", "masonry", "metal forming", "woodworking",
                     "macgyver", "how-to", "household cyclopedia", "home repair",
                     "generator", "wood burning", "leather work", "foxfire",
                     "black powder", "energy device"],
        "priority": 6
    },
    "navigation": {
        "keywords": ["map reading", "land navigation", "compass", "direction finding",
                     "signaling", "radio monitoring", "phonetic alphabet", "find your way"],
        "priority": 3
    },
    "self-defense": {
        "keywords": ["combatives", "martial arts", "hand to hand", "self defense",
                     "krav maga", "aikido", "jiujitsu", "jiu-jitsu", "unarmed combat",
                     "pressure points", "kill or get killed", "close quarters",
                     "physical security", "physical fitness", "navy seal fitness",
                     "secret hiding", "steal this book"],
        "priority": 7
    },
    "shelter-construction": {
        "keywords": ["shelter", "shack", "shanties", "debris hut", "shelter building",
                     "shelter construction", "fallout shelter", "family shelter"],
        "priority": 5
    },
    "water-sanitation": {
        "keywords": ["water purification", "water treatment", "sodis", "safe water",
                     "hygiene", "sanitation", "field hygiene"],
        "priority": 3
    },
    "reference": {
        "keywords": ["checklist", "phonetic alphabet", "edibility test", "load chart",
                     "knots", "rope", "lashing", "splices"],
        "priority": 8
    },
    "education": {
        "keywords": ["handbook", "encyclopedia", "manual", "guide", "training"],
        "priority": 10  # catch-all, lowest priority
    }
}

# Scoring rules
# Essential = life-saving, small-to-medium, critical for survival
# Standard = important reference, practical skills
# Comprehensive = nice-to-have, specialized, large reference volumes
ESSENTIAL_KEYWORDS = [
    "where there is no doctor", "where there is no dentist", "first aid",
    "fm 21-76", "survival manual", "water purification", "water treatment",
    "nuclear war survival skills", "emergency plan", "citizen preparedness",
    "medical handbook", "survival and austere medicine", "wilderness medicine",
    "emergency war surgery", "wound closure", "field hygiene",
    "nuclear survival", "bug out bag", "survival kit",
    "fm 4-25", "preventive medicine"
]

STANDARD_KEYWORDS = [
    "cold weather", "canning", "preserving", "shelter", "map reading",
    "navigation", "compass", "preparedness manual", "lds prep",
    "ranger handbook", "edible", "trapping", "snare", "bushcraft",
    "crisis guide", "food", "garden", "camping", "self-sufficient",
    "decontamination", "contamination", "protection", "fallout",
    "checklist", "knots", "deadfalls", "signals", "direction finding"
]

# Low relevance items
LOW_RELEVANCE_KEYWORDS = [
    "burning man", "dog bug out", "gift mix", "baby food",
    "healing pets", "anticancer", "stealing", "steal this book",
    "navy seal fitness", "boy scout cookbook", "dutch oven",
    "camping recipes", "native berry"
]

# Political/conspiracy content filter
# This library focuses on practical general knowledge. PDFs with overtly
# political, partisan, or conspiracy-theory framing are excluded.
# Note: Military manuals, government preparedness guides, and religious-origin
# practical guides (e.g. LDS Preparedness Manual) are NOT political — they
# teach practical skills without pushing an ideology.
POLITICAL_EXCLUSION_KEYWORDS = [
    "new world order", "deep state", "globalist agenda", "illuminati",
    "government conspiracy", "one world government", "shadow government",
    "sovereign citizen", "political manifesto", "anarchist cookbook",
    "patriot movement", "militia movement", "insurrection",
    "government tyranny", "gun control", "second amendment",
    "great reset conspiracy", "martial law takeover", "wake up sheeple",
    "false flag", "crisis actor", "truth movement",
    "agenda 21", "agenda 2030 conspiracy", "fema camp",
    "depopulation agenda", "chemtrail", "great replacement",
]


def check_political_content(title, filename):
    """Check if a PDF title/filename indicates overtly political content.
    Returns the matched keyword if political, or None if clean."""
    combined = (title + " " + filename).lower()
    for keyword in POLITICAL_EXCLUSION_KEYWORDS:
        if keyword in combined:
            return keyword
    return None


def categorize_pdf(title, filename):
    """Assign the best category based on title keywords."""
    title_lower = title.lower()
    filename_lower = filename.lower()
    combined = title_lower + " " + filename_lower

    best_category = "education"  # default fallback
    best_priority = 999
    best_match_count = 0

    for cat_id, cat_info in CATEGORY_RULES.items():
        match_count = 0
        for keyword in cat_info["keywords"]:
            if keyword.lower() in combined:
                match_count += 1

        if match_count > 0:
            # Prefer categories with more keyword matches, then by priority
            if match_count > best_match_count or (match_count == best_match_count and cat_info["priority"] < best_priority):
                best_category = cat_id
                best_priority = cat_info["priority"]
                best_match_count = match_count

    return best_category


def score_pdf(title, filename, size_bytes):
    """Score PDF as Essential/Standard/Comprehensive."""
    combined = (title + " " + filename).lower()
    size_mb = size_bytes / (1024 * 1024)

    # Check for Essential
    for keyword in ESSENTIAL_KEYWORDS:
        if keyword in combined:
            return "essential"

    # Check for Standard
    for keyword in STANDARD_KEYWORDS:
        if keyword in combined:
            return "standard"

    # Large files tend to be comprehensive reference volumes
    if size_mb > 20:
        return "comprehensive"

    # Default to standard
    return "standard"


def check_relevance(title):
    """Check if a PDF has low relevance to serious survival scenarios."""
    title_lower = title.lower()
    for keyword in LOW_RELEVANCE_KEYWORDS:
        if keyword in title_lower:
            return "low"
    return "high"


def generate_summary_from_title(title, category, score):
    """Generate a basic summary from the title and metadata.
    A more thorough summary would require reading the PDF content."""
    cat_names = {
        "survival": "survival",
        "medicine": "medical and first aid",
        "preparedness": "emergency preparedness",
        "military": "military field operations",
        "nuclear-cbrn": "nuclear/CBRN preparedness",
        "food-agriculture": "food procurement and preservation",
        "diy-repair": "DIY construction and repair",
        "navigation": "navigation and communication",
        "self-defense": "self-defense and security",
        "shelter-construction": "shelter construction",
        "water-sanitation": "water and sanitation",
        "reference": "quick reference",
        "education": "general education",
        "computing-technology": "computing and technology"
    }
    cat_desc = cat_names.get(category, "general reference")
    return f"{title}. A {cat_desc} resource classified as {score} for offline survival library use."


def main():
    # Load manifest
    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)

    # Load existing catalog template
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    print(f"Processing {len(manifest['items'])} downloaded PDFs...")

    catalog_items = []
    category_counts = {}
    tier_counts = {"essential": 0, "standard": 0, "comprehensive": 0}
    excluded_political = []

    for item in manifest["items"]:
        title = item["title"]
        filename = item["filename"]
        size_bytes = item["size_bytes"]

        # Political content filter — skip overtly political/conspiracy material
        political_match = check_political_content(title, filename)
        if political_match:
            excluded_political.append((title, political_match))
            print(f"  [EXCLUDED - POLITICAL] {title} (matched: \"{political_match}\")")
            continue

        # Categorize
        category = categorize_pdf(title, filename)
        category_counts[category] = category_counts.get(category, 0) + 1

        # Score
        score = score_pdf(title, filename, size_bytes)
        tier_counts[score] += 1

        # Relevance
        relevance = check_relevance(title)

        # Summary
        summary = generate_summary_from_title(title, category, score)

        catalog_item = {
            "id": filename.replace(".pdf", "").lower().replace(" ", "-"),
            "title": title,
            "filename": filename,
            "category": category,
            "tier": score,
            "relevance": relevance,
            "summary": summary,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "sha256": item["sha256"],
            "source": item["source"],
            "original_url": item["original_url"]
        }

        catalog_items.append(catalog_item)

        print(f"  [{category:>20}] [{score:>13}] [{relevance:>4}] {title}")

    # Sort items by category, then by tier priority, then by title
    tier_order = {"essential": 0, "standard": 1, "comprehensive": 2}
    catalog_items.sort(key=lambda x: (x["category"], tier_order.get(x["tier"], 1), x["title"]))

    # Update catalog
    catalog["generated"] = datetime.now().isoformat()
    catalog["stats"]["total_pdfs"] = len(catalog_items)
    catalog["stats"]["categories"] = category_counts
    catalog["stats"]["tiers"] = tier_counts
    catalog["items"] = catalog_items

    # Calculate total size
    total_size = sum(item["size_bytes"] for item in catalog_items)
    catalog["stats"]["total_size_mb"] = round(total_size / (1024 * 1024), 2)

    # Save catalog
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"CATALOGING COMPLETE")
    print(f"  Total PDFs:    {len(catalog_items)}")
    print(f"  Total size:    {catalog['stats']['total_size_mb']} MB")
    print(f"\n  By Category:")
    for cat, count in sorted(category_counts.items()):
        print(f"    {cat:>25}: {count}")
    print(f"\n  By Tier:")
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier:>15}: {count}")
    print(f"\n  Low relevance: {sum(1 for i in catalog_items if i['relevance'] == 'low')}")
    if excluded_political:
        print(f"\n  Excluded (political content): {len(excluded_political)}")
        for title, keyword in excluded_political:
            print(f"    - {title} (matched: \"{keyword}\")")
    print(f"{'='*60}")
    print(f"\nCatalog saved to: {CATALOG_FILE}")


if __name__ == "__main__":
    main()
