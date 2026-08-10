#!/usr/bin/env python3
"""
Stock Analysis Application - Main Flask Application
Provides RESTful API for stock watchlist management, real-time data, and AI-powered analysis
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from config import Config
from services.massive_api import MassiveAPIClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from services.embeddings import EmbeddingsService
from services.agent_tools import AgentToolkit
from services.llm_agent import StockAnalysisAgent
# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.from_object(Config)
CORS(app)  # Enable CORS for all routes

# Initialize connection pool
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        sslmode='require'
    )
    logger.info("Database connection pool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database connection pool: {e}")
    connection_pool = None

# Initialize services
massive_client = MassiveAPIClient(Config.MASSIVE_API_KEY)
embeddings_service = EmbeddingsService(api_key=Config.OPENAI_API_KEY)
toolkit = AgentToolkit(get_db_connection, massive_client, embeddings_service)
analysis_agent = StockAnalysisAgent(toolkit, api_key=Config.OPENAI_API_KEY)

# Database helper functions
def get_db_connection():
    """Get a connection from the pool"""
    if connection_pool:
        return connection_pool.getconn()
    return None

def release_db_connection(conn):
    """Return connection to the pool"""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def get_db():
    """Get database connection for request context"""
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Release database connection after request"""
    db = g.pop('db', None)
    if db is not None:
        release_db_connection(db)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Root endpoint - Serve the frontend
