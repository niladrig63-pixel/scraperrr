/**
 * app.js — Glaido AI News Aggregator: Frontend Application
 * 
 * Handles: data fetching, bento-grid rendering, filtering,
 * bookmarking, toast notifications, and UI interactions.
 */

// ============================================================
// State
// ============================================================
const state = {
    articles: [],
    savedIds: new Set(),
    currentFilter: 'all',  // 'all' | 'bens_bites' | 'the_rundown' | 'saved'
    loading: true,
};

// ============================================================
// DOM References
// ============================================================
const $grid = document.getElementById('bentoGrid');
const $loading = document.getElementById('loadingState');
const $empty = document.getElementById('emptyState');
const $filterTabs = document.getElementById('filterTabs');
const $articleCount = document.getElementById('articleCount');
const $btnRefresh = document.getElementById('btnRefresh');
const $btnScrape = document.getElementById('btnScrape');
const $toastContainer = document.getElementById('toastContainer');

// ============================================================
// API
// ============================================================
const API = {
    async getArticles(source = null, saved = false) {
        let url = '/api/articles?';
        if (source && source !== 'all' && source !== 'saved') url += `source=${source}&`;
        if (saved) url += 'saved=true&';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    },

    async saveArticle(articleId) {
        const res = await fetch('/api/articles/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_id: articleId }),
        });
        return res.json();
    },

    async unsaveArticle(articleId) {
        const res = await fetch(`/api/articles/save/${articleId}`, {
            method: 'DELETE',
        });
        return res.json();
    },

    async triggerScrape() {
        const res = await fetch('/api/scrape', { method: 'POST' });
        return res.json();
    },
};

// ============================================================
// Rendering
// ============================================================
function formatDate(isoString) {
    if (!isoString) return 'Recently';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffH = Math.floor(diffMs / 3600000);
        const diffD = Math.floor(diffMs / 86400000);

        if (diffH < 1) return 'Just now';
        if (diffH < 24) return `${diffH}h ago`;
        if (diffD < 7) return `${diffD}d ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return 'Recently';
    }
}

function createArticleCard(article, index) {
    const isHero = index === 0;
    const isSaved = state.savedIds.has(article.id);
    const isNew = article.is_new;

    const card = document.createElement('div');
    card.className = `article-card${isHero ? ' hero' : ''}`;
    card.style.animationDelay = `${index * 0.05}s`;
    card.dataset.id = article.id;

    // Build thumbnail HTML
    let thumbnailHTML = '';
    if (article.thumbnail) {
        thumbnailHTML = `<img class="card-thumbnail" src="${escapeHtml(article.thumbnail)}" alt="" loading="lazy" onerror="this.style.display='none'">`;
    }

    // Build badges
    let badgesHTML = `<span class="source-badge">${escapeHtml(article.source_display)}</span>`;
    if (isNew) {
        badgesHTML += `<span class="new-badge">● New</span>`;
    }

    card.innerHTML = `
        ${thumbnailHTML}
        <div class="card-content">
            <div class="card-header">
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                    ${badgesHTML}
                </div>
                <span class="card-date">${formatDate(article.published_date)}</span>
            </div>
            <h3 class="card-title">
                <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer">
                    ${escapeHtml(article.title)}
                </a>
            </h3>
            ${article.subtitle ? `<p class="card-subtitle">${escapeHtml(article.subtitle)}</p>` : ''}
            <div class="card-footer">
                <span class="card-author">${article.author ? escapeHtml(article.author) : ''}</span>
                <button class="btn-save ${isSaved ? 'saved' : ''}" data-id="${article.id}" title="${isSaved ? 'Remove bookmark' : 'Save article'}">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="${isSaved ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;

    return card;
}

function renderArticles(articles) {
    $grid.innerHTML = '';

    if (articles.length === 0) {
        $grid.classList.add('hidden');
        $empty.classList.remove('hidden');
        $articleCount.textContent = '0 articles';
        return;
    }

    $empty.classList.add('hidden');
    $grid.classList.remove('hidden');

    articles.forEach((article, i) => {
        $grid.appendChild(createArticleCard(article, i));
    });

    $articleCount.textContent = `${articles.length} article${articles.length !== 1 ? 's' : ''}`;

    // Attach save button listeners
    $grid.querySelectorAll('.btn-save').forEach(btn => {
        btn.addEventListener('click', handleSaveClick);
    });
}

function getFilteredArticles() {
    let filtered = [...state.articles];

    if (state.currentFilter === 'saved') {
        filtered = filtered.filter(a => state.savedIds.has(a.id));
    } else if (state.currentFilter !== 'all') {
        filtered = filtered.filter(a => a.source === state.currentFilter);
    }

    return filtered;
}

// ============================================================
// Event Handlers
// ============================================================
async function handleSaveClick(e) {
    const btn = e.currentTarget;
    const articleId = btn.dataset.id;
    const isSaved = state.savedIds.has(articleId);

    try {
        if (isSaved) {
            await API.unsaveArticle(articleId);
            state.savedIds.delete(articleId);
            btn.classList.remove('saved');
            btn.querySelector('svg').setAttribute('fill', 'none');
            btn.title = 'Save article';
            showToast('Article removed from saved', 'success');
        } else {
            await API.saveArticle(articleId);
            state.savedIds.add(articleId);
            btn.classList.add('saved');
            btn.querySelector('svg').setAttribute('fill', 'currentColor');
            btn.title = 'Remove bookmark';
            showToast('Article saved!', 'success');
        }

        // If on saved filter, re-render to remove unsaved cards
        if (state.currentFilter === 'saved') {
            renderArticles(getFilteredArticles());
        }
    } catch (err) {
        showToast('Failed to update bookmark', 'error');
        console.error(err);
    }
}

async function handleRefresh() {
    $btnRefresh.classList.add('spinning');
    try {
        await loadArticles();
        showToast('Articles refreshed', 'success');
    } catch (err) {
        showToast('Failed to refresh', 'error');
    }
    $btnRefresh.classList.remove('spinning');
}

async function handleScrape() {
    $btnScrape.classList.add('loading');
    $btnScrape.querySelector('span').textContent = 'Scraping...';
    try {
        const result = await API.triggerScrape();
        showToast(`Scrape complete: ${result.new_articles} new articles found`, 'success');
        await loadArticles();
    } catch (err) {
        showToast('Scrape failed — check console', 'error');
        console.error(err);
    }
    $btnScrape.classList.remove('loading');
    $btnScrape.querySelector('span').textContent = 'Scrape Now';
}

function handleFilterClick(e) {
    const tab = e.target.closest('.filter-tab');
    if (!tab) return;

    $filterTabs.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    state.currentFilter = tab.dataset.source;
    renderArticles(getFilteredArticles());
}

// ============================================================
// Data Loading
// ============================================================
async function loadArticles() {
    try {
        const data = await API.getArticles();
        state.articles = data.articles || [];
        state.savedIds = new Set(data.saved_ids || []);

        $loading.classList.add('hidden');
        renderArticles(getFilteredArticles());
    } catch (err) {
        $loading.classList.add('hidden');
        $empty.classList.remove('hidden');
        showToast('Failed to load articles', 'error');
        console.error(err);
    }
}

// ============================================================
// Toast Notifications
// ============================================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success'
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#BFF549" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';

    toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
    $toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = '0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// Utilities
// ============================================================
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ============================================================
// Initialize
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // Event listeners
    $btnRefresh.addEventListener('click', handleRefresh);
    $btnScrape.addEventListener('click', handleScrape);
    $filterTabs.addEventListener('click', handleFilterClick);

    // Initial load
    loadArticles();
});
