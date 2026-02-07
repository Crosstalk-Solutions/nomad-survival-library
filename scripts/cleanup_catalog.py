"""Clean up catalog - remove entries for files that don't exist (deduped)."""
import json
from pathlib import Path

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

print(f"Removed {len(removed)} duplicate entries:")
for r in removed:
    print(f"  - {r}")

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
