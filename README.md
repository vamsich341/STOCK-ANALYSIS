# Stock Analysis Application

A comprehensive stock analysis platform built with Flask, Lakebase Postgres, and the Massive API. Track watchlists, analyze performance, and get AI-powered insights on your investment portfolio.

## Features

* **Watchlist Management**: Create and manage multiple stock watchlists with custom theses and notes
* **Real-Time Data**: Fetch current quotes, historical prices, and fundamentals via Massive API
* **AI-Powered Analysis**: Automated performance analysis, stock comparisons, and news summaries
* **Research Notes**: Document your investment research and track thesis validation
* **Price Alerts**: Get notified of significant price movements
* **Semantic Search**: Find companies and news using context-aware queries (with embeddings)

## Architecture

* **Backend**: Flask REST API (Python 3.9+)
* **Database**: Lakebase Postgres (Databricks)
* **External API**: Massive Stocks API
* **Port**: 8000

## Project Structure

```
STOCK-ANALYSIS/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── schema.sql            # Database schema
├── requirements.txt      # Python dependencies
├── services/
│   ├── __init__.py
│   ├── massive_api.py   # Massive API client
│   └── agent.py         # Analysis agent logic
└── README.md            # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

Connect to your Lakebase Postgres instance and run the schema:

```bash
psql "postgresql://ROOTUSER:npg_fsCrk8DWK3nj@ep-falling-thunder-d8fyunjf.database.us-east-2.cloud.databricks.com/databricks_postgres?sslmode=require" -f schema.sql
```

### 3. Configure Environment (Optional)

Create a `.env` file to override default settings:

```bash
DATABASE_URL=postgresql://ROOTUSER:npg_fsCrk8DWK3nj@ep-falling-thunder-d8fyunjf.database.us-east-2.cloud.databricks.com/databricks_postgres?sslmode=require
MASSIVE_API_KEY=0JTHKK3cpM_Zv4lOFt9xpxaGtC6DtQlv
PORT=8000
DEBUG=False
SECRET_KEY=your-secret-key-here
```

### 4. Run the Application

```bash
python app.py
```

The API will be available at `http://localhost:8000`

### 5. Verify Installation

Test the health endpoint:

```bash
curl http://localhost:8000/health
```

## API Endpoints

### Health Check

```
GET /health
```

Returns server health status and database connectivity.

### User Management

**Create User**
```
POST /api/users
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "preferences": {"theme": "dark"}
}
```

**Get User**
```
GET /api/users/{user_id}
```

### Watchlist Management

**Get All Watchlists**
```
GET /api/users/{user_id}/watchlists
```

**Create Watchlist**
```
POST /api/users/{user_id}/watchlists
Content-Type: application/json

{
  "name": "Tech Growth",
  "description": "High-growth technology stocks"
}
```

**Get Watchlist Details**
```
GET /api/watchlists/{watchlist_id}
```

**Add Ticker to Watchlist**
```
POST /api/watchlists/{watchlist_id}/tickers
Content-Type: application/json

{
  "ticker": "AAPL",
  "thesis": "Strong fundamentals and ecosystem",
  "target_price": 200.00,
  "notes": "Watch for Q4 earnings"
}
```

**Remove Ticker from Watchlist**
```
DELETE /api/watchlists/{watchlist_id}/tickers/{ticker}
```

### Stock Data

**Get Current Quote**
```
GET /api/stocks/{ticker}/quote

Example: GET /api/stocks/AAPL/quote
```

**Get Historical Data**
```
GET /api/stocks/{ticker}/historical?days=30

Query Parameters:
- days: Number of days of historical data (default: 30)
```

**Get Stock News**
```
GET /api/stocks/{ticker}/news?limit=10

Query Parameters:
- limit: Number of articles to return (default: 10)
```

### Analysis Endpoints

**Analyze Performance**
```
POST /api/analysis/performance
Content-Type: application/json

{
  "ticker": "TSLA",
  "user_id": 1,
  "days": 30
}
```

Returns comprehensive performance analysis including:
* Price movements and trends
* Volatility metrics
* Volume analysis
* Key findings

**Compare Stocks**
```
POST /api/analysis/compare
Content-Type: application/json

{
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "user_id": 1
}
```

Returns comparative analysis identifying:
* Best and worst performers
* Volatility leaders
* Volume comparisons

**Summarize News**
```
POST /api/analysis/news-summary
Content-Type: application/json

{
  "ticker": "NVDA",
  "user_id": 1,
  "days": 7
}
```

