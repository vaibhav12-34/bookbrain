/**
 * BookBrain — Frontend Application
 * SPA with hash-based routing, API integration, and dynamic rendering.
 */

const API_BASE = 'http://127.0.0.1:8000/api';

// ============================================
// State Management
// ============================================
const state = {
    books: [],
    currentBook: null,
    chatMessages: [],
    loading: false,
    stats: { total_books: 0, processed_books: 0, total_authors: 0, total_categories: 0 },
};

// ============================================
// API Client
// ============================================
const api = {
    async get(endpoint) {
        try {
            const resp = await fetch(`${API_BASE}${endpoint}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error(`GET ${endpoint} failed:`, err);
            throw err;
        }
    },

    async post(endpoint, data) {
        try {
            const resp = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (err) {
            console.error(`POST ${endpoint} failed:`, err);
            throw err;
        }
    },
};

// ============================================
// Router
// ============================================
function getRoute() {
    const hash = window.location.hash || '#/';
    const parts = hash.slice(2).split('/');
    return { path: parts[0] || 'library', param: parts[1] || null };
}

function navigate(path) {
    window.location.hash = `#/${path}`;
}

window.addEventListener('hashchange', () => renderPage());

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// Stats
// ============================================
async function loadStats() {
    try {
        state.stats = await api.get('/stats/');
        const el = document.getElementById('stat-books');
        if (el) {
            el.innerHTML = `<span class="stat-number">${state.stats.total_books}</span> books`;
        }
    } catch (e) {
        // Stats endpoint might not be ready yet
    }
}

// ============================================
// Page Renderers
// ============================================

function renderPage() {
    const { path, param } = getRoute();

    // Update nav active state
    document.querySelectorAll('.nav-link').forEach(link => {
        const route = link.dataset.route;
        link.classList.toggle('active', route === path || (path === 'book' && route === 'library'));
    });

    const main = document.getElementById('main-content');

    switch (path) {
        case 'library':
        case '':
            renderLibrary(main);
            break;
        case 'book':
            renderBookDetail(main, param);
            break;
        case 'ask':
            renderAskAI(main);
            break;
        case 'upload':
            renderUpload(main);
            break;
        case 'scrape':
            renderScrape(main);
            break;
        default:
            renderLibrary(main);
    }

    loadStats();
}

// --- Library Page ---
async function renderLibrary(container) {
    container.innerHTML = `
        <div class="page-header">
            <h1 class="page-title">Your Library</h1>
            <p class="page-subtitle">Browse and explore your AI-analyzed book collection</p>
        </div>
        <div class="search-bar">
            <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" class="search-input" id="library-search" placeholder="Search books by title, author, or description...">
        </div>
        <div id="book-grid-container">
            <div class="loading-spinner" style="padding:48px;text-align:center;width:100%;">
                <div class="spinner"></div> Loading your books...
            </div>
        </div>
    `;

    const searchInput = document.getElementById('library-search');
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadBooks(searchInput.value), 350);
    });

    await loadBooks();
}

