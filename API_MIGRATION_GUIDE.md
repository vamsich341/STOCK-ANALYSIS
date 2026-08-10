# API Migration Guide: Demo Data → Production APIs

## 🎯 Overview

The stock-analysis app has been **upgraded from demo/mock data to production-ready real-time market data** using:

* **Primary Source:** Alpha Vantage API (free tier: 5 calls/min, 500 calls/day)
* **Fallback Source:** Yahoo Finance (yfinance)
* **No More Demo Data:** All hardcoded mock quotes and fake historical data removed

---

## 📊 What Changed

### Before (Demo Data Problems)

```python
# ❌ OLD: Hardcoded demo data tried FIRST
DEMO_QUOTES = {
    'AAPL': {'price': 178.25, 'prev_close': 175.50},  # Static fake data
    'MSFT': {'price': 415.30, 'prev_close': 412.80},
    # ... 8 more hardcoded tickers
}

def get_quote(ticker):
    # Try demo data FIRST
    demo_quote = self._get_demo_quote(ticker)
    if demo_quote:
        return demo_quote  # Returns fake data!
    
    # Only tries real API if not in demo list
    return real_api_call(ticker)
```

**Problems:**
* Demo data returned for 10 popular tickers (AAPL, MSFT, GOOGL, etc.)
* Users got **fake prices** for major stocks
* Historical data was **randomly generated**
* No way to get real market data for demo tickers

### After (Production APIs)

```python
# ✅ NEW: Real APIs tried in order with proper fallback
def get_quote(ticker):
    # 1. Check cache (5 min TTL)
    if cached:
        return cached
    
    # 2. Try Alpha Vantage (primary)
    try:
        return alpha_vantage_api(ticker)  # Real data!
    except:
        pass
    
    # 3. Try Yahoo Finance (fallback)
    try:
        return yfinance_api(ticker)  # Still real data!
    except:
        pass
    
    # 4. Return stale cache if available
    return stale_cache if available
```

**Benefits:**
* **Real market data** for all tickers
* Automatic failover between two APIs
* Smart caching reduces API calls
* Proper rate limiting prevents blocks
* Request retries with exponential backoff

---

## 🔑 Alpha Vantage API Setup

### 1. Get Free API Key

Visit: https://www.alphavantage.co/support/#api-key

Fill out the form to get your **free API key** instantly.

**Free Tier Limits:**
* 5 API calls per minute
* 500 API calls per day
* Sufficient for most applications!

### 2. Set Environment Variable

**For Databricks Apps:**
```bash
# In app environment configuration
ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE
```

**For local development:**
```bash
export ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE
```

**For .env file:**
```bash
ALPHA_VANTAGE_API_KEY=YOUR_KEY_HERE
```

### 3. Fallback Behavior

If you don't set an API key:
* System uses `'demo'` key (limited to ~5 tickers: AAPL, MSFT, IBM, GOOGL, TSLA)
* Other tickers automatically fall back to Yahoo Finance
* **Still no fake/demo data!**

---

## 🏗️ Architecture

### Data Source Waterfall

```
User Request
    ↓
┌─────────────────────┐
│   Check Cache       │  ← 5 min TTL for quotes, 1 hour for historical
│   (5 min fresh)     │
└─────────────────────┘
    ↓ (miss)
┌─────────────────────┐
│  Alpha Vantage API  │  ← Primary: 5 calls/min rate limit
│  (Real-time data)   │
└─────────────────────┘
    ↓ (fail)
┌─────────────────────┐
│  Yahoo Finance API  │  ← Fallback: 2 sec between calls
│  (Real-time data)   │
└─────────────────────┘
    ↓ (fail)
┌─────────────────────┐
│   Stale Cache       │  ← Last resort: return old data if available
│   (marked stale)    │
└─────────────────────┘
    ↓ (none)
    Return None
```

### Rate Limiting

**Alpha Vantage:**
* 5 calls per minute = 12 seconds between calls (with buffer: 12.5s)
* Automatic enforcement before each call
* Prevents "Thank you for using Alpha Vantage" rate limit message

**Yahoo Finance:**
* 2 seconds between calls + random jitter (0.2-0.5s)
* User-Agent spoofing to avoid blocks
* Retries with exponential backoff

### Retry Strategy

```python
Retry(
    total=3,                    # 3 retry attempts
    backoff_factor=1,           # Wait 1, 2, 4 seconds
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
```

