-- ============================================================
-- Glaido AI News Aggregator — Supabase Schema
-- Run this in your Supabase SQL Editor:
--   https://unrwcfeifeffmtegkjke.supabase.co → SQL Editor
-- ============================================================

-- 1. Articles table
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    source_display TEXT NOT NULL,
    author TEXT,
    published_date TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    thumbnail TEXT,
    summary TEXT,
    tags TEXT[] DEFAULT '{}',
    is_new BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Saved articles (bookmarks)
CREATE TABLE IF NOT EXISTS saved_articles (
    id SERIAL PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(article_id)
);

-- 3. Scrape state tracking
CREATE TABLE IF NOT EXISTS scrape_state (
    source TEXT PRIMARY KEY,
    last_scraped_at TIMESTAMPTZ,
    articles_found INTEGER DEFAULT 0,
    status TEXT DEFAULT 'never_run',
    error_message TEXT
);

-- 4. Enable Row Level Security (allow anon access for MVP)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_state ENABLE ROW LEVEL SECURITY;

-- Allow anon read/write for MVP (tighten later with auth)
CREATE POLICY "Allow all access to articles" ON articles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to saved_articles" ON saved_articles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to scrape_state" ON scrape_state FOR ALL USING (true) WITH CHECK (true);

-- 5. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_saved_article_id ON saved_articles(article_id);
