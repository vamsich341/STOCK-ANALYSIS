"""
Production Stock Data API Client
Uses Alpha Vantage as primary source with Yahoo Finance fallback
NO DEMO DATA - Production ready with retries, rate limiting, and error handling
"""

import yfinance as yf
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class StockAPIClient:
    """Production-ready stock data client with Alpha Vantage + Yahoo Finance"""
    
    def __init__(self, alpha_vantage_key: str = None):
        """Initialize production API client
        
        Args:
            alpha_vantage_key: Alpha Vantage API key (get free at alphavantage.co)
        """
        self.alpha_vantage_key = alpha_vantage_key or 'demo'  # Use 'demo' key for testing
        self.alpha_vantage_base = 'https://www.alphavantage.co/query'
        
        # Cache configuration
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes for quotes, longer for historical
        self._historical_cache_ttl = 3600  # 1 hour for historical data
        
        # Rate limiting
        self._alpha_vantage_last_call = 0
        self._alpha_vantage_min_interval = 12.5  # 5 calls/min = 12 seconds between calls (with buffer)
        
        self._yfinance_last_call = 0
        self._yfinance_min_interval = 2.0  # 2 seconds between Yahoo calls
        
        # Request session with retry logic
        self.session = self._create_session()
        
        logger.info("Production Stock API Client initialized (Alpha Vantage + Yahoo Finance)")
        if self.alpha_vantage_key == 'demo':
            logger.warning("Using Alpha Vantage demo key - limited to 5 tickers. Set ALPHA_VANTAGE_API_KEY env var.")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Retry strategy: 3 retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _rate_limit_alpha_vantage(self):
        """Enforce Alpha Vantage rate limiting (5 calls/minute)"""
        current_time = time.time()
        time_since_last = current_time - self._alpha_vantage_last_call
        
        if time_since_last < self._alpha_vantage_min_interval:
            sleep_time = self._alpha_vantage_min_interval - time_since_last
            logger.debug(f"Alpha Vantage rate limit: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._alpha_vantage_last_call = time.time()
    
    def _rate_limit_yfinance(self):
        """Enforce Yahoo Finance rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self._yfinance_last_call
        
        if time_since_last < self._yfinance_min_interval:
            sleep_time = self._yfinance_min_interval - time_since_last + random.uniform(0.2, 0.5)
            time.sleep(sleep_time)
        
        self._yfinance_last_call = time.time()
    
    def _get_cache_key(self, method: str, ticker: str, params: str = "") -> str:
        """Generate cache key"""
        return f"{method}:{ticker}:{params}"
    
    def _get_cached(self, cache_key: str, ttl: int = None) -> Optional[Dict]:
        """Get cached data if still valid"""
        if cache_key not in self._cache:
            return None
        
        cached_time, data = self._cache[cache_key]
        cache_ttl = ttl or self._cache_ttl
        
        if (time.time() - cached_time) < cache_ttl:
            return data
        
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """Store data in cache"""
        self._cache[cache_key] = (time.time(), data)
    
    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get real-time quote for a stock
        
        Tries in order:
        1. Cache (if fresh)
        2. Alpha Vantage API
        3. Yahoo Finance (fallback)
        4. Stale cache (if available)
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Quote data dictionary or None if all sources fail
        """
        ticker = ticker.upper()
        cache_key = self._get_cache_key('quote', ticker)
        
        # 1. Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for {ticker}")
            return cached
        
        # 2. Try Alpha Vantage
        try:
            quote = self._get_quote_alpha_vantage(ticker)
            if quote:
                self._set_cache(cache_key, quote)
                logger.info(f"Alpha Vantage: {ticker} @ ${quote['price']}")
                return quote
        except Exception as e:
            logger.warning(f"Alpha Vantage failed for {ticker}: {e}")
        
        # 3. Fallback to Yahoo Finance
        try:
            quote = self._get_quote_yfinance(ticker)
            if quote:
                self._set_cache(cache_key, quote)
                logger.info(f"Yahoo Finance fallback: {ticker} @ ${quote['price']}")
                return quote
        except Exception as e:
            logger.error(f"Yahoo Finance failed for {ticker}: {e}")
        
        # 4. Last resort: return stale cache if exists
        if cache_key in self._cache:
            _, stale_data = self._cache[cache_key]
            logger.warning(f"Returning stale cache for {ticker}")
            stale_data['_stale'] = True
            return stale_data
        
        logger.error(f"All data sources failed for {ticker}")
        return None
    
    def _get_quote_alpha_vantage(self, ticker: str) -> Optional[Dict]:
        """Get quote from Alpha Vantage API"""
        self._rate_limit_alpha_vantage()
        
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker,
            'apikey': self.alpha_vantage_key
        }
        
        response = self.session.get(
            self.alpha_vantage_base,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API limit or error
        if 'Error Message' in data:
            raise Exception(f"Alpha Vantage error: {data['Error Message']}")
        
        if 'Note' in data:
            raise Exception("Alpha Vantage rate limit exceeded")
        
        if 'Global Quote' not in data or not data['Global Quote']:
            raise Exception("No data returned from Alpha Vantage")
        
        quote = data['Global Quote']
        
        # Parse Alpha Vantage response
        price = float(quote.get('05. price', 0))
        prev_close = float(quote.get('08. previous close', price))
        change = float(quote.get('09. change', 0))
        change_percent = float(quote.get('10. change percent', '0').rstrip('%'))
        
        return {
            'ticker': ticker,
            'company_name': ticker,  # Alpha Vantage doesn't provide company name in quotes
            'price': round(price, 2),
            'previous_close': round(prev_close, 2),
            'open': round(float(quote.get('02. open', price)), 2),
            'high': round(float(quote.get('03. high', price)), 2),
            'low': round(float(quote.get('04. low', price)), 2),
            'volume': int(quote.get('06. volume', 0)),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'currency': 'USD',
            'timestamp': datetime.now().isoformat(),
            'source': 'alpha_vantage'
        }
    
    def _get_quote_yfinance(self, ticker: str) -> Optional[Dict]:
        """Get quote from Yahoo Finance (fallback)"""
        self._rate_limit_yfinance()
        
        stock = yf.Ticker(ticker)
        stock.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        # Get recent history
        hist = stock.history(period="5d")
        
        if hist.empty:
            raise Exception(f"No data from Yahoo Finance for {ticker}")
        
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Close']
        
        price = float(latest['Close'])
        prev_close_val = float(prev_close)
        change = price - prev_close_val
        change_percent = (change / prev_close_val) * 100
        
        return {
            'ticker': ticker,
            'company_name': ticker,
            'price': round(price, 2),
            'previous_close': round(prev_close_val, 2),
            'open': round(float(latest['Open']), 2),
            'high': round(float(latest['High']), 2),
            'low': round(float(latest['Low']), 2),
            'volume': int(latest['Volume']),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'currency': 'USD',
            'timestamp': datetime.now().isoformat(),
            'source': 'yfinance'
        }
    
    def get_historical(self, ticker: str, period: str = '1mo') -> Optional[List[Dict]]:
        """Get historical price data
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('1d', '5d', '1mo', '3mo', '1y', '5y')
        
        Returns:
            List of historical price records
        """
        ticker = ticker.upper()
        cache_key = self._get_cache_key('historical', ticker, period)
        
        # Check cache (longer TTL for historical data)
        cached = self._get_cached(cache_key, ttl=self._historical_cache_ttl)
        if cached:
            logger.debug(f"Historical cache hit for {ticker} ({period})")
            return cached
        
        # Use Yahoo Finance for historical data (Alpha Vantage requires different API calls)
        try:
            self._rate_limit_yfinance()
            
            stock = yf.Ticker(ticker)
            stock.session.headers['User-Agent'] = 'Mozilla/5.0'
            
            hist = stock.history(period=period)
            
            if hist.empty:
                logger.warning(f"No historical data for {ticker}")
                return None
            
            # Convert to list of dicts
            historical_data = []
            for date, row in hist.iterrows():
                historical_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume'])
                })
            
            self._set_cache(cache_key, historical_data)
            logger.info(f"Fetched {len(historical_data)} historical records for {ticker}")
            return historical_data
        
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            
            # Return stale cache if available
            if cache_key in self._cache:
                _, stale_data = self._cache[cache_key]
                logger.warning(f"Returning stale historical cache for {ticker}")
                return stale_data
            
            return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get company information
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Company info dictionary
        """
        ticker = ticker.upper()
        cache_key = self._get_cache_key('info', ticker)
        
        cached = self._get_cached(cache_key, ttl=86400)  # 24 hour cache for company info
        if cached:
            return cached
        
        try:
            self._rate_limit_yfinance()
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            company_data = {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'description': info.get('longBusinessSummary'),
                'market_cap': info.get('marketCap'),
                'website': info.get('website'),
                'country': info.get('country'),
                'employees': info.get('fullTimeEmployees')
            }
            
            self._set_cache(cache_key, company_data)
            logger.info(f"Fetched company info for {ticker}")
            return company_data
        
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return {
                'ticker': ticker,
                'name': ticker
            }
    
    def health_check(self) -> Dict:
        """Check API health status"""
        status = {
            'alpha_vantage': 'unknown',
            'yfinance': 'unknown',
            'cache_size': len(self._cache)
        }
        
        # Test Alpha Vantage
        try:
            self._get_quote_alpha_vantage('AAPL')
            status['alpha_vantage'] = 'healthy'
        except Exception as e:
            status['alpha_vantage'] = f'unhealthy: {str(e)[:50]}'
        
        # Test Yahoo Finance
        try:
            self._get_quote_yfinance('AAPL')
            status['yfinance'] = 'healthy'
        except Exception as e:
            status['yfinance'] = f'unhealthy: {str(e)[:50]}'
        
        return status


# Backwards compatibility alias
class MassiveAPI:
    """Backwards compatible wrapper for StockAPIClient"""
    def __init__(self):
        self.client = StockAPIClient()
        logger.info("MassiveAPI compatibility layer initialized")
    
    def get_quote(self, ticker: str) -> Optional[Dict]:
        return self.client.get_quote(ticker)
    
    def get_historical(self, ticker: str, period: str = '1mo') -> Optional[List[Dict]]:
        return self.client.get_historical(ticker, period)
    
    def get_company_info(self, ticker: str) -> Optional[Dict]:
        return self.client.get_company_info(ticker)