async function loadBooks(search = '') {
    const gridContainer = document.getElementById('book-grid-container');
    if (!gridContainer) return;

    try {
        const endpoint = search
            ? `/books/?search=${encodeURIComponent(search)}`
            : '/books/';
        const data = await api.get(endpoint);
        const books = data.results || data;
        state.books = books;

        if (books.length === 0) {
            gridContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📚</div>
                    <h2 class="empty-state-title">${search ? 'No matches found' : 'Your library is empty'}</h2>
                    <p class="empty-state-text">${search ? 'Try a different search term' : 'Start by adding books or discovering new ones!'}</p>
                    ${!search ? '<button class="btn btn-primary" onclick="navigate(\'upload\')">Add Your First Book</button>' : ''}
                </div>
            `;
            return;
        }

        gridContainer.innerHTML = `<div class="book-grid">${books.map(renderBookCard).join('')}</div>`;

        // Add click handlers
        gridContainer.querySelectorAll('.book-card').forEach(card => {
            card.addEventListener('click', () => navigate(`book/${card.dataset.id}`));
        });

    } catch (err) {
        gridContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h2 class="empty-state-title">Connection Error</h2>
                <p class="empty-state-text">Make sure the Django backend is running on port 8000.</p>
                <button class="btn btn-primary" onclick="renderLibrary(document.getElementById('main-content'))">Retry</button>
            </div>
        `;
    }
}

function renderBookCard(book) {
    const authors = Array.isArray(book.authors)
        ? book.authors.map(a => typeof a === 'string' ? a : a.name).join(', ')
        : '';
    const categories = Array.isArray(book.categories)
        ? book.categories.map(c => typeof c === 'string' ? c : c.name).slice(0, 3)
        : [];

    const coverHtml = book.cover_image_url
        ? `<img src="${book.cover_image_url}" alt="${escapeHtml(book.title)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'book-card-cover-placeholder\\'>📖</div>'">`
        : `<div class="book-card-cover-placeholder">📖</div>`;

    const ratingHtml = book.average_rating
        ? `<div class="book-card-badge">⭐ ${book.average_rating.toFixed(1)}</div>`
        : '';

    const tagsHtml = categories.length > 0
        ? categories.map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')
        : '';

    const processingTag = !book.is_processed
        ? `<span class="tag tag-processing">⏳ Processing</span>`
        : '';

    return `
        <div class="book-card" data-id="${book.id}" id="book-card-${book.id}">
            <div class="book-card-cover">
                ${coverHtml}
                ${ratingHtml}
            </div>
            <div class="book-card-body">
                <h3 class="book-card-title">${escapeHtml(book.title)}</h3>
                <p class="book-card-author">${escapeHtml(authors) || 'Unknown Author'}</p>
                <div class="book-card-tags">
                    ${processingTag}
                    ${tagsHtml}
                </div>
            </div>
        </div>
    `;
}

// --- Book Detail Page ---
async function renderBookDetail(container, bookId) {
    container.innerHTML = `
        <button class="btn btn-back" onclick="navigate('library')">← Back to Library</button>
        <div class="loading-spinner" style="padding:48px;text-align:center;">
            <div class="spinner"></div> Loading book details...
        </div>
    `;

    try {
        const book = await api.get(`/books/${bookId}/`);
        state.currentBook = book;

        const authors = book.authors.map(a => a.name || a).join(', ');
        const coverHtml = book.cover_image_url
            ? `<img src="${book.cover_image_url}" alt="${escapeHtml(book.title)}">`
            : `<div class="book-detail-cover-placeholder">📖</div>`;

        container.innerHTML = `
            <button class="btn btn-back" onclick="navigate('library')">← Back to Library</button>
            <div class="book-detail">
                <div class="book-detail-cover">${coverHtml}</div>
                <div class="book-detail-info">
                    <h1 class="book-detail-title">${escapeHtml(book.title)}</h1>
                    <p class="book-detail-authors">${escapeHtml(authors) || 'Unknown Author'}</p>

                    <div class="book-detail-meta">
                        ${book.publish_date ? `<div class="meta-item"><span class="meta-item-label">Published</span><span class="meta-item-value">${escapeHtml(book.publish_date)}</span></div>` : ''}
                        ${book.page_count ? `<div class="meta-item"><span class="meta-item-label">Pages</span><span class="meta-item-value">${book.page_count}</span></div>` : ''}
                        ${book.average_rating ? `<div class="meta-item"><span class="meta-item-label">Rating</span><span class="meta-item-value">⭐ ${book.average_rating.toFixed(1)}${book.ratings_count ? ` (${book.ratings_count})` : ''}</span></div>` : ''}
                        ${book.language ? `<div class="meta-item"><span class="meta-item-label">Language</span><span class="meta-item-value">${book.language.toUpperCase()}</span></div>` : ''}
                        ${book.publisher ? `<div class="meta-item"><span class="meta-item-label">Publisher</span><span class="meta-item-value">${escapeHtml(book.publisher)}</span></div>` : ''}
                    </div>

                    ${book.description ? `
                        <div class="glass-card">
                            <h3 class="glass-card-title"><span class="icon">📝</span> Description</h3>
                            <p class="description-text">${escapeHtml(book.description)}</p>
                        </div>
                    ` : ''}

                    ${book.is_processed ? renderAIInsights(book) : `
                        <div class="glass-card">
                            <h3 class="glass-card-title"><span class="icon">⏳</span> AI Processing</h3>
                            <p class="description-text">This book is still being analyzed by our AI engine. Check back shortly!</p>
                        </div>
                    `}

                    ${book.categories && book.categories.length > 0 ? `
                        <div class="glass-card">
                            <h3 class="glass-card-title"><span class="icon">🏷️</span> Categories</h3>
                            <div class="theme-list">
                                ${book.categories.map(c => `<span class="theme-tag">${escapeHtml(c.name || c)}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <div class="glass-card" id="recommendations-section">
                        <h3 class="glass-card-title"><span class="icon">✨</span> Recommended Books</h3>
                        <div id="recommendations-container">
                            <div class="loading-spinner"><div class="spinner"></div> Finding similar books...</div>
                        </div>
                    </div>

                    ${book.preview_link ? `
                        <a href="${book.preview_link}" target="_blank" class="btn btn-secondary" style="margin-top: var(--space-md);">
                            Preview on Google Books →
                        </a>
                    ` : ''}
                </div>
            </div>
        `;

        // Load recommendations
        loadRecommendations(bookId);

    } catch (err) {
        container.innerHTML = `
            <button class="btn btn-back" onclick="navigate('library')">← Back to Library</button>
            <div class="empty-state">
                <div class="empty-state-icon">😕</div>
                <h2 class="empty-state-title">Book not found</h2>
                <p class="empty-state-text">This book may have been removed or doesn't exist.</p>
            </div>
        `;
    }
}

function renderAIInsights(book) {
    let html = '';

    if (book.ai_summary || book.ai_sentiment || book.ai_reading_level || (book.ai_themes && book.ai_themes.length)) {
        html += `
            <div class="glass-card">
                <h3 class="glass-card-title"><span class="icon">🧠</span> AI Insights</h3>
                <div class="ai-insights">
                    ${book.ai_sentiment ? `
                        <div class="insight-card">
                            <div class="insight-label">Tone</div>
                            <div class="insight-value sentiment">${escapeHtml(book.ai_sentiment)}</div>
                        </div>
                    ` : ''}
                    ${book.ai_reading_level ? `
                        <div class="insight-card">
                            <div class="insight-label">Reading Level</div>
                            <div class="insight-value">${escapeHtml(book.ai_reading_level)}</div>
                        </div>
                    ` : ''}
                </div>
                ${book.ai_themes && book.ai_themes.length > 0 ? `
                    <div style="margin-top: var(--space-md);">
                        <div class="insight-label" style="margin-bottom: var(--space-sm);">Themes</div>
                        <div class="theme-list">
                            ${book.ai_themes.map(t => `<span class="theme-tag">${escapeHtml(t)}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                ${book.ai_summary ? `
                    <div style="margin-top: var(--space-lg);">
                        <div class="insight-label" style="margin-bottom: var(--space-sm);">AI Summary</div>
                        <p class="description-text">${escapeHtml(book.ai_summary)}</p>
                    </div>
                ` : ''}
            </div>
        `;
    }

    return html;
}

async function loadRecommendations(bookId) {
    const container = document.getElementById('recommendations-container');
    if (!container) return;

    try {
        const data = await api.get(`/books/${bookId}/recommendations/`);
        const recs = data.recommendations || [];

        if (recs.length === 0) {
            container.innerHTML = `<p class="description-text">Add more books to get personalized recommendations!</p>`;
            return;
        }

        container.innerHTML = `
            <div class="rec-grid">
                ${recs.map(rec => `
                    <div class="rec-card" onclick="navigate('book/${rec.id}')">
                        <div class="rec-card-cover">
                            ${rec.cover_image_url
                ? `<img src="${rec.cover_image_url}" alt="${escapeHtml(rec.title)}" onerror="this.parentElement.innerHTML='📖'">`
                : '📖'
            }
                        </div>
                        <div class="rec-card-info">
                            <div class="rec-card-title">${escapeHtml(rec.title)}</div>
                            <div class="rec-card-reason">${escapeHtml(rec.reason)}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<p class="description-text">Could not load recommendations.</p>`;
    }
}

// --- Ask AI Page ---
function renderAskAI(container) {
    container.innerHTML = `
        <div class="ask-container">
            <div class="page-header">
                <h1 class="page-title">Ask AI About Books</h1>
                <p class="page-subtitle">Get intelligent answers, summaries, genre analysis, and recommendations</p>
            </div>

            <!-- Quick Action Chips -->
            <div class="qa-quick-actions" id="qa-quick-actions">
                <span class="qa-chip" onclick="askQuickQuestion('What books do you have in the library?')">📚 Library overview</span>
                <span class="qa-chip" onclick="askQuickQuestion('Summarize the most popular book')">📝 Summarize a book</span>
                <span class="qa-chip" onclick="askQuickQuestion('What genres are available?')">🏷️ Show genres</span>
                <span class="qa-chip" onclick="askQuickQuestion('Recommend a Hindi book')">🇮🇳 Hindi books</span>
                <span class="qa-chip" onclick="askQuickQuestion('Recommend books similar to Godan')">✨ Get recommendations</span>
                <span class="qa-chip" onclick="askQuickQuestion('Tell me about Premchand')">👤 About an author</span>
            </div>

            <!-- Question Input -->
            <form class="qa-input-section glass-card" id="ask-form" onsubmit="handleAskSubmit(event)">
                <div class="qa-input-row">
                    <div class="qa-input-wrapper">
                        <svg class="qa-input-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        <input type="text" class="qa-input" id="ask-input" placeholder="Ask anything about your books..." autocomplete="off">
                    </div>
                    <button type="submit" class="btn btn-primary qa-submit-btn" id="ask-submit-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                        Ask
                    </button>
                </div>
            </form>

            <!-- Answer Results Area -->
            <div id="qa-results-area">
                ${state.chatMessages.length === 0 ? renderQAWelcome() : renderQAHistory()}
            </div>
        </div>
    `;

    document.getElementById('ask-input').focus();
}

function renderQAWelcome() {
    return `
        <div class="qa-welcome">
            <div class="qa-welcome-icon">🧠</div>
            <h2 class="qa-welcome-title">Your AI Book Assistant</h2>
            <p class="qa-welcome-text">Ask me questions and I'll search your library to provide answers with book summaries, genre analysis, and personalized recommendations.</p>
            <div class="qa-feature-grid">
                <div class="qa-feature-card">
                    <span class="qa-feature-icon">📝</span>
                    <span class="qa-feature-label">Summaries</span>
                    <span class="qa-feature-desc">AI-generated book summaries</span>
                </div>
                <div class="qa-feature-card">
                    <span class="qa-feature-icon">🏷️</span>
                    <span class="qa-feature-label">Genres & Themes</span>
                    <span class="qa-feature-desc">Detect categories and themes</span>
                </div>
                <div class="qa-feature-card">
                    <span class="qa-feature-icon">✨</span>
                    <span class="qa-feature-label">Recommendations</span>
                    <span class="qa-feature-desc">Find similar books to read</span>
                </div>
                <div class="qa-feature-card">
                    <span class="qa-feature-icon">💬</span>
                    <span class="qa-feature-label">Q&A</span>
                    <span class="qa-feature-desc">Ask anything about your library</span>
                </div>
            </div>
        </div>
    `;
}

function renderQAHistory() {
    return state.chatMessages.map((msg, idx) => {
        if (msg.role === 'user') {
            return `<div class="qa-question-banner"><span class="qa-q-label">Q</span> ${escapeHtml(msg.content)}</div>`;
        }
        return renderQAResult(msg, idx);
    }).join('');
}

function renderQAResult(msg, idx) {
    const confClass = msg.confidence > 0.6 ? 'confidence-high'
        : msg.confidence > 0.3 ? 'confidence-medium' : 'confidence-low';
    const confLabel = msg.confidence > 0.6 ? 'High' : msg.confidence > 0.3 ? 'Medium' : 'Low';
    const confPercent = msg.confidence !== undefined ? (msg.confidence * 100).toFixed(0) : null;

    // Build matched books section
    let matchedBooksHtml = '';
    if (msg.matched_books && msg.matched_books.length > 0) {
        matchedBooksHtml = `
            <div class="qa-section">
                <h3 class="qa-section-title"><span class="icon">📚</span> Matched Books</h3>
                <div class="qa-book-cards">
                    ${msg.matched_books.map(book => renderQABookCard(book)).join('')}
                </div>
            </div>
        `;
    }

    // Build recommendations section
    let recsHtml = '';
    if (msg.recommendations && msg.recommendations.length > 0) {
        recsHtml = `
            <div class="qa-section">
                <h3 class="qa-section-title"><span class="icon">✨</span> You Might Also Like</h3>
                <div class="qa-rec-strip">
                    ${msg.recommendations.map(rec => `
                        <div class="qa-rec-item" onclick="navigate('book/${rec.id}')">
                            <div class="qa-rec-cover">
                                ${rec.cover_image_url
                ? `<img src="${rec.cover_image_url}" alt="${escapeHtml(rec.title)}" onerror="this.parentElement.innerHTML='📖'">`
                : '<span>📖</span>'
            }
                            </div>
                            <div class="qa-rec-info">
                                <div class="qa-rec-title">${escapeHtml(rec.title)}</div>
                                <div class="qa-rec-authors">${(rec.authors || []).join(', ')}</div>
                                ${rec.categories && rec.categories.length > 0 ? `
                                    <div class="qa-rec-cats">${rec.categories.slice(0, 2).map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}</div>
                                ` : ''}
                                <div class="qa-rec-reason">${escapeHtml(rec.reason)}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    return `
        <div class="qa-result-block" style="animation: fadeInUp 0.4s ease">
            <!-- Answer Section -->
            <div class="qa-answer-card glass-card">
                <div class="qa-answer-header">
                    <div class="qa-answer-label"><span class="qa-ai-dot"></span> BookBrain AI</div>
                    ${confPercent !== null ? `<span class="confidence-badge ${confClass}">Confidence: ${confLabel} (${confPercent}%)</span>` : ''}
                </div>
                <div class="qa-answer-body">${escapeHtml(msg.content)}</div>
                ${msg.sources && msg.sources.length > 0 ? `
                    <div class="qa-answer-sources">
                        <span class="qa-sources-label">Sources:</span>
                        ${msg.sources.map(s => `
                            <span class="chat-source" onclick="navigate('book/${s.book_id}')">
                                📖 ${escapeHtml(s.book_title)}
                            </span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>

            ${matchedBooksHtml}
            ${recsHtml}
        </div>
    `;
}

function renderQABookCard(book) {
    const authors = (book.authors || []).join(', ');
    const themes = book.ai_themes || [];
    const categories = book.categories || [];

    return `
        <div class="qa-book-card" onclick="navigate('book/${book.id}')">
            <div class="qa-book-cover">
                ${book.cover_image_url
            ? `<img src="${book.cover_image_url}" alt="${escapeHtml(book.title)}" onerror="this.parentElement.innerHTML='<span>📖</span>'">`
            : '<span>📖</span>'
        }
            </div>
            <div class="qa-book-details">
                <h4 class="qa-book-title">${escapeHtml(book.title)}</h4>
                <p class="qa-book-author">${escapeHtml(authors) || 'Unknown Author'}</p>

                <!-- Metadata Pills -->
                <div class="qa-book-meta-row">
                    ${book.ai_sentiment ? `<span class="qa-pill qa-pill-sentiment">${escapeHtml(book.ai_sentiment)}</span>` : ''}
                    ${book.ai_reading_level ? `<span class="qa-pill qa-pill-level">${escapeHtml(book.ai_reading_level)}</span>` : ''}
                    ${book.language ? `<span class="qa-pill">${book.language.toUpperCase()}</span>` : ''}
                    ${book.page_count ? `<span class="qa-pill">${book.page_count} pages</span>` : ''}
                    ${book.average_rating ? `<span class="qa-pill qa-pill-rating">⭐ ${book.average_rating.toFixed(1)}</span>` : ''}
                </div>

                <!-- Genres / Categories -->
                ${categories.length > 0 ? `
                    <div class="qa-book-section">
                        <span class="qa-mini-label">Genre</span>
                        <div class="qa-tag-row">
                            ${categories.map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Themes -->
                ${themes.length > 0 ? `
                    <div class="qa-book-section">
                        <span class="qa-mini-label">Themes</span>
                        <div class="qa-tag-row">
                            ${themes.map(t => `<span class="theme-tag">${escapeHtml(t)}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- AI Summary -->
                ${book.ai_summary ? `
                    <div class="qa-book-section">
                        <span class="qa-mini-label">AI Summary</span>
                        <p class="qa-book-summary">${escapeHtml(book.ai_summary)}</p>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

function askQuickQuestion(question) {
    const input = document.getElementById('ask-input');
    if (input) {
        input.value = question;
        input.focus();
        // Auto-submit
        document.getElementById('ask-form').dispatchEvent(new Event('submit'));
    }
}

async function handleAskSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('ask-input');
    const question = input.value.trim();
    if (!question) return;

    // Add user message
    state.chatMessages.push({ role: 'user', content: question });
    input.value = '';

    // Show loading state
    const resultsArea = document.getElementById('qa-results-area');
    resultsArea.innerHTML = renderQAHistory() + `
        <div class="qa-result-block" style="animation: fadeInUp 0.4s ease">
            <div class="qa-answer-card glass-card">
                <div class="qa-answer-header">
                    <div class="qa-answer-label"><span class="qa-ai-dot"></span> BookBrain AI</div>
                </div>
                <div class="qa-loading">
                    <div class="spinner"></div>
                    <span>Searching your library and generating insights...</span>
                </div>
            </div>
        </div>
    `;

    // Hide quick actions after first question
    const quickActions = document.getElementById('qa-quick-actions');
    if (quickActions) quickActions.style.display = 'none';

    // Disable submit
    const btn = document.getElementById('ask-submit-btn');
    btn.disabled = true;

    try {
        const data = await api.post('/books/ask/', { question });
        state.chatMessages.push({
            role: 'assistant',
            content: data.answer,
            sources: data.sources,
            confidence: data.confidence,
            matched_books: data.matched_books || [],
            recommendations: data.recommendations || [],
        });
    } catch (err) {
        state.chatMessages.push({
            role: 'assistant',
            content: `Sorry, I encountered an error: ${err.message}. Make sure you have books in your library first!`,
            sources: [],
            matched_books: [],
            recommendations: [],
        });
    }

    // Re-render results
    resultsArea.innerHTML = renderQAHistory();
    btn.disabled = false;
    input.focus();

    // Scroll to latest result
    const blocks = resultsArea.querySelectorAll('.qa-result-block');
    if (blocks.length > 0) {
        blocks[blocks.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

window.askQuickQuestion = askQuickQuestion;

// --- Upload Page ---
function renderUpload(container) {
    container.innerHTML = `
        <div class="form-container">
            <div class="page-header">
                <h1 class="page-title">Add Books</h1>
                <p class="page-subtitle">Search and add books by title or ISBN</p>
            </div>
            <form class="glass-card" id="upload-form" onsubmit="handleUpload(event)">
                <div class="form-group">
                    <label class="form-label" for="upload-query">Book Title or ISBN</label>
                    <input type="text" class="form-input" id="upload-query" placeholder="e.g., The Great Gatsby, or 9780743273565" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="upload-type">Search Type</label>
                    <select class="form-input" id="upload-type">
                        <option value="title">Search by Title</option>
                        <option value="isbn">Search by ISBN</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" id="upload-submit" style="width:100%;">
                    🔍 Search & Add Book
                </button>
            </form>
            <div id="upload-results" style="margin-top: var(--space-xl);"></div>
        </div>
    `;
}

async function handleUpload(e) {
    e.preventDefault();
    const query = document.getElementById('upload-query').value.trim();
    const searchType = document.getElementById('upload-type').value;
    const btn = document.getElementById('upload-submit');
    const results = document.getElementById('upload-results');

    if (!query) return;

    btn.disabled = true;
    btn.textContent = '⏳ Searching...';
    results.innerHTML = '<div class="loading-spinner" style="padding:24px;"><div class="spinner"></div> Scraping book data from multiple sources...</div>';

    try {
        const data = await api.post('/books/upload/', { query, search_type: searchType });
        showToast(data.message, 'success');

        const books = data.books || [];
        results.innerHTML = `
            <h3 style="color: var(--success); margin-bottom: var(--space-md);">✓ ${books.length} book(s) added successfully!</h3>
            <div class="book-grid">
                ${books.map(renderBookCard).join('')}
            </div>
            <p style="color: var(--text-muted); margin-top: var(--space-md); font-size: var(--font-size-sm);">
                AI insights are being generated in the background...
            </p>
        `;

        // Add click handlers
        results.querySelectorAll('.book-card').forEach(card => {
            card.addEventListener('click', () => navigate(`book/${card.dataset.id}`));
        });

    } catch (err) {
        showToast(err.message, 'error');
        results.innerHTML = `<div class="glass-card" style="border-color: var(--error);">${escapeHtml(err.message)}</div>`;
    }

    btn.disabled = false;
    btn.textContent = '🔍 Search & Add Book';
}

// --- Scrape/Discover Page ---
function renderScrape(container) {
    container.innerHTML = `
        <div class="form-container">
            <div class="page-header">
                <h1 class="page-title">Discover Books</h1>
                <p class="page-subtitle">Scrape and import books by topic from public APIs</p>
            </div>
            <form class="glass-card" id="scrape-form" onsubmit="handleScrape(event)">
                <div class="form-group">
                    <label class="form-label" for="scrape-topic">Topic or Category</label>
                    <input type="text" class="form-input" id="scrape-topic" placeholder="e.g., science fiction, machine learning, fantasy" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="scrape-count">Number of Books</label>
                    <select class="form-input" id="scrape-count">
                        <option value="5">5 books</option>
                        <option value="10" selected>10 books</option>
                        <option value="20">20 books</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" id="scrape-submit" style="width:100%;">
                    🌐 Discover Books
                </button>
            </form>
            <div id="scrape-results" style="margin-top: var(--space-xl);"></div>

            <div class="glass-card" style="margin-top: var(--space-xl);">
                <h3 class="glass-card-title"><span class="icon">💡</span> Popular Topics</h3>
                <div class="theme-list">
                    ${['Classic Literature', 'Science Fiction', 'Fantasy', 'Machine Learning',
            'Philosophy', 'History', 'Psychology', 'Economics', 'Mystery',
            'Biography', 'Self Help', 'Programming'].map(topic =>
                `<span class="theme-tag" style="cursor:pointer;" onclick="document.getElementById('scrape-topic').value='${topic}'">${topic}</span>`
            ).join('')}
                </div>
            </div>
        </div>
    `;
}

async function handleScrape(e) {
    e.preventDefault();
    const topic = document.getElementById('scrape-topic').value.trim();
    const maxResults = parseInt(document.getElementById('scrape-count').value);
    const btn = document.getElementById('scrape-submit');
    const results = document.getElementById('scrape-results');

    if (!topic) return;

    btn.disabled = true;
    btn.textContent = '⏳ Scraping...';
    results.innerHTML = `
        <div class="loading-spinner" style="padding:24px;">
            <div class="spinner"></div> Scraping "${escapeHtml(topic)}" from Open Library & Google Books...
        </div>
    `;

    try {
        const data = await api.post('/books/scrape/', { topic, max_results: maxResults });
        showToast(data.message, 'success');

        const books = data.books || [];
        results.innerHTML = `
            <h3 style="color: var(--success); margin-bottom: var(--space-md);">✓ Discovered ${books.length} book(s)!</h3>
            <div class="book-grid">
                ${books.map(renderBookCard).join('')}
            </div>
            <p style="color: var(--text-muted); margin-top: var(--space-md); font-size: var(--font-size-sm);">
                AI insights are being generated in the background. Refresh the page in a moment to see insights.
            </p>
        `;

        results.querySelectorAll('.book-card').forEach(card => {
            card.addEventListener('click', () => navigate(`book/${card.dataset.id}`));
        });

    } catch (err) {
        showToast(err.message, 'error');
        results.innerHTML = `<div class="glass-card" style="border-color: var(--error);">${escapeHtml(err.message)}</div>`;
    }

    btn.disabled = false;
    btn.textContent = '🌐 Discover Books';
}

// ============================================
// Utilities
// ============================================
function escapeHtml(text) {
    if (!text) return '';
    // First decode any HTML numeric entities (&#2325; etc.) to actual Unicode
    let str = String(text).replace(/&#(\d+);/g, (_, code) => String.fromCharCode(code));
    // Then safely escape for HTML insertion
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    renderPage();

    // Brand click navigates home
    document.getElementById('nav-brand').addEventListener('click', () => navigate('library'));
});

// Make navigate available globally for onclick handlers
window.navigate = navigate;
