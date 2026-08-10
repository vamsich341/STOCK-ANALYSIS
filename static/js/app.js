// Stock Analysis Dashboard - Main JavaScript

// App State
const state = {
    currentUser: null,
    currentView: 'dashboard',
    watchlists: [],
    selectedWatchlist: null
};

// API Base URL
const API_URL = window.location.origin;

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    checkExistingUser();
});

function initializeApp() {
    console.log('Initializing Stock Analysis Dashboard...');
    showView('dashboard');
}

// Event Listeners
function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = e.currentTarget.dataset.view;
            showView(view);
        });
    });

    // Login
    document.getElementById('loginBtn').addEventListener('click', () => openModal('loginModal'));
    document.getElementById('loginSubmitBtn').addEventListener('click', handleLogin);

    // Quick Search
    document.getElementById('quickSearchBtn').addEventListener('click', handleQuickSearch);
    document.getElementById('quickSearchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleQuickSearch();
    });

    // Watchlist
    document.getElementById('createWatchlistBtn').addEventListener('click', () => openModal('createWatchlistModal'));
    document.getElementById('createWatchlistSubmitBtn').addEventListener('click', handleCreateWatchlist);
    document.getElementById('addTickerBtn').addEventListener('click', () => openModal('addTickerModal'));
    document.getElementById('addTickerSubmitBtn').addEventListener('click', handleAddTicker);

    // Analysis
    document.getElementById('analyzePerformanceBtn').addEventListener('click', handleAnalyzePerformance);
    document.getElementById('compareStocksBtn').addEventListener('click', handleCompareStocks);
    document.getElementById('summarizeNewsBtn').addEventListener('click', handleSummarizeNews);

    // News
    document.getElementById('newsSearchBtn').addEventListener('click', handleNewsSearch);
    document.getElementById('newsSearchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleNewsSearch();
    });

    // Modal Close Buttons
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            closeModal(modal.id);
        });
    });

    // Click outside modal to close
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// View Management
function showView(viewName) {
    // Update navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.view === viewName) {
            btn.classList.add('active');
        }
    });

    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}View`).classList.add('active');

    state.currentView = viewName;

    // Load data for view
    if (viewName === 'watchlist' && state.currentUser) {
        loadWatchlists();
    } else if (viewName === 'dashboard') {
        updateDashboardStats();
    }
}

// Modal Management
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Loading Overlay
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// User Management
function checkExistingUser() {
    const savedUser = localStorage.getItem('stockAnalysisUser');
    if (savedUser) {
        state.currentUser = JSON.parse(savedUser);
        updateUserDisplay();
        updateDashboardStats();
    }
}

function updateUserDisplay() {
    if (state.currentUser) {
        document.getElementById('username').textContent = state.currentUser.username;
        document.getElementById('loginBtn').textContent = 'Logout';
        document.getElementById('loginBtn').onclick = handleLogout;
    }
}

async function handleLogin() {
    const username = document.getElementById('usernameInput').value.trim();
    const email = document.getElementById('emailInput').value.trim();

    if (!username || !email) {
        showToast('Please enter username and email', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email })
        });

        const data = await response.json();

        if (response.ok || response.status === 409) {
            // User created or already exists, now fetch the user
            const userResponse = await fetch(`${API_URL}/api/users?email=${email}`);
            if (!userResponse.ok) {
                // If we can't fetch by email, use the data from creation
                state.currentUser = data;
            } else {
                state.currentUser = await userResponse.json();
            }
            
            localStorage.setItem('stockAnalysisUser', JSON.stringify(state.currentUser));
            updateUserDisplay();
            closeModal('loginModal');
            showToast(`Welcome, ${username}!`, 'success');
            updateDashboardStats();
        } else {
            showToast('Failed to login', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Login failed. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

function handleLogout() {
    localStorage.removeItem('stockAnalysisUser');
    state.currentUser = null;
    document.getElementById('username').textContent = 'Guest';
    document.getElementById('loginBtn').textContent = 'Login';
    document.getElementById('loginBtn').onclick = () => openModal('loginModal');
    showToast('Logged out successfully', 'success');
    updateDashboardStats();
}

// Quick Search
async function handleQuickSearch() {
    const ticker = document.getElementById('quickSearchInput').value.trim().toUpperCase();
    
    if (!ticker) {
        showToast('Please enter a ticker symbol', 'warning');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/stocks/${ticker}/quote`);
        
        if (!response.ok) {
            showToast('Stock not found', 'error');
            hideLoading();
            return;
        }

        const quote = await response.json();
        displayStockCard(quote);
    } catch (error) {
        console.error('Search error:', error);
        showToast('Failed to fetch stock data', 'error');
    } finally {
        hideLoading();
    }
}

