# Project: NOMAD Survival Library

## Purpose
Curated offline PDF survival resource library for [Project NOMAD](https://github.com/Crosstalk-Solutions/project-nomad). Downloads, categorizes, scores, and summarizes freely available survival/preparedness PDFs for integration into NOMAD's offline content system.

## Related Projects
- **Project NOMAD**: https://github.com/Crosstalk-Solutions/project-nomad — The parent project. This library is designed to integrate with NOMAD's Content Explorer and tier system (Essential/Standard/Comprehensive).
- **Live repo**: https://github.com/Crosstalk-Solutions/nomad-survival-library

## Architecture

### Directory Structure
```
nomad-survival-library/
├── catalog/
│   └── catalog.json          # THE source of truth — all metadata, summaries, scores
├── pdfs/{category}/          # PDFs organized by category
├── scripts/                  # Python processing pipeline
├── links.txt                 # Source URLs for PDF discovery
└── README.md
```

### The Catalog (`catalog/catalog.json`)
This is the most important file in the project. It contains every PDF's metadata:
- `id`, `title`, `filename`, `path` — identification and location
- `category` — one of the 12 categories (see below)
- `tier` — `essential` | `standard` | `comprehensive`
- `relevance` — `high` | `low` (low = included but flagged as marginally useful)
- `summary` — concise content description (hand-written for essential tier, auto-generated for others)
- `pages`, `size_bytes`, `size_mb` — document metrics
- `sha256` — integrity hash, also used for deduplication
- `source`, `original_url` — provenance tracking
- `content_duplicate_of` — (optional) flags same-content different-scan duplicates

### Categories
| ID | Name |
|----|------|
| `survival` | Wilderness and general survival |
| `medicine` | Medical, first aid, field medicine |
| `preparedness` | Emergency planning, checklists, kits |
| `military` | Military field manuals and tactics |
| `nuclear-cbrn` | Nuclear/chemical/biological/radiological |
| `food-agriculture` | Food preservation, foraging, agriculture |
| `shelter-construction` | Shelter building and fortification |
| `education` | General survival education |
| `diy-repair` | DIY, repair, practical homestead skills |
| `navigation` | Maps, compass, communication |
| `water-sanitation` | Water treatment, hygiene |
| `reference` | Quick-reference cards and charts |

### Tier Scoring (matches NOMAD's content tiers)
- **Essential** — Life-saving, critical knowledge. First priority for limited storage. Examples: FM 21-76 Survival Manual, Where There is No Doctor, Nuclear War Survival Skills.
- **Standard** — Important reference and practical skills. Mid-tier priority. Examples: Ranger Handbook, LDS Preparedness Manual, canning guides.
- **Comprehensive** — Specialized, supplementary, or large reference volumes. Examples: EMP satellite damage report.

Scoring considers both **survival criticality** and **file size/storage impact**.

## Processing Pipeline

The scripts in `scripts/` form a pipeline. Run them in order when adding new content:

1. **`master_urls.py`** — Central URL registry. Add new source URLs here.
2. **`download_pdfs.py`** — Downloads all PDFs, deduplicates by SHA-256 hash. Outputs to `pdfs/_downloads/`.
3. **`retry_downloads.py`** — Retries failures with improved strategies (Google Docs, Wayback Machine, alternate headers).
4. **`categorize_pdfs.py`** — Auto-assigns categories and tier scores based on title/filename keyword matching.
5. **`generate_summaries.py`** — Extracts text via PyPDF2, generates summaries, refines categories/scores.
6. **`improve_summaries.py`** — Applies hand-written summaries for essential tier items. Has a `MANUAL_SUMMARIES` dict — add new hand-written summaries here.
7. **`organize_pdfs.py`** — Moves PDFs from `_downloads/` into `pdfs/{category}/` directories.
8. **`cleanup_catalog.py`** — Removes catalog entries for missing files, recalculates stats.

### Adding New PDFs
1. Add source URLs to `scripts/master_urls.py` in the appropriate list
2. Run `download_pdfs.py` (it skips already-downloaded files)
3. Run `categorize_pdfs.py` then `generate_summaries.py`
4. For any new essential items, add hand-written summaries to `improve_summaries.py` and run it
5. Run `organize_pdfs.py` to sort into category directories
6. Verify with `cleanup_catalog.py`

## Tech Stack
- **Python 3.11** — All scripts
- **PyPDF2** — PDF text extraction for summaries
- **Git LFS** — PDF storage (`.gitattributes` tracks `*.pdf`)
- **GitHub CLI (`gh`)** — Repo management

## Important Notes

- **Always update `catalog/catalog.json`** when adding, removing, or modifying PDFs. It's the source of truth for NOMAD integration.
- **Git LFS**: PDFs are LFS-tracked. Run `git lfs install` before cloning. The free GitHub tier gives 10 GB storage — current usage is ~422 MB.
- **Deduplication**: SHA-256 hash dedup catches identical files. `content_duplicate_of` field flags same-content-different-scan items (e.g., two different scans of the same Army field manual).
- **Relevance flagging**: Don't delete low-relevance items — flag them with `"relevance": "low"` so downstream consumers can filter.
- **Summaries**: Essential tier items get hand-written summaries (in `improve_summaries.py`). Standard/Comprehensive get auto-generated ones. Always hand-write summaries for new essential items.
- **Dead links**: ~121 source URLs are dead (old Google Docs from 2012, defunct domains). The `download_manifest.json` and `retry_manifest.json` track all failures for future recovery attempts.

## Current Stats (as of 2026-02-07)
- 109 PDFs, ~402 MB total
- 32 Essential / 76 Standard / 1 Comprehensive
- 5 low-relevance items flagged
- 2 content-level duplicate pairs identified
- Sources: trueprepper.com (63), seasonedcitizenprepper.com (31), infobooks.org (0 — 403 blocked), Wayback Machine recoveries (15)

## Future Work
- [ ] NOMAD integration — API service or Content Explorer plugin for browsing/downloading PDFs
- [ ] Recover more PDFs from dead Google Docs links (may need manual browser download)
- [ ] Download infobooks.org PDFs (requires browser-based approach to bypass 403)
- [ ] Add more source sites for broader coverage
- [ ] Improve auto-generated summaries for standard tier items
- [ ] Remove content-level duplicates (keep best quality scan of each)
