"""
Improve catalog summaries with hand-written descriptions for essential items
and better auto-generated ones for the rest.
"""

import json
from pathlib import Path
from PyPDF2 import PdfReader

BASE_DIR = Path(__file__).parent.parent
CATALOG_FILE = BASE_DIR / "catalog" / "catalog.json"

# Hand-written summaries for essential tier items
MANUAL_SUMMARIES = {
    "FM 21-76 US Army Survival Manual": "The definitive U.S. Army survival field manual covering psychology of survival, planning, basic medicine, shelter construction, water procurement, fire-making, food foraging, weapons and tools, desert/tropical/cold weather/sea survival, navigation, and signaling. The gold standard reference for military and civilian wilderness survival.",
    "FM 21-76-1 Survival Evasion and Recovery": "U.S. military multiservice guide covering survival, evasion, resistance, and escape (SERE) procedures. Includes navigation without instruments, shelter and fire techniques, water and food procurement, evasion planning, and recovery operations. Companion to FM 21-76.",
    "FM 21-76-1 Survival Evasion Recovery": "Alternate edition of the U.S. military survival, evasion, and recovery manual covering SERE principles, fieldcraft, navigation, sustenance, and evader conduct. Duplicate content to FM 21-76-1 from trueprepper.",
    "FM 4-25.11 First Aid": "U.S. Army field manual for first aid procedures including casualty evaluation, breathing restoration, bleeding control, shock prevention, fracture treatment, burns care, heat/cold injuries, and field-expedient bandaging. Essential medical reference for emergency situations.",
    "Where There is No Doctor": "Comprehensive 503-page village health care handbook by David Werner, widely regarded as the most important medical reference for situations without professional healthcare access. Covers diagnostics, common diseases, wounds, childbirth, nutrition, preventive care, and when to seek help. Used worldwide by aid organizations.",
    "Where There is No Dentist": "Practical dental care guide for situations without access to professional dentistry. Covers tooth anatomy, common dental problems, pain management, tooth extraction, oral hygiene, and preventive dental care using available materials.",
    "ST 31-91B Special Forces Medical Handbook": "Comprehensive U.S. Army Special Forces medical reference covering emergency assessment, trauma care, pharmacology, disease diagnosis, veterinary medicine, dental emergencies, OB/GYN, pediatrics, and preventive medicine. One of the most thorough military medical handbooks available.",
    "US Army Special Forces Medical Handbook ST 31-91B": "Alternate edition of the Special Forces Medical Handbook. Comprehensive military medical reference covering emergency treatment, trauma surgery, pharmacology, disease management, and preventive medicine across 407 pages. Larger file size edition with clearer formatting.",
    "Survival and Austere Medicine": "Community-authored guide to practicing medicine when modern healthcare is unavailable. Covers wound management, fractures, infections, chronic disease management, improvised equipment, dental care, anesthesia, and pharmaceutical alternatives. Highly practical for long-term grid-down scenarios.",
    "NAVMED P-5010 USN Manual of Preventive Medicine": "U.S. Navy guide covering disease prevention, sanitation, pest control, food safety, water quality, occupational health, and field hygiene. Essential for maintaining health in austere or group-living conditions.",
    "FM 21-10 Field Hygiene and Sanitation": "U.S. Army manual on maintaining health and hygiene in field conditions. Covers water purification, waste disposal, personal hygiene, pest management, food sanitation, and disease prevention. Critical for any scenario involving group survival.",
    "Nuclear War Survival Skills by Cresson Kearny": "The definitive civilian guide to surviving nuclear war, authored by Oak Ridge National Laboratory researcher Cresson Kearny. Covers blast/fallout protection, improvised shelters, ventilation, water/food storage, radiation measurement, and post-attack recovery across 317 pages. Essential reading for nuclear preparedness.",
    "Nuclear War Survival Skills": "Alternate edition of Kearny's nuclear survival guide covering fallout protection, improvised shelter construction, ventilation pumps, water storage, fallout meter construction, and recovery procedures. Core nuclear preparedness reference.",
    "Nuclear Survival Kit Checklist": "Quick-reference checklist for assembling a nuclear event survival kit including radiation detection, shelter supplies, decontamination materials, and communication equipment.",
    "FEMA Citizen Preparedness Guide": "Official FEMA guide for individual and family emergency preparedness covering risk assessment, emergency kits, communication plans, shelter-in-place procedures, and evacuation planning across multiple disaster types.",
    "Basic Emergency Plan": "Concise emergency planning template for families and individuals to document evacuation routes, meeting points, emergency contacts, and critical procedures.",
    "Home Survival Kit Checklist": "Practical checklist for assembling a comprehensive home emergency kit covering water, food, first aid, tools, communication, lighting, and sanitation supplies.",
    "Bug Out Bag Checklist": "Detailed checklist for building a 72-hour evacuation bag covering shelter, water filtration, fire-making, food, first aid, navigation, communication, and personal documents.",
    "Survival First Aid Kit Checklist": "Comprehensive checklist for assembling a survival-oriented first aid kit including trauma supplies, medications, wound care, and improvised medical tools.",
    "Flood Survival Kit Checklist": "Specialized checklist for flood disaster preparation including water barriers, waterproof storage, evacuation supplies, and recovery essentials.",
    "Hurricane Survival Kit Checklist": "Hurricane-specific emergency kit checklist covering wind protection, water supply, communication backup, structural reinforcement, and evacuation readiness.",
    "Kids Bug Out Bag Checklist": "Age-appropriate evacuation bag checklist for children including comfort items, identification, simplified survival supplies, and medical information.",
    "Down But Not Out - Canadian Survival Manual": "Canadian Armed Forces survival manual covering Arctic, temperate, and wilderness survival including shelter construction, fire-making, water procurement, food sources, navigation, and rescue signaling. Adapted for Canadian geography and climate extremes.",
    "Montana Winter Survival Manual": "State-published winter survival guide focused on cold weather vehicle emergencies, hypothermia prevention, shelter building in snow, fire-making in wet conditions, and winter-specific survival priorities.",
    "Dog Bug Out Bag Checklist": "Checklist for preparing an evacuation kit for dogs including food, water, medications, identification, leash/carrier, and comfort items.",
    "3 Day Emergency Prep": "Practical 3-day emergency preparedness guide covering essential supplies, water storage, food preparation, first aid basics, communication plans, and shelter-in-place procedures.",
    "Bug Out Vehicle Checklist": "Checklist for outfitting a vehicle for emergency evacuation including mechanical supplies, fuel reserves, navigation tools, camping gear, and security considerations.",
    "Everyday Carry Checklist": "Practical checklist for daily-carry preparedness items including tools, first aid, communication, fire-making, and personal protection essentials.",
    "Estonia Be Prepared Crisis Guide": "Estonian government crisis preparedness guide covering emergency supplies, communication plans, evacuation procedures, and self-sufficiency during infrastructure disruption. Notable for its post-Soviet practical approach to civil defense.",
    "FEMA Family Supply List": "Official FEMA recommended supply list for family emergency preparedness including water, food, medical, sanitation, and communication essentials.",
    "How to Handle a Crisis": "160-page comprehensive crisis management guide covering natural disasters, civil emergencies, personal safety, and family preparedness with practical action plans.",
    "Norway One Week Preparedness Guide": "Norwegian government guide for civilian self-sufficiency during one week of infrastructure disruption covering water, food, warmth, communication, and medical supplies.",
    "SCARE Kit Checklist": "Specialized emergency kit checklist for shelter, communication, aid, recovery, and escape scenarios.",
    "Sweden In Case of Crisis or War": "Swedish government civil defense booklet distributed to all households covering wartime preparedness, shelter procedures, supply stockpiling, and crisis communication. Notable for direct government guidance on military threat preparedness.",
}


