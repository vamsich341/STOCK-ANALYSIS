"""
Massive API Client - Integration with Massive Stocks API
Provides real-time and historical stock data, fundamentals, and news
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class MassiveAPIClient:
    """Client for interacting with Massive Stocks API"""
    
    def __init__(self, api_key: str, base_url: str = 'https://api.massive.io/v1'):
        """
        Initialize Massive API client
        
        Args:
            api_key: Massive API key
            base_url: Base URL for Massive API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key from endpoint and parameters"""
        param_str = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache:
            return False
        cached_time, _ = self._cache[cache_key]
        return (time.time() - cached_time) < self._cache_ttl
    
    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached data if valid"""
        if self._is_cache_valid(cache_key):
            _, data = self._cache[cache_key]
            return data
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """Store data in cache"""
        self._cache[cache_key] = (time.time(), data)
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, use_cache: bool = True) -> Optional[Dict]:
        """
        Make a request to Massive API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            use_cache: Whether to use cache
        
        Returns:
            API response data or None on error
        """
        if params is None:
            params = {}
        
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache
        if use_cache:
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache hit for {endpoint}")
                return cached_data
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Cache successful response
            if use_cache:
                self._set_cache(cache_key, data)
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Error parsing JSON response from {endpoint}: {e}")
            return None
    
    def get_current_quote(self, ticker: str) -> Optional[Dict]:
        """
        Get current quote for a ticker
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Current quote data including price, volume, etc.
        """
        endpoint = f"stocks/{ticker}/quote"
        data = self._make_request(endpoint)
        
        if data:
            return {
                'ticker': ticker,
                'price': data.get('price'),
                'open': data.get('open'),
                'high': data.get('high'),
                'low': data.get('low'),
                'volume': data.get('volume'),
                'change': data.get('change'),
                'change_percent': data.get('change_percent'),
                'previous_close': data.get('previous_close'),
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat())
            }
        return None
    
    def get_historical_data(self, ticker: str, days: int = 30, interval: str = '1day') -> Optional[List[Dict]]:
        """
        Get historical price data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of historical data
            interval: Data interval (1min, 5min, 15min, 1hour, 1day)
        
        Returns:
            List of historical price points
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        endpoint = f"stocks/{ticker}/historical"
        params = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'interval': interval
        }
        
        data = self._make_request(endpoint, params)
        
        if data and 'results' in data:
            return [
                {
                    'timestamp': point.get('timestamp'),
                    'open': point.get('open'),
                    'high': point.get('high'),
                    'low': point.get('low'),
                    'close': point.get('close'),
                    'volume': point.get('volume'),
                    'vwap': point.get('vwap')
                }
                for point in data['results']
            ]
        return None
    
    def get_company_fundamentals(self, ticker: str) -> Optional[Dict]:
        """
        Get company fundamental data
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Company fundamentals including profile, financials, etc.
        """
        endpoint = f"stocks/{ticker}/company"
        data = self._make_request(endpoint)
        
        if data:
            return {
                'ticker': ticker,
                'name': data.get('name'),
                'exchange': data.get('exchange'),
                'sector': data.get('sector'),
                'industry': data.get('industry'),
                'market_cap': data.get('market_cap'),
                'description': data.get('description'),
                'ceo': data.get('ceo'),
                'employees': data.get('employees'),
                'founded': data.get('founded'),
                'headquarters': data.get('headquarters'),
                'website': data.get('website'),
                'pe_ratio': data.get('pe_ratio'),
                'dividend_yield': data.get('dividend_yield'),
                'earnings_per_share': data.get('eps'),
                'beta': data.get('beta')
            }
        return None
    
    def get_stock_news(self, ticker: str, limit: int = 10) -> Optional[List[Dict]]:
        """
        Get recent news articles for a ticker
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of articles to return
        
        Returns:
            List of news articles
        """
        endpoint = f"stocks/{ticker}/news"
        params = {'limit': limit}
        
        data = self._make_request(endpoint, params, use_cache=False)  # Don't cache news
        
        if data and 'articles' in data:
            return [
                {
                    'title': article.get('title'),
                    'summary': article.get('summary'),
                    'content': article.get('content'),
                    'url': article.get('url'),
                    'source': article.get('source'),
                    'author': article.get('author'),
                    'published_at': article.get('published_at')
                }
                for article in data['articles']
            ]
        return None
    
    def get_market_movers(self, direction: str = 'gainers', limit: int = 10) -> Optional[List[Dict]]:
        """
        Get market movers (gainers, losers, most active)
        
        Args:
            direction: 'gainers', 'losers', or 'active'
            limit: Number of results to return
        
        Returns:
            List of top movers
        """
        endpoint = f"market/movers/{direction}"
        params = {'limit': limit}
        
        data = self._make_request(endpoint, params)
        
        if data and 'stocks' in data:
            return data['stocks']
        return None
    
    def search_stocks(self, query: str, limit: int = 10) -> Optional[List[Dict]]:
        """
        Search for stocks by name or ticker
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching stocks
        """
        endpoint = "stocks/search"
        params = {'q': query, 'limit': limit}
        
        data = self._make_request(endpoint, params)
        
        if data and 'results' in data:
            return [
                {
                    'ticker': result.get('ticker'),
                    'name': result.get('name'),
                    'exchange': result.get('exchange'),
                    'type': result.get('type')
                }
                for result in data['results']
            ]
        return None
    
    def get_realtime_trades(self, ticker: str, limit: int = 50) -> Optional[List[Dict]]:
        """
        Get real-time trade data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            limit: Number of recent trades to return
        
        Returns:
            List of recent trades
        """
        endpoint = f"stocks/{ticker}/trades"
        params = {'limit': limit}
        
        data = self._make_request(endpoint, params, use_cache=False)
        
        if data and 'trades' in data:
            return data['trades']
        return None
    
    def get_options_chain(self, ticker: str, expiration: Optional[str] = None) -> Optional[Dict]:
        """
        Get options chain data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            expiration: Optional expiration date (YYYY-MM-DD)
        
        Returns:
            Options chain data
        """
        endpoint = f"stocks/{ticker}/options"
        params = {}
        if expiration:
            params['expiration'] = expiration
        
        data = self._make_request(endpoint, params)
        
        if data:
            return {
                'ticker': ticker,
                'expirations': data.get('expirations', []),
                'calls': data.get('calls', []),
                'puts': data.get('puts', [])
            }
        return None