"""
main.py — Glaido AI News Aggregator: FastAPI Server + Scheduler

Phase 3 Layer 2: Management (Decision Making)
- Serves the API endpoints defined in data_logic.md
- Manages article storage (JSON files)
- Runs the 24-hour scrape scheduler
- Serves the static frontend dashboard
"""

import os
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core_logic import scrape_all, scrape_source, SCRAPERS
from tools import now_iso, ensure_data_dir
from supabase_store import (
    load_articles, save_articles, merge_articles,
    load_saved_ids, save_bookmark, remove_bookmark,
    get_saved_article_ids,
    load_scrape_state, save_scrape_state,
    check_connection,
)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

# ---------------------------------------------------------------------------
# Environment Detection
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# ---------------------------------------------------------------------------
# Scheduler Setup (skipped in serverless)
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler() if HAS_SCHEDULER and not IS_SERVERLESS else None


def scheduled_scrape():
    """Background job: scrape all sources and merge into storage."""
    print(f"\n[SCHEDULER] Running scrape cycle at {now_iso()}")
    try:
        new_articles = scrape_all()
        existing = load_articles()
        merged = merge_articles(existing, new_articles)
        save_articles(merged)

        # Update scrape state
        state = load_scrape_state()
        for source_key in SCRAPERS:
            source_articles = [a for a in new_articles if a["source"] == source_key]
            state[source_key] = {
                "source": source_key,
                "last_scraped_at": now_iso(),
                "articles_found": len(source_articles),
                "status": "success" if source_articles else "no_new",
                "error_message": None,
            }
        save_scrape_state(state)
        print(f"[SCHEDULER] Scrape complete. {len(new_articles)} new, {len(merged)} total.")
    except Exception as e:
        print(f"[SCHEDULER] Scrape failed: {e}")


# ---------------------------------------------------------------------------
# App Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    ensure_data_dir()

    # Verify Supabase connection
    if check_connection():
        print("[STARTUP] Supabase connected.")
    else:
        print("[STARTUP] WARNING: Supabase connection failed! Check .env")

    if not IS_SERVERLESS and scheduler:
        # Run initial scrape if no data exists
        existing = load_articles()
        if not existing:
            print("[STARTUP] No articles found. Running initial scrape...")
            scheduled_scrape()

        # Start the 24-hour scheduler
        scheduler.add_job(scheduled_scrape, "interval", hours=24, id="scrape_cycle")
        scheduler.start()
        print("[STARTUP] Scheduler started — scraping every 24 hours.")
    else:
        print("[STARTUP] Serverless mode — scheduler disabled.")

    yield

    # Shutdown
    if not IS_SERVERLESS and scheduler:
        scheduler.shutdown(wait=False)
        print("[SHUTDOWN] Scheduler stopped.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Glaido AI News Aggregator",
    description="Scrapes and serves AI newsletter articles",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class SaveArticleRequest(BaseModel):
    article_id: str


# ---------------------------------------------------------------------------
# API Endpoints (per data_logic.md)
# ---------------------------------------------------------------------------
@app.get("/api/articles")
async def get_articles(source: str | None = Query(None), saved: bool = Query(False)):
    """
    Return all scraped articles.
    Optional filters: ?source=bens_bites  ?saved=true
    """
    articles = load_articles()

    if source:
        articles = [a for a in articles if a["source"] == source]

    if saved:
        saved_entries = load_saved_ids()
        saved_id_set = {s["article_id"] for s in saved_entries}
        articles = [a for a in articles if a["id"] in saved_id_set]

    # Calculate is_new for each article
    now = datetime.now(timezone.utc)
    for a in articles:
        if a.get("published_date"):
            try:
                pub = datetime.fromisoformat(a["published_date"])
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                a["is_new"] = (now - pub).total_seconds() < 86400
            except (ValueError, TypeError):
                a["is_new"] = False
        else:
            a["is_new"] = False

    saved_entries = load_saved_ids()
    saved_id_list = [s["article_id"] for s in saved_entries]
    state = load_scrape_state()

    return {
        "articles": articles,
        "saved_ids": saved_id_list,
        "last_updated": now_iso(),
        "sources": [
            {
                "name": key,
                "status": state.get(key, {}).get("status", "unknown"),
                "last_scraped": state.get(key, {}).get("last_scraped_at", "never"),
            }
            for key in SCRAPERS
        ],
    }


@app.get("/api/articles/saved")
async def get_saved_articles():
    """Return saved/bookmarked articles."""
    saved_entries = load_saved_ids()
    saved_id_set = {s["article_id"] for s in saved_entries}
    articles = load_articles()
    saved_articles = [a for a in articles if a["id"] in saved_id_set]
    return {"articles": saved_articles, "saved_ids": list(saved_id_set)}


@app.post("/api/articles/save")
async def save_article(req: SaveArticleRequest):
    """Bookmark an article via Supabase."""
    try:
        result = save_bookmark(req.article_id)
        return {"status": "saved", "article_id": req.article_id}
    except Exception as e:
        return {"status": "already_saved", "article_id": req.article_id}


@app.delete("/api/articles/save/{article_id}")
async def unsave_article(article_id: str):
    """Remove bookmark via Supabase."""
    try:
        remove_bookmark(article_id)
        return {"status": "unsaved", "article_id": article_id}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Article not saved")


@app.post("/api/scrape")
async def trigger_scrape(source: str | None = Query(None)):
    """Manually trigger a scrape cycle."""
    if source:
        if source not in SCRAPERS:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}")
        new_articles = scrape_source(source)
    else:
        new_articles = scrape_all()

    existing = load_articles()
    merged = merge_articles(existing, new_articles)
    save_articles(merged)

    # Update state
    state = load_scrape_state()
    sources_scraped = {source} if source else set(SCRAPERS.keys())
    for src in sources_scraped:
        src_articles = [a for a in new_articles if a["source"] == src]
        state[src] = {
            "source": src,
            "last_scraped_at": now_iso(),
            "articles_found": len(src_articles),
            "status": "success" if src_articles else "no_new",
            "error_message": None,
        }
    save_scrape_state(state)

    return {
        "status": "complete",
        "new_articles": len(new_articles),
        "total_articles": len(merged),
    }


@app.get("/api/status")
async def get_status():
    """Return scraper health & last-run status per source."""
    state = load_scrape_state()
    articles = load_articles()
    return {
        "total_articles": len(articles),
        "sources": {
            key: state.get(key, {"status": "never_run", "last_scraped_at": None})
            for key in SCRAPERS
        },
        "last_updated": now_iso(),
    }


# ---------------------------------------------------------------------------
# Serve Static Frontend
# ---------------------------------------------------------------------------
# Mount static files (CSS, JS, images)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve the brand assets
DESIGN_DIR = os.path.join(os.path.dirname(__file__), "DesignGuidelines")
if os.path.exists(DESIGN_DIR):
    app.mount("/brand", StaticFiles(directory=DESIGN_DIR), name="brand")


@app.get("/")
async def serve_index():
    """Serve the main dashboard HTML."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "Glaido AI News Aggregator API. Frontend not yet built."},
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("  GLAIDO AI NEWS AGGREGATOR")
    print("  http://localhost:8000")
    print("=" * 60 + "\n")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