def extract_text_snippet(pdf_path, max_pages=3):
    """Extract a text snippet for auto-summary generation."""
    try:
        reader = PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        text_parts = []
        for i in range(min(max_pages, num_pages)):
            try:
                t = reader.pages[i].extract_text()
                if t:
                    text_parts.append(t)
            except Exception:
                continue
        return " ".join(text_parts)[:2000], num_pages
    except Exception:
        return "", 0


def auto_summary(title, text, num_pages, size_bytes, category):
    """Generate a better auto-summary when no manual one exists."""
    size_mb = round(size_bytes / (1024 * 1024), 2)

    if not text or len(text) < 30:
        return f"{title}. A {num_pages}-page reference document ({size_mb} MB) in the {category.replace('-', ' ')} category for offline survival library use."

    # Detect the publishing organization from early text
    text_lower = text.lower()[:800]
    org = ""
    if "department of the army" in text_lower:
        org = "U.S. Army"
    elif "marine corps" in text_lower or "usmc" in text_lower:
        org = "U.S. Marine Corps"
    elif "department of defense" in text_lower:
        org = "U.S. Department of Defense"
    elif "fema" in text_lower:
        org = "FEMA"
    elif "canadian" in text_lower or "canada" in text_lower:
        org = "Canadian Forces"
    elif "boy scout" in text_lower:
        org = "Boy Scouts of America"

    org_str = f"{org} " if org else ""

    cat_desc = {
        "survival": "wilderness and general survival",
        "medicine": "medical and health care",
        "preparedness": "emergency preparedness and planning",
        "military": "military operations and tactics",
        "nuclear-cbrn": "nuclear, chemical, biological, and radiological defense",
        "food-agriculture": "food procurement, preservation, and agriculture",
        "diy-repair": "practical DIY skills and home management",
        "navigation": "navigation and communication",
        "self-defense": "self-defense and personal security",
        "shelter-construction": "shelter design and construction",
        "water-sanitation": "water treatment and sanitation",
        "reference": "quick reference",
        "education": "general survival education",
    }.get(category, "general reference")

    return f"{title}. {org_str}{num_pages}-page reference covering {cat_desc} topics. {size_mb} MB."


def main():
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)

    manual_count = 0
    auto_count = 0

    for item in catalog["items"]:
        title = item["title"]

        # Check for manual summary
        if title in MANUAL_SUMMARIES:
            item["summary"] = MANUAL_SUMMARIES[title]
            manual_count += 1
        else:
            # Generate improved auto-summary
            path = item.get("path", f"pdfs/{item['category']}/{item['filename']}")
            pdf_path = BASE_DIR / path
            text, _ = extract_text_snippet(pdf_path) if pdf_path.exists() else ("", 0)
            item["summary"] = auto_summary(
                title, text, item.get("pages", 0),
                item["size_bytes"], item["category"]
            )
            auto_count += 1

    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Updated summaries: {manual_count} manual, {auto_count} auto-generated")
    print(f"Catalog saved to {CATALOG_FILE}")


if __name__ == "__main__":
    main()