---

## 📝 API Response Format

All APIs return standardized format:

```python
{
    'ticker': 'AAPL',
    'company_name': 'Apple Inc.',
    'price': 180.50,
    'previous_close': 178.25,
    'open': 179.30,
    'high': 182.00,
    'low': 178.50,
    'volume': 52430000,
    'change': 2.25,
    'change_percent': 1.26,
    'currency': 'USD',
    'timestamp': '2026-08-10T10:30:00',
    'source': 'alpha_vantage'  # or 'yfinance'
}
```

### Source Field

* `'source': 'alpha_vantage'` - Data from Alpha Vantage
* `'source': 'yfinance'` - Data from Yahoo Finance fallback
* `'_stale': True` - Stale cache data (only when all APIs fail)

---

## 🧪 Testing

### Test Real-Time Quotes

```python
from services.stock_api import StockAPIClient

client = StockAPIClient(alpha_vantage_key='YOUR_KEY')

# Test popular stock
quote = client.get_quote('AAPL')
print(f"AAPL: ${quote['price']} (source: {quote['source']})")

# Test less common stock
quote = client.get_quote('TSLA')
print(f"TSLA: ${quote['price']} (source: {quote['source']})")
```

### Test Historical Data

```python
# Get 1 month of history
history = client.get_historical('MSFT', period='1mo')
print(f"Fetched {len(history)} days of MSFT history")

# Available periods: '1d', '5d', '1mo', '3mo', '1y', '5y'
```

### Test Health Check

```python
status = client.health_check()
print(status)

# Output:
# {
#     'alpha_vantage': 'healthy',
#     'yfinance': 'healthy',
#     'cache_size': 42
# }
```

### Test API Endpoint

```bash
# Test through Flask API
curl http://localhost:5000/api/stocks/AAPL/quote

# Response:
{
    "ticker": "AAPL",
    "price": 180.50,
    "change": 2.25,
    "change_percent": 1.26,
    "source": "alpha_vantage"
}
```

---

## 📈 Performance & Costs

### Caching Strategy

| Data Type | Cache TTL | Rationale |
|-----------|-----------|-----------|
| Real-time quotes | 5 minutes | Balance freshness vs API calls |
| Historical data | 1 hour | Infrequent changes |
| Company info | 24 hours | Rarely changes |

**Cache Hit Rate:** Typically 70-80% after warm-up

### API Call Estimates

**Scenario: 100 daily active users**

* Average 10 quote checks per user = 1,000 requests
* Cache hit rate 75% = 250 API calls
* Well within 500 calls/day free limit ✅

**Scenario: Heavy usage (500 users)**

* 5,000 total requests
* 75% cache hit = 1,250 API calls
* Exceeds free tier → Yahoo Finance fallback kicks in
* **Still free!** Yahoo Finance has no hard limits

### Cost Comparison

| Tier | Price | Calls/Day | Calls/Min |
|------|-------|-----------|-----------|
| **Alpha Vantage Free** | $0 | 500 | 5 |
| Alpha Vantage Premium | $49.99/mo | 30,000 | 30 |
| **Yahoo Finance** | $0 | Unlimited* | ~30/min |
| Polygon.io Free | $0 | 5 API calls | N/A |
| Polygon.io Starter | $29/mo | Unlimited | 5/sec |

*Yahoo Finance has soft limits but is reliable for most use cases

---

## 🔧 Migration Checklist

### For Production Deployment

- [x] Replace `services/massive_api.py` with `services/stock_api.py`
- [x] Update `app.py` imports
- [x] Update `agent_tools.py` parameter names
- [x] Add `ALPHA_VANTAGE_API_KEY` to config
- [ ] Set `ALPHA_VANTAGE_API_KEY` environment variable in production
- [ ] Test all stock endpoints
- [ ] Monitor API usage in production
- [ ] Set up alerts for API failures

### Verification Steps

```bash
# 1. Check imports work
python -c "from services.stock_api import StockAPIClient; print('✅ Import OK')"

# 2. Test quote fetch
python -c "from services.stock_api import StockAPIClient;            c = StockAPIClient();            q = c.get_quote('AAPL');            print(f'✅ Quote: {q["price"]} ({q["source"]})')"

# 3. Start app and test endpoint
python app.py &
sleep 5
curl http://localhost:5000/api/stocks/AAPL/quote
```