function displayStockCard(quote) {
    const container = document.getElementById('quickSearchResults');
    
    const change = quote.change || 0;
    const changePercent = quote.change_percent || 0;
    const isPositive = change >= 0;
    
    container.innerHTML = `
        <div class="stock-card">
            <div class="stock-header">
                <div>
                    <div class="stock-symbol">${quote.ticker}</div>
                    <div class="stock-change">
                        <span class="change-badge ${isPositive ? 'change-positive' : 'change-negative'}">
                            ${isPositive ? '▲' : '▼'} ${Math.abs(change).toFixed(2)} (${changePercent.toFixed(2)}%)
                        </span>
                    </div>
                </div>
                <div class="stock-price ${isPositive ? 'price-positive' : 'price-negative'}">
                    ${(quote.price || 0).toFixed(2)}
                </div>
            </div>
            <div class="stock-details">
                <div class="detail-item">
                    <span class="detail-label">Open</span>
                    <span class="detail-value">${(quote.open || 0).toFixed(2)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">High</span>
                    <span class="detail-value">${(quote.high || 0).toFixed(2)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Low</span>
                    <span class="detail-value">${(quote.low || 0).toFixed(2)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Volume</span>
                    <span class="detail-value">${formatNumber(quote.volume || 0)}</span>
                </div>
            </div>
        </div>
    `;
}

// Watchlist Management
async function loadWatchlists() {
    if (!state.currentUser) {
        document.getElementById('watchlistsContainer').innerHTML = `
            <div class="empty-state">
                <p>Please login to manage watchlists</p>
            </div>
        `;
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/users/${state.currentUser.user_id}/watchlists`);
        const watchlists = await response.json();
        
        state.watchlists = watchlists;
        displayWatchlists(watchlists);
    } catch (error) {
        console.error('Error loading watchlists:', error);
        showToast('Failed to load watchlists', 'error');
    } finally {
        hideLoading();
    }
}

function displayWatchlists(watchlists) {
    const container = document.getElementById('watchlistsContainer');
    
    if (watchlists.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-star" style="font-size: 3rem; color: var(--text-secondary); margin-bottom: 1rem;"></i>
                <p>No watchlists yet. Create your first one!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = watchlists.map(w => `
        <div class="watchlist-card" onclick="selectWatchlist(${w.watchlist_id})">
            <h3><i class="fas fa-folder"></i> ${w.name}</h3>
            <p>${w.description || 'No description'}</p>
            <div class="watchlist-meta">
                <span><i class="fas fa-chart-line"></i> ${w.ticker_count || 0} stocks</span>
                <span><i class="fas fa-calendar"></i> ${new Date(w.created_at).toLocaleDateString()}</span>
            </div>
        </div>
    `).join('');
}

window.selectWatchlist = async function(watchlistId) {
    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/watchlists/${watchlistId}`);
        const watchlist = await response.json();
        
        state.selectedWatchlist = watchlist;
        displayWatchlistDetail(watchlist);
    } catch (error) {
        console.error('Error loading watchlist:', error);
        showToast('Failed to load watchlist', 'error');
    } finally {
        hideLoading();
    }
};

function displayWatchlistDetail(watchlist) {
    document.getElementById('watchlistTitle').textContent = watchlist.name;
    document.getElementById('watchlistDetail').style.display = 'block';
    
    const container = document.getElementById('watchlistTickers');
    
    if (!watchlist.tickers || watchlist.tickers.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No stocks in this watchlist yet</p>
            </div>
        `;
        return;
    }

    container.innerHTML = watchlist.tickers.map(t => `
        <div class="ticker-card">
            <div class="ticker-header">
                <div class="ticker-info">
                    <h4>${t.ticker}</h4>
                    <span class="ticker-company">${t.company_name || 'Loading...'}</span>
                </div>
                <div class="ticker-actions">
                    <button onclick="viewTickerDetails('${t.ticker}')" title="View Details">
                        <i class="fas fa-chart-line"></i>
                    </button>
                    <button onclick="removeTickerFromWatchlist(${watchlist.watchlist_id}, '${t.ticker}')" title="Remove">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            ${t.thesis ? `
                <div class="ticker-thesis">
                    <strong>Investment Thesis:</strong>
                    <p>${t.thesis}</p>
                </div>
            ` : ''}
            ${t.target_price ? `
                <div class="detail-item">
                    <span class="detail-label">Target Price</span>
                    <span class="detail-value">${parseFloat(t.target_price).toFixed(2)}</span>
                </div>
            ` : ''}
        </div>
    `).join('');
}

async function handleCreateWatchlist() {
    if (!state.currentUser) {
        showToast('Please login first', 'warning');
        return;
    }

    const name = document.getElementById('watchlistName').value.trim();
    const description = document.getElementById('watchlistDesc').value.trim();

    if (!name) {
        showToast('Please enter a watchlist name', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/users/${state.currentUser.user_id}/watchlists`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });

        if (response.ok) {
            showToast('Watchlist created successfully', 'success');
            closeModal('createWatchlistModal');
            document.getElementById('watchlistName').value = '';
            document.getElementById('watchlistDesc').value = '';
            loadWatchlists();
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to create watchlist', 'error');
        }
    } catch (error) {
        console.error('Error creating watchlist:', error);
        showToast('Failed to create watchlist', 'error');
    } finally {
        hideLoading();
    }
}

