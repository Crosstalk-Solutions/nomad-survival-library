# NOMAD Survival Library

Curated offline PDF survival resource library for [Project NOMAD](https://github.com/Crosstalk-Solutions/project-nomad). A categorized, scored, and summarized collection of freely available survival, preparedness, and self-sufficiency reference materials designed for offline use.

## Library Stats

| Metric | Value |
|--------|-------|
| Total PDFs | 155 |
| Total Size | ~490 MB |
| Essential Tier | 37 |
| Standard Tier | 116 |
| Comprehensive Tier | 2 |
| Categories | 12 |

## Categories

| Category | Count | Description |
|----------|-------|-------------|
| Education & Reference | 31 | General knowledge, homesteading, and educational materials |
| Preparedness & Planning | 27 | Emergency planning, checklists, bug-out preparation |
| Food & Agriculture | 20 | Food preservation, foraging, trapping, agriculture |
| Medicine & First Aid | 19 | Medical knowledge, first aid, field medicine |
| Survival | 17 | Wilderness survival, bushcraft, general survival skills |
| Military Manuals | 15 | Military field manuals, tactics, fieldcraft |
| Nuclear / CBRN | 9 | Nuclear, chemical, biological threat preparation |
| Shelter & Construction | 6 | Building shelters, fortifications, emergency structures |
| DIY & Repair | 6 | Construction, repair, practical skills |
| Navigation & Communication | 2 | Map reading, compass use, radio communication |
| Water & Sanitation | 2 | Water purification, hygiene, sanitation |
| Quick Reference | 1 | Checklists, charts, and quick-reference cards |

## Tier System

Matches Project NOMAD's content tier system:

- **Essential** — Life-saving knowledge and critical preparedness resources. Small-to-medium file sizes. First priority for limited storage.
- **Standard** — Important reference material and practical skills. Mid-tier priority.
- **Comprehensive** — Specialized reference volumes and supplementary materials. Full library inclusion.

## Directory Structure

```
nomad-survival-library/
├── README.md
├── links.txt                    # Source URLs
├── catalog/
│   ├── catalog.json             # Complete catalog with metadata, summaries, and scores
│   ├── download_manifest.json   # Download tracking and hash dedup records
│   └── download_log.txt         # Download session log
├── pdfs/
│   ├── education/               # 31 PDFs
│   ├── preparedness/            # 27 PDFs
│   ├── food-agriculture/        # 20 PDFs
│   ├── medicine/                # 19 PDFs
│   ├── survival/                # 17 PDFs
│   ├── military/                # 15 PDFs
│   ├── nuclear-cbrn/            # 9 PDFs
│   ├── shelter-construction/    # 6 PDFs
│   ├── diy-repair/              # 6 PDFs
│   ├── navigation/              # 2 PDFs
│   ├── water-sanitation/        # 2 PDFs
│   └── reference/               # 1 PDF
└── scripts/
    ├── master_urls.py           # All source URLs compiled
    ├── download_pdfs.py         # Bulk PDF downloader
    ├── retry_downloads.py       # Retry failed downloads
    ├── categorize_pdfs.py       # Auto-categorization engine
    ├── generate_summaries.py    # Text extraction + summary generation
    ├── improve_summaries.py     # Hand-written summaries for essential items
    ├── organize_pdfs.py         # Sort PDFs into category directories
    └── cleanup_catalog.py       # Catalog maintenance
```

## Catalog Format

Each entry in `catalog/catalog.json` contains:

```json
{
  "id": "fm-21-76-us-army-survival-manual",
  "title": "FM 21-76 US Army Survival Manual",
  "filename": "FM-21-76-US-Army-Survival-Manual.pdf",
  "category": "survival",
  "tier": "essential",
  "relevance": "high",
  "summary": "The definitive U.S. Army survival field manual covering...",
  "pages": 233,
  "size_bytes": 13340672,
  "size_mb": 12.72,
  "sha256": "abc123...",
  "source": "trueprepper",
  "original_url": "https://...",
  "path": "pdfs/survival/FM-21-76-US-Army-Survival-Manual.pdf"
}
```

## NOMAD Integration

The catalog is designed for integration with Project NOMAD's Content Explorer. Possible integration paths:

1. **API Service** — Expose catalog.json via a lightweight API that NOMAD's Command Center GUI can query
2. **Additional Content** — Integrate alongside ZIM files in the existing Content Explorer tier system
3. **Standalone App** — Separate PDF library browser within NOMAD's interface

### Key Integration Points

- `catalog.json` — Primary data source for browsing, filtering, and downloading
- `tier` field — Maps to NOMAD's Essential/Standard/Comprehensive content tiers
- `category` field — Enables filtering and organized browsing
- `path` field — Relative path to the PDF file for serving/downloading
- `sha256` field — Integrity verification for downloads

## Sources

PDFs sourced from freely available, public domain, and government publications:

- [TruePrepper](https://trueprepper.com/survival-pdfs-downloads/) — 63 PDFs (100% success rate)
- [Archive.org](https://archive.org/details/homesteading-survival-manuals) — 46 PDFs from the Homesteading & Survival Manuals collection
- [Seasoned Citizen Prepper](https://seasonedcitizenprepper.com/preparedness-downloads/) — 31 of 66 direct PDFs + ~110 legacy Google Docs links (mostly dead)
- [InfoBooks.org](https://www.infobooks.org/free-pdf-books/self-improvement/survival/) — 16 PDFs (blocked automated download)
- Wayback Machine — Used to recover some PDFs from defunct domains

## Notes

- PDFs are tracked with Git LFS (`.gitattributes` configured for `*.pdf`)
- SHA-256 hashes used for deduplication — 24 duplicates removed during processing
- 5 PDFs flagged as low relevance but included in library (Burning Man guide, dog bug-out bag, gift jar recipes, etc.)
- ~121 URLs from source pages were inaccessible (dead Google Docs links from 2012, defunct domains, 403 blocks)