@app.route('/', methods=['GET'])
def index():
    """Serve the main web interface"""
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({'error': 'Frontend not available', 'details': str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'disconnected',
        'massive_api': 'unknown'
    }
    
    # Check database connection
    try:
        conn = get_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            health_status['database'] = 'connected'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['status'] = 'degraded'
    
    return jsonify(health_status), 200

# ========== USER ENDPOINTS ==========

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    preferences = data.get('preferences', {})
    
    if not username or not email:
        return jsonify({'error': 'Username and email are required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "INSERT INTO users (username, email, preferences) VALUES (%s, %s, %s) RETURNING user_id, username, email, created_at",
            (username, email, psycopg2.extras.Json(preferences))
        )
        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        return jsonify(dict(user)), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'User already exists'}), 409
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get users - supports ?email= query parameter"""
    email = request.args.get('email')
    
    if not email:
        return jsonify({'error': 'Email parameter is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT user_id, username, email, created_at, last_login, preferences FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            return jsonify(dict(user)), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    
    except Exception as e:
        logger.error(f"Error fetching user by email: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT user_id, username, email, preferences, created_at, last_login FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(dict(user)), 200
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return jsonify({'error': str(e)}), 500

# ========== WATCHLIST ENDPOINTS ==========

@app.route('/api/users/<int:user_id>/watchlists', methods=['GET'])
def get_watchlists(user_id):
    """Get all watchlists for a user"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """SELECT w.*, COUNT(wt.watchlist_ticker_id) as ticker_count 
               FROM watchlists w 
               LEFT JOIN watchlist_tickers wt ON w.watchlist_id = wt.watchlist_id 
               WHERE w.user_id = %s 
               GROUP BY w.watchlist_id 
               ORDER BY w.created_at DESC""",
            (user_id,)
        )
        watchlists = cursor.fetchall()
        cursor.close()
        return jsonify([dict(w) for w in watchlists]), 200
    except Exception as e:
        logger.error(f"Error fetching watchlists: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/watchlists', methods=['POST'])
def create_watchlist(user_id):
    """Create a new watchlist"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    
    if not name:
        return jsonify({'error': 'Watchlist name is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "INSERT INTO watchlists (user_id, name, description) VALUES (%s, %s, %s) RETURNING *",
            (user_id, name, description)
        )
        watchlist = cursor.fetchone()
        conn.commit()
        cursor.close()
        return jsonify(dict(watchlist)), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Watchlist with this name already exists'}), 409
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlists/<int:watchlist_id>', methods=['GET'])
def get_watchlist(watchlist_id):
    """Get watchlist with tickers"""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get watchlist details
        cursor.execute("SELECT * FROM watchlists WHERE watchlist_id = %s", (watchlist_id,))
        watchlist = cursor.fetchone()
        
        if not watchlist:
            return jsonify({'error': 'Watchlist not found'}), 404
        
        # Get tickers in watchlist
        cursor.execute(
            """SELECT wt.*, c.name as company_name, c.sector, c.market_cap 
               FROM watchlist_tickers wt 
               LEFT JOIN companies c ON wt.company_id = c.company_id 
               WHERE wt.watchlist_id = %s 
               ORDER BY wt.added_at DESC""",
            (watchlist_id,)
        )
        tickers = cursor.fetchall()
        cursor.close()
        
        result = dict(watchlist)
        result['tickers'] = [dict(t) for t in tickers]
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlists/<int:watchlist_id>/tickers', methods=['POST'])
def add_ticker_to_watchlist(watchlist_id):
    """Add a ticker to watchlist"""
    data = request.get_json()
    ticker = data.get('ticker', '').upper()
    thesis = data.get('thesis', '')
    target_price = data.get('target_price')
    notes = data.get('notes', '')
    
    if not ticker:
        return jsonify({'error': 'Ticker symbol is required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if company exists, if not fetch from Massive API
        cursor.execute("SELECT company_id FROM companies WHERE ticker = %s", (ticker,))
        company = cursor.fetchone()
        
        company_id = None
        if not company:
            # Fetch company data from Massive API
            company_data = massive_client.get_company_info(ticker)
            if company_data:
                cursor.execute(
                    """INSERT INTO companies (ticker, name, exchange, sector, industry, market_cap, description, fundamentals) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                       RETURNING company_id""",
                    (
                        ticker,
                        company_data.get('name', ticker),
                        company_data.get('exchange'),
                        company_data.get('sector'),
                        company_data.get('industry'),
                        company_data.get('market_cap'),
                        company_data.get('description'),
                        psycopg2.extras.Json(company_data)
                    )
                )
                company_id = cursor.fetchone()['company_id']
        else:
            company_id = company['company_id']
        
        # Add to watchlist
        cursor.execute(
            """INSERT INTO watchlist_tickers (watchlist_id, ticker, company_id, thesis, target_price, notes) 
               VALUES (%s, %s, %s, %s, %s, %s) 
               RETURNING *""",
            (watchlist_id, ticker, company_id, thesis, target_price, notes)
        )
        watchlist_ticker = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        return jsonify(dict(watchlist_ticker)), 201
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Ticker already in watchlist'}), 409
    except Exception as e:
        logger.error(f"Error adding ticker to watchlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlists/<int:watchlist_id>/tickers/<ticker>', methods=['DELETE'])
def remove_ticker_from_watchlist(watchlist_id, ticker):
    """Remove a ticker from watchlist"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM watchlist_tickers WHERE watchlist_id = %s AND ticker = %s",
            (watchlist_id, ticker.upper())
        )
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        
        if deleted == 0:
            return jsonify({'error': 'Ticker not found in watchlist'}), 404
        
        return jsonify({'message': 'Ticker removed successfully'}), 200
    except Exception as e:
        logger.error(f"Error removing ticker: {e}")
        return jsonify({'error': str(e)}), 500

# ========== STOCK DATA ENDPOINTS ==========

@app.route('/api/stocks/<ticker>/quote', methods=['GET'])
def get_stock_quote(ticker):
    """Get current stock quote"""
    try:
        quote = massive_client.get_quote(ticker.upper())
        if not quote:
            return jsonify({'error': 'Stock not found'}), 404
        return jsonify(quote), 200
    except Exception as e:
        logger.error(f"Error fetching stock quote: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/<ticker>/historical', methods=['GET'])
def get_historical_data(ticker):
    """Get historical price data"""
    days = request.args.get('days', 30, type=int)
    
    try:
        # Calculate start and end dates
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        historical = massive_client.get_historical_data(ticker.upper(), start_date=start_date, end_date=end_date)
        if not historical:
            return jsonify({'error': 'No historical data available'}), 404
        return jsonify(historical), 200
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stocks/<ticker>/news', methods=['GET'])
def get_stock_news(ticker):
    """Get recent news for a stock"""
    limit = request.args.get('limit', 10, type=int)
    
    try:
        # First check database
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """SELECT * FROM news_articles 
               WHERE ticker = %s 
               ORDER BY published_at DESC 
               LIMIT %s""",
            (ticker.upper(), limit)
        )
        news = cursor.fetchall()
        cursor.close()
        
        # If not enough in DB, fetch from API
        if len(news) < limit:
            api_news = massive_client.get_news(ticker=ticker.upper(), limit=limit)
            
            # Store new articles in database
            if api_news:
                for article in api_news:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """INSERT INTO news_articles (ticker, title, summary, content, url, source, published_at) 
                               VALUES (%s, %s, %s, %s, %s, %s, %s) 
                               ON CONFLICT (ticker, url) DO NOTHING""",
                            (
                                ticker.upper(),
                                article.get('title'),
                                article.get('summary'),
                                article.get('content'),
                                article.get('url'),
                                article.get('source'),
                                article.get('published_at')
                            )
                        )
                        cursor.close()
                    except Exception as e:
                        logger.error(f"Error storing news article: {e}")
                
                conn.commit()
                news = api_news
        
        return jsonify([dict(n) for n in news]), 200
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return jsonify({'error': str(e)}), 500

# ========== ANALYSIS ENDPOINTS ==========



@app.route('/api/semantic-search', methods=['POST'])
def semantic_search():
    """
    Semantic search across companies and news using embeddings
    
    Request body:
    {
        "query": "AI chip companies with strong earnings",
        "search_type": "companies" | "news" | "both",
        "limit": 10
    }
    """
    try:
        data = request.json
        query = data.get('query', '')
        search_type = data.get('search_type', 'both')
        limit = min(int(data.get('limit', 10)), 50)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Initialize embeddings service
        embeddings_service = EmbeddingsService()
        
        # Generate embedding for the query
        query_embedding = embeddings_service.generate_embedding(query)
        
        if not query_embedding:
            return jsonify({'error': 'Failed to generate embedding for query'}), 500
        
        results = {}
        
        # Search companies
        if search_type in ['companies', 'both']:
            cursor = get_db_cursor()
            try:
                cursor.execute("""
                    SELECT 
                        ticker,
                        name,
                        description,
                        sector,
                        industry,
                        market_cap,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM companies
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                companies = []
                for row in cursor.fetchall():
                    companies.append({
                        'ticker': row[0],
                        'name': row[1],
                        'description': row[2][:200] if row[2] else '',
                        'sector': row[3],
                        'industry': row[4],
                        'market_cap': row[5],
                        'similarity': float(row[6])
                    })
                
                results['companies'] = companies
                cursor.close()
                
            except Exception as e:
                logger.error(f"Error searching companies: {e}")
                results['companies'] = []
        
        # Search news
        if search_type in ['news', 'both']:
            cursor = get_db_cursor()
            try:
                cursor.execute("""
                    SELECT 
                        article_id,
                        ticker,
                        title,
                        summary,
                        url,
                        source,
                        published_at,
                        sentiment_score,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM news_articles
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                articles = []
                for row in cursor.fetchall():
                    articles.append({
                        'article_id': row[0],
                        'ticker': row[1],
                        'title': row[2],
                        'summary': row[3],
                        'url': row[4],
                        'source': row[5],
                        'published_at': row[6].isoformat() if row[6] else None,
                        'sentiment_score': float(row[7]) if row[7] else None,
                        'similarity': float(row[8])
                    })
                
                results['news'] = articles
                cursor.close()
                
            except Exception as e:
                logger.error(f"Error searching news: {e}")
                results['news'] = []
        
        return jsonify({
            'query': query,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/performance', methods=['POST'])
def analyze_performance():
    """Analyze stock performance"""
    data = request.get_json()
    ticker = data.get('ticker', '').upper()
    user_id = data.get('user_id')
    days = data.get('days', 30)
    
    if not ticker:
        return jsonify({'error': 'Ticker is required'}), 400
    
    try:
        analysis = analysis_agent.analyze_performance(ticker, days=days)
        
        # Save report to database
        if user_id and analysis:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """INSERT INTO analysis_reports 
                   (user_id, ticker, report_type, summary, detailed_analysis, key_findings, metrics) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s) 
                   RETURNING report_id""",
                (
                    user_id,
                    ticker,
                    'performance',
                    analysis.get('summary'),
                    analysis.get('detailed_analysis'),
                    psycopg2.extras.Json(analysis.get('key_findings', [])),
                    psycopg2.extras.Json(analysis.get('metrics', {}))
                )
            )
            report_id = cursor.fetchone()['report_id']
            conn.commit()
            cursor.close()
            analysis['report_id'] = report_id
        
        return jsonify(analysis), 200
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/compare', methods=['POST'])
def compare_stocks():
    """Compare multiple stocks"""
    data = request.get_json()
    tickers = [t.upper() for t in data.get('tickers', [])]
    user_id = data.get('user_id')
    
    if not tickers or len(tickers) < 2:
        return jsonify({'error': 'At least 2 tickers are required'}), 400
    
    try:
        comparison = analysis_agent.compare_stocks(tickers)
        
        # Save report for each ticker
        if user_id and comparison:
            conn = get_db()
            for ticker in tickers:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO analysis_reports 
                       (user_id, ticker, report_type, summary, detailed_analysis, key_findings, metrics) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        user_id,
                        ticker,
                        'comparison',
                        comparison.get('summary'),
                        comparison.get('detailed_analysis'),
                        psycopg2.extras.Json(comparison.get('key_findings', [])),
                        psycopg2.extras.Json(comparison.get('comparative_metrics', {}))
                    )
                )
                cursor.close()
            conn.commit()
        
        return jsonify(comparison), 200
    except Exception as e:
        logger.error(f"Error comparing stocks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/news-summary', methods=['POST'])
def summarize_news():
    """Generate news summary for a ticker"""
    data = request.get_json()
    ticker = data.get('ticker', '').upper()
    user_id = data.get('user_id')
    days = data.get('days', 7)
    
    if not ticker:
        return jsonify({'error': 'Ticker is required'}), 400
    
    try:
        summary = analysis_agent.summarize_news(ticker, days=days)
        
        # Save report
        if user_id and summary:
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """INSERT INTO analysis_reports 
                   (user_id, ticker, report_type, summary, detailed_analysis, key_findings) 
                   VALUES (%s, %s, %s, %s, %s, %s) 
                   RETURNING report_id""",
                (
                    user_id,
                    ticker,
                    'news_summary',
                    summary.get('summary'),
                    summary.get('detailed_summary'),
                    psycopg2.extras.Json(summary.get('key_themes', []))
                )
            )
            report_id = cursor.fetchone()['report_id']
            conn.commit()
            cursor.close()
            summary['report_id'] = report_id
        
        return jsonify(summary), 200
    except Exception as e:
        logger.error(f"Error summarizing news: {e}")
        return jsonify({'error': str(e)}), 500

# ========== RESEARCH NOTES ENDPOINTS ==========

@app.route('/api/users/<int:user_id>/notes', methods=['GET'])
def get_user_notes(user_id):
    """Get all research notes for a user"""
    ticker = request.args.get('ticker', '').upper()
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if ticker:
            cursor.execute(
                """SELECT * FROM research_notes 
                   WHERE user_id = %s AND ticker = %s 
                   ORDER BY created_at DESC""",
                (user_id, ticker)
            )
        else:
            cursor.execute(
                "SELECT * FROM research_notes WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
        
        notes = cursor.fetchall()
        cursor.close()
        return jsonify([dict(n) for n in notes]), 200
    except Exception as e:
        logger.error(f"Error fetching notes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notes', methods=['POST'])
def create_note():
    """Create a research note"""
    data = request.get_json()
    user_id = data.get('user_id')
    ticker = data.get('ticker', '').upper()
    title = data.get('title')
    content = data.get('content')
    note_type = data.get('note_type', 'neutral')
    tags = data.get('tags', [])
    
    if not all([user_id, ticker, title, content]):
        return jsonify({'error': 'user_id, ticker, title, and content are required'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """INSERT INTO research_notes (user_id, ticker, title, content, note_type, tags) 
               VALUES (%s, %s, %s, %s, %s, %s) 
               RETURNING *""",
            (user_id, ticker, title, content, note_type, tags)
        )
        note = cursor.fetchone()
        conn.commit()
        cursor.close()
        return jsonify(dict(note)), 201
    except Exception as e:
        logger.error(f"Error creating note: {e}")
        return jsonify({'error': str(e)}), 500


# ========== LLM AGENT ENDPOINT ==========

@app.route('/api/agent/query', methods=['POST'])
def agent_query():
    """
    LLM Agent endpoint - Intelligent stock analysis with tool calling
    
    Request body:
    {
        "query": "What's AAPL's price and how has it performed?",
        "user_id": 1,  # optional, for write operations
        "conversation_history": []  # optional, for context
    }
    """
    try:
        data = request.json
        query = data.get('query', '')
        user_id = data.get('user_id')
        conversation_history = data.get('conversation_history', [])
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Initialize agent components
        stock_api_instance = StockAPIClient(alpha_vantage_key=Config.ALPHA_VANTAGE_API_KEY)
        
        # Try to get embeddings service (may not be available)
        try:
            embeddings_service_instance = EmbeddingsService()
        except:
            embeddings_service_instance = None
        
        # Create toolkit
        toolkit = AgentToolkit(
            db_connection=get_db,
            stock_api=stock_api_instance,
            embeddings_service=embeddings_service_instance
        )
        
        # Create agent
        agent = StockAnalysisAgent(toolkit)
        
        # Run agent
        result = agent.run(
            user_query=query,
            user_id=user_id,
            conversation_history=conversation_history
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in agent query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/agent/capabilities', methods=['GET'])
def agent_capabilities():
    """Get agent capabilities and example queries"""
    try:
        # Create a dummy agent to get capabilities
        toolkit = AgentToolkit(
            db_connection=get_db,
            massive_api=MassiveAPI(),
            embeddings_service=None
        )
        agent = StockAnalysisAgent(toolkit)
        
        capabilities = agent.explain_capabilities()
        return jsonify(capabilities)
    
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Initialize database schema on first run
    logger.info("Starting Stock Analysis Application...")
    logger.info(f"Listening on port {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)