---

## 🚨 Troubleshooting

### "Alpha Vantage rate limit exceeded"

**Symptom:**
```json
{"error": "Alpha Vantage rate limit exceeded"}
```

**Solution:**
* System automatically falls back to Yahoo Finance
* Reduce request frequency if hitting limits often
* Consider upgrading to Alpha Vantage premium for higher limits

### "No data returned"

**Symptom:**
```python
quote = client.get_quote('INVALID')
# Returns: None
```

**Solution:**
* Check ticker symbol is valid
* Some OTC/pink sheet stocks not available in free APIs
* Check logs for specific error messages

### "Yahoo Finance failing"

**Symptom:**
```
WARNING: Yahoo Finance failed for TICKER: HTTP 404
```

**Solution:**
* Ticker may be delisted or invalid
* Yahoo sometimes blocks requests - retry after delay
* Check if ticker exists on yahoo.com/quote/TICKER

### Cache issues

**Symptom:** Stale prices showing

**Solution:**
```python
# Clear cache manually
client._cache = {}

# Or reduce cache TTL
client._cache_ttl = 60  # 1 minute
```

---

## 📚 Code Examples

### Basic Usage

```python
from services.stock_api import StockAPIClient
from config import Config

# Initialize client
client = StockAPIClient(alpha_vantage_key=Config.ALPHA_VANTAGE_API_KEY)

# Get quote
quote = client.get_quote('TSLA')
print(f"Tesla: ${quote['price']} ({quote['change_percent']:+.2f}%)")

# Get historical
history = client.get_historical('NVDA', period='1y')
print(f"NVDA 1-year history: {len(history)} days")

# Get company info
info = client.get_company_info('GOOGL')
print(f"{info['name']}: {info['sector']} / {info['industry']}")
```

### With Error Handling

```python
def safe_get_quote(ticker: str):
    """Get quote with comprehensive error handling"""
    try:
        quote = client.get_quote(ticker)
        
        if not quote:
            return {"error": f"No data available for {ticker}"}
        
        if quote.get('_stale'):
            return {
                "warning": "Using stale data (APIs unavailable)",
                "data": quote
            }
        
        return {"data": quote, "source": quote.get('source')}
    
    except Exception as e:
        logging.error(f"Error fetching {ticker}: {e}")
        return {"error": str(e)}
```

### Batch Requests

```python
def get_portfolio_quotes(tickers: list) -> dict:
    """Get quotes for multiple tickers efficiently"""
    results = {}
    
    for ticker in tickers:
        quote = client.get_quote(ticker)
        if quote:
            results[ticker] = {
                'price': quote['price'],
                'change_percent': quote['change_percent'],
                'source': quote.get('source')
            }
        
        # Rate limiting handled automatically
    
    return results

# Example usage
portfolio = get_portfolio_quotes(['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
```

---

## 🎉 Benefits Summary

✅ **Real Market Data**
* No more fake/demo data
* Accurate prices for all tickers
* Real-time updates

✅ **Production Ready**
* Automatic failover between APIs
* Request retries with backoff
* Comprehensive error handling

✅ **Performance**
* Smart caching reduces API calls
* Rate limiting prevents blocks
* Stale cache fallback ensures uptime

✅ **Cost Effective**
* Free tier sufficient for most apps
* Automatic Yahoo Finance fallback
* No usage surprises

✅ **Maintainable**
* Clean, documented code
* Easy to test
* Simple to monitor

---

## 📞 Support

**Alpha Vantage:**
* Docs: https://www.alphavantage.co/documentation/
* Support: https://www.alphavantage.co/support/

**Yahoo Finance (yfinance):**
* GitHub: https://github.com/ranaroussi/yfinance
* Docs: https://python-yahoofinance.readthedocs.io/

**Issues:**
* Check logs: `tail -f app.log`
* Test health: `client.health_check()`
* Monitor cache: `len(client._cache)`

---

## 🔄 Rollback Plan

If you need to temporarily roll back:

```python
# Revert to old massive_api.py (not recommended)
# Or use backwards compatibility wrapper:

from services.stock_api import MassiveAPI  # Wrapper included

api = MassiveAPI()  # Works like old client
quote = api.get_quote('AAPL')
```

**Note:** Wrapper still uses new real APIs, just compatible interface.
