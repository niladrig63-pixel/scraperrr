# 📋 Project Constitution — project.md

> **Single Source of Truth: Map & Vision**

---

## Primary Purpose
Build a **beautiful, interactive AI News Aggregator Dashboard** that scrapes the latest articles (last 24 hours) from AI newsletters and displays them in a gorgeous, modern web UI. Users can save/bookmark articles that persist across page refreshes. The system runs on a 24-hour cycle — new articles appear automatically; if there are none, nothing changes.

## Primary Tech Stack
- **Backend:** Python 3.11+ (FastAPI, scraping, data processing)
- **Frontend:** HTML/CSS/JS (single-page app, bento-grid layout)
- **Scraping:** `requests` + `BeautifulSoup4`
- **Persistence:** Local JSON files (Supabase planned later)
- **Server:** FastAPI (async, serves API + static frontend)
- **Scheduling:** APScheduler (embedded 24-hour cycle)

## Brand Identity — Glaido
- **Primary/Accent:** `#BFF549` (bright lime green)
- **Background:** `#000000` (pure black)
- **Text on green:** `#000000`
- **Secondary text / links:** `#99A1AF` (silver-grey)
- **Font:** Inter — h1: 96px, h2: 48px, body: 24px
- **Logo:** `DesignGuidelines/glaido-main-white.svg`
- **UI Style:** Bento grid / card layout — modular, dark-mode, interactive

## Sources (Phase 1 — Newsletters)
| Source | URL | Platform | Notes |
|---|---|---|---|
| Ben's Bites | `https://www.bensbites.com/archive` | Substack | Public archive, article links follow `/p/` pattern |
| The Rundown AI | `https://www.therundown.ai/` | Custom (Beehiiv-based) | Public article listing, links follow `/p/` pattern |
| Reddit (r/artificial, etc.) | *Planned for later* | Reddit API / scrape | Future phase |

## Expected Output / Deliverables
1. **Web Dashboard** — gorgeous, responsive, card-based article feed
2. **Scraper Engine** — collects articles from sources every 24 hours
3. **Save/Bookmark System** — saved articles persist across refreshes (local storage + backend JSON)
4. **Auto-refresh** — dashboard reflects latest scraped data on load; manual refresh available

## Goals & Constraints
- **Data-first:** Scrape → Parse → Store → Serve → Display
- **24-hour cycle:** Only fetch new articles; skip if nothing new
- **Persistence:** Saved articles AND scraped data survive page refresh
- **Gorgeous UI:** Modern, sleek, interactive design (cards, animations, dark mode)
- **Modular:** Each source is a separate scraper module (easy to add Reddit later)

## Behavioral Rules / "Do Not" Rules
- Do NOT scrape more than once per 24 hours per source
- Do NOT lose saved/bookmarked articles on refresh
- Do NOT proceed with scraping if a source is unreachable — log the error gracefully
- Do NOT hardcode article data — everything flows from the scraper pipeline
- Do NOT build Supabase integration yet — that's a future phase

---

**Status:** 🟢 COMPLETE — Ready for Data Schema confirmation in `data_logic.md`.