Returns news summary with:
* Article count and themes
* Key headlines
* Recent news activity

### Research Notes

**Get User Notes**
```
GET /api/users/{user_id}/notes?ticker=AAPL

Query Parameters:
- ticker: Filter by ticker (optional)
```

**Create Research Note**
```
POST /api/notes
Content-Type: application/json

{
  "user_id": 1,
  "ticker": "AMZN",
  "title": "AWS Growth Analysis",
  "content": "Examining AWS revenue trends...",
  "note_type": "bullish",
  "tags": ["cloud", "earnings"]
}
```

## Database Schema

### Core Tables

* **users**: Application users and preferences
* **watchlists**: User-created watchlists
* **watchlist_tickers**: Junction table linking watchlists to tickers
* **companies**: Company fundamental data and profiles
* **price_snapshots**: Historical and real-time price data
* **news_articles**: Company news and filings with sentiment
* **research_notes**: User-generated research and observations
* **analysis_reports**: AI-generated analysis and summaries
* **price_alerts**: User-defined price movement alerts
* **user_activity_log**: Activity tracking for notifications

### Key Features

* **Vector Search**: Companies and news tables support semantic search via embeddings (1536-dimensional)
* **Automatic Timestamps**: Created/updated timestamps managed by triggers
* **Foreign Key Constraints**: Referential integrity with CASCADE deletes
* **Comprehensive Indexes**: Optimized for common query patterns

## Agent Capabilities

The analysis agent (`services/agent.py`) provides:

1. **Performance Analysis**
   * Price change calculations
   * Volatility metrics
   * Volume trend analysis
   * Multi-period comparisons

2. **Stock Comparison**
   * Side-by-side metrics
   * Best/worst performer identification
   * Volatility and volume rankings

3. **News Summarization**
   * Recent article aggregation
   * Theme extraction
   * Key headline identification

4. **Notable Move Detection**
   * Configurable thresholds
   * Real-time alerts
   * Price movement tracking

5. **Thesis Validation**
   * Performance vs. thesis alignment
   * News sentiment correlation
   * Fundamental context

## Massive API Integration

The application integrates with Massive API for:

* **Real-time quotes**: Current price, volume, and market data
* **Historical data**: OHLCV data with configurable intervals
* **Company fundamentals**: Profile, financials, and metrics
* **News articles**: Real-time company news and filings
* **Market movers**: Gainers, losers, and most active stocks
* **Stock search**: Fuzzy search by name or ticker

### Caching Strategy

* 5-minute cache for quotes and historical data
* No caching for real-time trades and news
* In-memory cache with TTL

## Development

### Running Tests

```bash
pytest tests/
```

### Database Migrations

For schema changes, update `schema.sql` and run:

```bash
psql $DATABASE_URL -f schema.sql
```

### Adding New Features

1. Add database tables to `schema.sql`
2. Implement API endpoints in `app.py`
3. Add service logic in `services/`
4. Update this README with new endpoints

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Environment Variables

Ensure these are set in production:

* `DATABASE_URL`: Lakebase Postgres connection string
* `MASSIVE_API_KEY`: Your Massive API key
* `SECRET_KEY`: Strong random secret for Flask sessions
* `DEBUG`: Set to `False`
* `LOG_LEVEL`: Set to `INFO` or `WARNING`

### Security Considerations

* Use HTTPS in production
* Implement rate limiting
* Validate all user inputs
* Use prepared statements for SQL (already implemented with psycopg2)
* Rotate API keys regularly
* Implement authentication/authorization (TODO)

## Future Enhancements

* [ ] User authentication (JWT, OAuth)
* [ ] WebSocket support for real-time data streaming
* [ ] Embeddings for semantic company/news search
* [ ] Advanced charting and visualization
* [ ] Portfolio tracking and performance metrics
* [ ] Social features (share watchlists, follow analysts)
* [ ] Mobile app (React Native)
* [ ] Backtesting framework
* [ ] Integration with brokerage APIs

## Troubleshooting

### Database Connection Issues

```bash
# Test connection directly
psql "$DATABASE_URL" -c "SELECT 1;"
```

### API Key Issues

```bash
# Test Massive API key
curl -H "Authorization: Bearer $MASSIVE_API_KEY" https://api.massive.io/v1/stocks/AAPL/quote
```

### Port Already in Use

```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
* Check the [Massive API Documentation](https://docs.massive.io)
* Review [Lakebase Postgres Docs](https://docs.databricks.com/lakebase)
* Open an issue in this repository

## Contributors

Built with ❤️ for the Databricks community