async function handleAddTicker() {
    if (!state.selectedWatchlist) {
        showToast('Please select a watchlist first', 'warning');
        return;
    }

    const ticker = document.getElementById('tickerSymbol').value.trim().toUpperCase();
    const thesis = document.getElementById('tickerThesis').value.trim();
    const targetPrice = document.getElementById('targetPrice').value;
    const notes = document.getElementById('tickerNotes').value.trim();

    if (!ticker) {
        showToast('Please enter a ticker symbol', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/watchlists/${state.selectedWatchlist.watchlist_id}/tickers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                ticker, 
                thesis, 
                target_price: targetPrice ? parseFloat(targetPrice) : null,
                notes 
            })
        });

        if (response.ok) {
            showToast(`${ticker} added to watchlist`, 'success');
            closeModal('addTickerModal');
            document.getElementById('tickerSymbol').value = '';
            document.getElementById('tickerThesis').value = '';
            document.getElementById('targetPrice').value = '';
            document.getElementById('tickerNotes').value = '';
            selectWatchlist(state.selectedWatchlist.watchlist_id);
        } else {
            const error = await response.json();
            showToast(error.error || 'Failed to add stock', 'error');
        }
    } catch (error) {
        console.error('Error adding ticker:', error);
        showToast('Failed to add stock', 'error');
    } finally {
        hideLoading();
    }
}

window.removeTickerFromWatchlist = async function(watchlistId, ticker) {
    if (!confirm(`Remove ${ticker} from watchlist?`)) return;

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/watchlists/${watchlistId}/tickers/${ticker}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast(`${ticker} removed from watchlist`, 'success');
            selectWatchlist(watchlistId);
        } else {
            showToast('Failed to remove stock', 'error');
        }
    } catch (error) {
        console.error('Error removing ticker:', error);
        showToast('Failed to remove stock', 'error');
    } finally {
        hideLoading();
    }
};

window.viewTickerDetails = function(ticker) {
    document.getElementById('quickSearchInput').value = ticker;
    showView('dashboard');
    handleQuickSearch();
};

// Analysis Functions
async function handleAnalyzePerformance() {
    const ticker = document.getElementById('perfTicker').value.trim().toUpperCase();
    const days = document.getElementById('perfDays').value;

    if (!ticker) {
        showToast('Please enter a ticker symbol', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/analysis/performance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                ticker, 
                days: parseInt(days),
                user_id: state.currentUser?.user_id
            })
        });

        if (response.ok) {
            const analysis = await response.json();
            displayAnalysisResult(analysis, 'Performance Analysis');
        } else {
            showToast('Failed to analyze performance', 'error');
        }
    } catch (error) {
        console.error('Analysis error:', error);
        showToast('Failed to analyze performance', 'error');
    } finally {
        hideLoading();
    }
}

async function handleCompareStocks() {
    const tickers = document.getElementById('compareTickers').value.trim().toUpperCase().split(',').map(t => t.trim());

    if (tickers.length < 2) {
        showToast('Please enter at least 2 tickers separated by commas', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/analysis/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                tickers,
                user_id: state.currentUser?.user_id
            })
        });

        if (response.ok) {
            const comparison = await response.json();
            displayAnalysisResult(comparison, 'Stock Comparison');
        } else {
            showToast('Failed to compare stocks', 'error');
        }
    } catch (error) {
        console.error('Comparison error:', error);
        showToast('Failed to compare stocks', 'error');
    } finally {
        hideLoading();
    }
}

