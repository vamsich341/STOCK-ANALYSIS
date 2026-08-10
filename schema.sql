-- Stock Analysis Application Database Schema
-- Designed for Lakebase Postgres (Databricks)

-- Users table: stores application users
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    preferences JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Watchlists table: stores user watchlists
CREATE TABLE IF NOT EXISTS watchlists (
    watchlist_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

CREATE INDEX idx_watchlists_user ON watchlists(user_id);

-- Companies table: stores company fundamental data
CREATE TABLE IF NOT EXISTS companies (
    company_id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    description TEXT,
    ceo VARCHAR(255),
    employees INTEGER,
    founded INTEGER,
    headquarters VARCHAR(255),
    website VARCHAR(255),
    fundamentals JSONB DEFAULT '{}',
    embedding vector(1536),  -- For semantic search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_industry ON companies(industry);

-- Watchlist tickers: junction table between watchlists and companies
CREATE TABLE IF NOT EXISTS watchlist_tickers (
    watchlist_ticker_id SERIAL PRIMARY KEY,
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    thesis TEXT,  -- User's investing thesis for this ticker
    target_price NUMERIC(10, 2),
    notes TEXT,
    UNIQUE(watchlist_id, ticker)
);

CREATE INDEX idx_watchlist_tickers_watchlist ON watchlist_tickers(watchlist_id);
CREATE INDEX idx_watchlist_tickers_ticker ON watchlist_tickers(ticker);
CREATE INDEX idx_watchlist_tickers_company ON watchlist_tickers(company_id);

-- Price snapshots: stores historical and real-time price data
CREATE TABLE IF NOT EXISTS price_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4),
    volume BIGINT,
    vwap NUMERIC(12, 4),  -- Volume-weighted average price
    trade_count INTEGER,
    source VARCHAR(50),  -- 'massive', 'yahoo', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, timestamp)
);

CREATE INDEX idx_price_snapshots_ticker ON price_snapshots(ticker);
CREATE INDEX idx_price_snapshots_timestamp ON price_snapshots(timestamp);
CREATE INDEX idx_price_snapshots_ticker_timestamp ON price_snapshots(ticker, timestamp DESC);
CREATE INDEX idx_price_snapshots_company ON price_snapshots(company_id);

-- News articles: stores company news and filings
CREATE TABLE IF NOT EXISTS news_articles (
    article_id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    url VARCHAR(500),
    source VARCHAR(100),
    author VARCHAR(255),
    published_at TIMESTAMP NOT NULL,
    sentiment_score NUMERIC(3, 2),  -- -1.0 to 1.0
    categories TEXT[],
    embedding vector(1536),  -- For semantic search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, url)
);

CREATE INDEX idx_news_ticker ON news_articles(ticker);
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_ticker_published ON news_articles(ticker, published_at DESC);
CREATE INDEX idx_news_company ON news_articles(company_id);

-- Research notes: user-generated notes and observations
CREATE TABLE IF NOT EXISTS research_notes (
    note_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    note_type VARCHAR(50),  -- 'bullish', 'bearish', 'neutral', 'question'
    tags TEXT[],
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_research_notes_user ON research_notes(user_id);
CREATE INDEX idx_research_notes_ticker ON research_notes(ticker);
CREATE INDEX idx_research_notes_company ON research_notes(company_id);
CREATE INDEX idx_research_notes_created ON research_notes(created_at DESC);

-- Analysis reports: AI-generated analysis and summaries
CREATE TABLE IF NOT EXISTS analysis_reports (
    report_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,  -- 'performance', 'news_summary', 'comparison', 'thesis_validation'
    query TEXT,  -- Original user query that generated this report
    summary TEXT NOT NULL,
    detailed_analysis TEXT,
    key_findings JSONB DEFAULT '[]',
    data_sources JSONB DEFAULT '[]',  -- References to price snapshots, news articles used
    metrics JSONB DEFAULT '{}',  -- Computed metrics (price changes, volatility, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP  -- Optional expiration for stale reports
);

CREATE INDEX idx_analysis_reports_user ON analysis_reports(user_id);
CREATE INDEX idx_analysis_reports_ticker ON analysis_reports(ticker);
CREATE INDEX idx_analysis_reports_company ON analysis_reports(company_id);
CREATE INDEX idx_analysis_reports_created ON analysis_reports(created_at DESC);
CREATE INDEX idx_analysis_reports_type ON analysis_reports(report_type);

-- User activity log: tracks user interactions for notifications
CREATE TABLE IF NOT EXISTS user_activity_log (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,  -- 'login', 'watchlist_update', 'report_generated'
    ticker VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_activity_user ON user_activity_log(user_id);
CREATE INDEX idx_user_activity_created ON user_activity_log(created_at DESC);

-- Price alerts: user-defined price movement notifications
CREATE TABLE IF NOT EXISTS price_alerts (
    alert_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,  -- 'price_above', 'price_below', 'percent_change', 'volume_spike'
    threshold NUMERIC(12, 4),
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_price_alerts_user ON price_alerts(user_id);
CREATE INDEX idx_price_alerts_ticker ON price_alerts(ticker);
CREATE INDEX idx_price_alerts_active ON price_alerts(is_active) WHERE is_active = TRUE;

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_watchlists_updated_at BEFORE UPDATE ON watchlists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_research_notes_updated_at BEFORE UPDATE ON research_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development
INSERT INTO users (username, email, preferences) VALUES 
    ('demo_user', 'demo@example.com', '{"theme": "dark", "notifications": true}')
ON CONFLICT (email) DO NOTHING;

COMMIT;