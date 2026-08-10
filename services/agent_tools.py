"""
Agent Tools - Explicit tools for LLM agent to interact with stock data
Provides both READ and WRITE operations with clear function signatures
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)

class AgentToolkit:
    """Toolkit of tools available to the LLM agent"""
    
    def __init__(self, db_connection, massive_api, embeddings_service=None):
        """Initialize toolkit with required services
        
        Args:
            db_connection: Database connection function
            massive_api: MassiveAPI instance for stock data
            embeddings_service: EmbeddingsService instance (optional)
        """
        self.get_db = db_connection
        self.api = massive_api
        self.embeddings_service = embeddings_service
    
    # ========== READ TOOLS ==========
    
    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote for a stock ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
        
        Returns:
            Dictionary with quote data including price, change, volume
        """
        logger.info(f"[TOOL] get_quote({ticker})")
        try:
            quote = self.api.get_quote(ticker)
            if quote:
                return {
                    'success': True,
                    'data': quote
                }
            return {
                'success': False,
                'error': f'No quote data available for {ticker}'
            }
        except Exception as e:
            logger.error(f"Error in get_quote: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_historical(self, ticker: str, period: str = '1mo') -> Dict[str, Any]:
        """Get historical price data for a stock
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('1d', '5d', '1mo', '3mo', '1y', '5y')
        
        Returns:
            Dictionary with historical price data
        """
        logger.info(f"[TOOL] get_historical({ticker}, {period})")
        try:
            history = self.api.get_historical(ticker, period=period)
            if history:
                return {
                    'success': True,
                    'data': history
                }
            return {
                'success': False,
                'error': f'No historical data available for {ticker}'
            }
        except Exception as e:
            logger.error(f"Error in get_historical: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_semantic(self, query: str, search_type: str = 'both', limit: int = 5) -> Dict[str, Any]:
        """Search for companies or news using semantic similarity
        
        Args:
            query: Natural language search query
            search_type: 'companies', 'news', or 'both'
            limit: Maximum number of results per type
        
        Returns:
            Dictionary with semantically similar companies and/or news
        """
        logger.info(f"[TOOL] search_semantic('{query}', {search_type}, limit={limit})")
        
        if not self.embeddings_service:
            return {
                'success': False,
                'error': 'Embeddings service not available'
            }
        
        try:
            # Generate embedding for query
            query_embedding = self.embeddings_service.generate_embedding(query)
            
            if not query_embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate embedding for query'
                }
            
            results = {}
            
            # Search companies
            if search_type in ['companies', 'both']:
                conn = self.get_db()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        ticker, name, description, sector, industry, market_cap,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM companies
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                companies = [dict(row) for row in cursor.fetchall()]
                results['companies'] = companies
                cursor.close()
            
            # Search news
            if search_type in ['news', 'both']:
                conn = self.get_db()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        article_id, ticker, title, summary, url, source,
                        published_at, sentiment_score,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM news_articles
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (query_embedding, query_embedding, limit))
                
                news = [dict(row) for row in cursor.fetchall()]
                results['news'] = news
                cursor.close()
            
            return {
                'success': True,
                'data': results
            }
        
        except Exception as e:
            logger.error(f"Error in search_semantic: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Get detailed company information
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Company details including sector, industry, description
        """
        logger.info(f"[TOOL] get_company_info({ticker})")
        try:
            conn = self.get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT company_id, ticker, name, description, sector, industry,
                       market_cap, website, founded, headquarters
                FROM companies
                WHERE ticker = %s
            """, (ticker.upper(),))
            
            company = cursor.fetchone()
            cursor.close()
            
            if company:
                return {
                    'success': True,
                    'data': dict(company)
                }
            return {
                'success': False,
                'error': f'Company not found: {ticker}'
            }
        
        except Exception as e:
            logger.error(f"Error in get_company_info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_news(self, ticker: str = None, limit: int = 10) -> Dict[str, Any]:
        """Get recent news articles
        
        Args:
            ticker: Stock ticker (optional, returns all news if None)
            limit: Maximum number of articles
        
        Returns:
            List of recent news articles
        """
        logger.info(f"[TOOL] get_news({ticker}, limit={limit})")
        try:
            conn = self.get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if ticker:
                cursor.execute("""
                    SELECT article_id, ticker, title, summary, url, source,
                           published_at, sentiment_score
                    FROM news_articles
                    WHERE ticker = %s
                    ORDER BY published_at DESC
                    LIMIT %s
                """, (ticker.upper(), limit))
            else:
                cursor.execute("""
                    SELECT article_id, ticker, title, summary, url, source,
                           published_at, sentiment_score
                    FROM news_articles
                    ORDER BY published_at DESC
                    LIMIT %s
                """, (limit,))
            
            articles = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            
            return {
                'success': True,
                'data': articles
            }
        
        except Exception as e:
            logger.error(f"Error in get_news: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== WRITE TOOLS ==========
    
    def add_to_watchlist(self, user_id: int, watchlist_id: int, ticker: str) -> Dict[str, Any]:
        """Add a stock to user's watchlist
        
        Args:
            user_id: User ID
            watchlist_id: Watchlist ID
            ticker: Stock ticker to add
        
        Returns:
            Success status and added ticker info
        """
        logger.info(f"[TOOL] add_to_watchlist(user={user_id}, watchlist={watchlist_id}, ticker={ticker})")
        try:
            conn = self.get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check if ticker already exists
            cursor.execute("""
                SELECT 1 FROM watchlist_tickers
                WHERE watchlist_id = %s AND ticker = %s
            """, (watchlist_id, ticker.upper()))
            
            if cursor.fetchone():
                cursor.close()
                return {
                    'success': False,
                    'error': f'{ticker} already in watchlist'
                }
            
            # Add ticker
            cursor.execute("""
                INSERT INTO watchlist_tickers (watchlist_id, ticker)
                VALUES (%s, %s)
                RETURNING watchlist_ticker_id, ticker, added_at
            """, (watchlist_id, ticker.upper()))
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'data': dict(result)
            }
        
        except Exception as e:
            logger.error(f"Error in add_to_watchlist: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_analysis(self, user_id: int, ticker: str, analysis: str, confidence: float = None) -> Dict[str, Any]:
        """Save AI-generated analysis for a stock
        
        Args:
            user_id: User ID
            ticker: Stock ticker
            analysis: Analysis text generated by the agent
            confidence: Optional confidence score (0-1)
        
        Returns:
            Success status and saved analysis ID
        """
        logger.info(f"[TOOL] save_analysis(user={user_id}, ticker={ticker}, confidence={confidence})")
        try:
            conn = self.get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                INSERT INTO user_notes (user_id, ticker, note_text)
                VALUES (%s, %s, %s)
                RETURNING note_id, user_id, ticker, note_text, created_at
            """, (user_id, ticker.upper(), analysis))
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'data': dict(result)
            }
        
        except Exception as e:
            logger.error(f"Error in save_analysis: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_alert(self, user_id: int, ticker: str, alert_type: str, 
                    threshold: float, message: str = None) -> Dict[str, Any]:
        """Create a price alert for a stock
        
        Args:
            user_id: User ID
            ticker: Stock ticker
            alert_type: 'price_above', 'price_below', 'percent_change'
            threshold: Price or percentage threshold
            message: Optional custom alert message
        
        Returns:
            Success status and alert info
        """
        logger.info(f"[TOOL] create_alert(user={user_id}, ticker={ticker}, type={alert_type}, threshold={threshold})")
        
        valid_types = ['price_above', 'price_below', 'percent_change']
        if alert_type not in valid_types:
            return {
                'success': False,
                'error': f'Invalid alert_type. Must be one of: {valid_types}'
            }
        
        try:
            conn = self.get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Store alert as a note with special formatting
            alert_text = f"[ALERT] {alert_type.replace('_', ' ').title()}: {ticker} @ ${threshold}"
            if message:
                alert_text += f" - {message}"
            
            cursor.execute("""
                INSERT INTO user_notes (user_id, ticker, note_text)
                VALUES (%s, %s, %s)
                RETURNING note_id, created_at
            """, (user_id, ticker.upper(), alert_text))
            
            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'data': {
                    'alert_id': result['note_id'],
                    'ticker': ticker.upper(),
                    'alert_type': alert_type,
                    'threshold': threshold,
                    'created_at': result['created_at']
                }
            }
        
        except Exception as e:
            logger.error(f"Error in create_alert: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== TOOL DEFINITIONS FOR LLM ==========
    
    @classmethod
    def get_tool_definitions(cls) -> List[Dict]:
        """Get tool definitions in OpenAI function calling format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_quote",
                    "description": "Get real-time quote for a stock ticker including price, change, volume",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_historical",
                    "description": "Get historical price data for a stock over various time periods",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol"
                            },
                            "period": {
                                "type": "string",
                                "description": "Time period: '1d', '5d', '1mo', '3mo', '1y', '5y'",
                                "enum": ["1d", "5d", "1mo", "3mo", "1y", "5y"]
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_semantic",
                    "description": "Search for companies or news using natural language semantic similarity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query (e.g., 'AI chip companies with strong earnings')"
                            },
                            "search_type": {
                                "type": "string",
                                "description": "What to search: 'companies', 'news', or 'both'",
                                "enum": ["companies", "news", "both"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results per type (default 5)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_company_info",
                    "description": "Get detailed information about a company including sector, industry, description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_news",
                    "description": "Get recent news articles for a stock or all stocks",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker (optional, returns all news if not provided)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of articles (default 10)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_to_watchlist",
                    "description": "Add a stock to the user's watchlist",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID"
                            },
                            "watchlist_id": {
                                "type": "integer",
                                "description": "Watchlist ID"
                            },
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker to add"
                            }
                        },
                        "required": ["user_id", "watchlist_id", "ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_analysis",
                    "description": "Save AI-generated stock analysis for the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID"
                            },
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker"
                            },
                            "analysis": {
                                "type": "string",
                                "description": "Analysis text"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Optional confidence score 0-1"
                            }
                        },
                        "required": ["user_id", "ticker", "analysis"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_alert",
                    "description": "Create a price alert for a stock",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID"
                            },
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker"
                            },
                            "alert_type": {
                                "type": "string",
                                "description": "Alert type",
                                "enum": ["price_above", "price_below", "percent_change"]
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Price or percentage threshold"
                            },
                            "message": {
                                "type": "string",
                                "description": "Optional custom message"
                            }
                        },
                        "required": ["user_id", "ticker", "alert_type", "threshold"]
                    }
                }
            }
        ]