async function handleSummarizeNews() {
    const ticker = document.getElementById('newsTicker').value.trim().toUpperCase();
    const days = document.getElementById('newsDays').value;

    if (!ticker) {
        showToast('Please enter a ticker symbol', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/analysis/news-summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                ticker, 
                days: parseInt(days),
                user_id: state.currentUser?.user_id
            })
        });

        if (response.ok) {
            const summary = await response.json();
            displayAnalysisResult(summary, 'News Summary');
        } else {
            showToast('Failed to summarize news', 'error');
        }
    } catch (error) {
        console.error('News summary error:', error);
        showToast('Failed to summarize news', 'error');
    } finally {
        hideLoading();
    }
}

function displayAnalysisResult(result, title) {
    const container = document.getElementById('analysisResults');
    
    container.innerHTML = `
        <div class="result-card">
            <h3><i class="fas fa-chart-line"></i> ${title}</h3>
            <div class="result-summary">
                <strong>Summary:</strong>
                <p>${result.summary || result.detailed_analysis || 'No summary available'}</p>
            </div>
            ${result.key_findings && result.key_findings.length > 0 ? `
                <div class="key-findings">
                    <h4>Key Findings:</h4>
                    <ul>
                        ${result.key_findings.map(f => `<li>${f}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            ${result.metrics ? `
                <div class="stock-details" style="margin-top: 1rem;">
                    ${Object.entries(result.metrics).slice(0, 6).map(([key, value]) => `
                        <div class="detail-item">
                            <span class="detail-label">${formatKey(key)}</span>
                            <span class="detail-value">${formatValue(key, value)}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;

    container.scrollIntoView({ behavior: 'smooth' });
}

// News Functions
async function handleNewsSearch() {
    const ticker = document.getElementById('newsSearchInput').value.trim().toUpperCase();

    if (!ticker) {
        showToast('Please enter a ticker symbol', 'error');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/api/stocks/${ticker}/news?limit=10`);
        
        if (response.ok) {
            const news = await response.json();
            displayNews(news);
        } else {
            showToast('Failed to fetch news', 'error');
        }
    } catch (error) {
        console.error('News error:', error);
        showToast('Failed to fetch news', 'error');
    } finally {
        hideLoading();
    }
}

function displayNews(articles) {
    const container = document.getElementById('newsContainer');
    
    if (articles.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No news articles found</p></div>';
        return;
    }

    container.innerHTML = articles.map(article => `
        <div class="news-card">
            <h4>${article.title || 'No title'}</h4>
            <div class="news-meta">
                <span><i class="fas fa-newspaper"></i> ${article.source || 'Unknown'}</span>
                <span><i class="fas fa-calendar"></i> ${article.published_at ? new Date(article.published_at).toLocaleDateString() : 'Unknown date'}</span>
            </div>
            <p class="news-summary">${article.summary || article.content || 'No summary available'}</p>
            ${article.url ? `
                <a href="${article.url}" target="_blank" class="btn btn-sm btn-primary">
                    Read More <i class="fas fa-external-link-alt"></i>
                </a>
            ` : ''}
        </div>
    `).join('');
}

// Dashboard Stats
async function updateDashboardStats() {
    if (!state.currentUser) {
        document.getElementById('watchlistCount').textContent = '0';
        document.getElementById('stockCount').textContent = '0';
        document.getElementById('noteCount').textContent = '0';
        document.getElementById('analysisCount').textContent = '0';
        return;
    }

    try {
        const watchlistsResponse = await fetch(`${API_URL}/api/users/${state.currentUser.user_id}/watchlists`);
        if (watchlistsResponse.ok) {
            const watchlists = await watchlistsResponse.json();
            document.getElementById('watchlistCount').textContent = watchlists.length;
            
            const totalStocks = watchlists.reduce((sum, w) => sum + (w.ticker_count || 0), 0);
            document.getElementById('stockCount').textContent = totalStocks;
        }

        const notesResponse = await fetch(`${API_URL}/api/users/${state.currentUser.user_id}/notes`);
        if (notesResponse.ok) {
            const notes = await notesResponse.json();
            document.getElementById('noteCount').textContent = notes.length;
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Utility Functions
function formatNumber(num) {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toFixed(0);
}

function formatKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatValue(key, value) {
    if (key.includes('price') || key.includes('change') && !key.includes('pct')) {
        return '$' + (typeof value === 'number' ? value.toFixed(2) : value);
    }
    if (key.includes('percent') || key.includes('pct')) {
        return (typeof value === 'number' ? value.toFixed(2) : value) + '%';
    }
    if (key.includes('volume')) {
        return formatNumber(value);
    }
    if (typeof value === 'number') {
        return value.toFixed(2);
    }
    return value;
}