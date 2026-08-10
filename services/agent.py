"""
Stock Analysis Agent - AI-powered stock analysis and research capabilities
Provides intelligent analysis, summaries, and comparisons using real market data
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)

class StockAnalysisAgent:
    """AI agent for stock analysis and research"""
    
    def __init__(self, massive_client):
        """
        Initialize Stock Analysis Agent
        
        Args:
            massive_client: MassiveAPIClient instance for fetching market data
        """
        self.massive_client = massive_client
    
    def analyze_performance(self, ticker: str, days: int = 30) -> Dict:
        """
        Analyze stock performance over a time period
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to analyze
        
        Returns:
            Comprehensive performance analysis
        """
        logger.info(f"Analyzing performance for {ticker} over {days} days")
        
        # Fetch historical data
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        historical = self.massive_client.get_historical_data(ticker, start_date, end_date)
        current_quote = self.massive_client.get_quote(ticker)
        fundamentals = self.massive_client.get_company_info(ticker)
        
        if not historical or not current_quote:
            return {
                'error': 'Unable to fetch sufficient data for analysis',
                'ticker': ticker
            }
        
        # Calculate metrics
        prices = [point['close'] for point in historical if point.get('close')]
        volumes = [point['volume'] for point in historical if point.get('volume')]
        
        if not prices:
            return {
                'error': 'No price data available',
                'ticker': ticker
            }
        
        first_price = prices[0]
        last_price = prices[-1]
        current_price = current_quote.get('price', last_price)
        
        # Price statistics
        price_change = current_price - first_price
        price_change_pct = (price_change / first_price) * 100 if first_price else 0
        high_price = max(prices)
        low_price = min(prices)
        avg_price = statistics.mean(prices)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # Volume statistics
        avg_volume = statistics.mean(volumes) if volumes else 0
        recent_volume = volumes[-1] if volumes else 0
        volume_change_pct = ((recent_volume - avg_volume) / avg_volume * 100) if avg_volume else 0
        
        # Generate summary
        performance_direction = "gained" if price_change > 0 else "lost"
        volatility_level = "high" if volatility / avg_price > 0.05 else "moderate" if volatility / avg_price > 0.02 else "low"
        volume_status = "above" if volume_change_pct > 0 else "below"
        
        summary = f"{ticker} has {performance_direction} {abs(price_change_pct):.2f}% over the past {days} days, " \
                  f"trading from ${first_price:.2f} to ${current_price:.2f}. " \
                  f"The stock shows {volatility_level} volatility with a {days}-day range of ${low_price:.2f} to ${high_price:.2f}. " \
                  f"Recent volume is {abs(volume_change_pct):.1f}% {volume_status} the {days}-day average."
        
        # Detailed analysis
        detailed_analysis = f"""Performance Analysis for {ticker}:

Price Movement:
- Starting Price: ${first_price:.2f}
- Current Price: ${current_price:.2f}
- Change: ${price_change:.2f} ({price_change_pct:+.2f}%)
- Period High: ${high_price:.2f}
- Period Low: ${low_price:.2f}
- Average Price: ${avg_price:.2f}

Volatility:
- Standard Deviation: ${volatility:.2f}
- Volatility Level: {volatility_level.capitalize()}
- Price Range: ${high_price - low_price:.2f} ({((high_price - low_price) / avg_price * 100):.1f}% of avg)

Volume Analysis:
- Average Daily Volume: {avg_volume:,.0f}
- Recent Volume: {recent_volume:,.0f}
- Volume Trend: {volume_change_pct:+.1f}% vs average
"""
        
        # Add fundamental context if available
        if fundamentals:
            company_name = fundamentals.get('name', ticker)
            
            detailed_analysis += f"\nCompany Context:\n"
            detailed_analysis += f"- Company: {company_name}\n"
        
        # Key findings
        key_findings = [
            f"Price {performance_direction} {abs(price_change_pct):.2f}% over {days} days",
            f"{volatility_level.capitalize()} volatility observed",
            f"Volume is {abs(volume_change_pct):.1f}% {volume_status} average"
        ]
        
        # Add trend observation
        if len(prices) >= 5:
            recent_trend = prices[-5:]
            trend_direction = "upward" if recent_trend[-1] > recent_trend[0] else "downward"
            key_findings.append(f"Recent 5-day trend is {trend_direction}")
        
        # Metrics for storage
        metrics = {
            'current_price': current_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'high': high_price,
            'low': low_price,
            'average': avg_price,
            'volatility': volatility,
            'avg_volume': avg_volume,
            'recent_volume': recent_volume,
            'volume_change_pct': volume_change_pct,
            'period_days': days
        }
        
        return {
            'ticker': ticker,
            'summary': summary,
            'detailed_analysis': detailed_analysis,
            'key_findings': key_findings,
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def compare_stocks(self, tickers: List[str], days: int = 30) -> Dict:
        """
        Compare multiple stocks on key metrics
        
        Args:
            tickers: List of ticker symbols to compare
            days: Period for comparison
        
        Returns:
            Comparative analysis
        """
        logger.info(f"Comparing stocks: {', '.join(tickers)} over {days} days")
        
        comparisons = []
        
        for ticker in tickers:
            analysis = self.analyze_performance(ticker, days=days)
            if 'error' not in analysis:
                comparisons.append({
                    'ticker': ticker,
                    'metrics': analysis['metrics']
                })
        
        if not comparisons:
            return {
                'error': 'Unable to fetch data for any of the requested tickers'
            }
        
        # Find best and worst performers
        best_performer = max(comparisons, key=lambda x: x['metrics']['price_change_pct'])
        worst_performer = min(comparisons, key=lambda x: x['metrics']['price_change_pct'])
        most_volatile = max(comparisons, key=lambda x: x['metrics']['volatility'])
        highest_volume = max(comparisons, key=lambda x: x['metrics']['avg_volume'])
        
        # Generate summary
        summary = f"Comparing {len(comparisons)} stocks over {days} days: "
        summary += f"{best_performer['ticker']} leads with {best_performer['metrics']['price_change_pct']:+.2f}% gain, "
        summary += f"while {worst_performer['ticker']} shows {worst_performer['metrics']['price_change_pct']:+.2f}% change. "
        summary += f"{most_volatile['ticker']} exhibits the highest volatility."
        
        # Detailed comparison
        detailed_analysis = f"Comparative Analysis ({days}-day period):\n\n"
        
        for comp in sorted(comparisons, key=lambda x: x['metrics']['price_change_pct'], reverse=True):
            ticker = comp['ticker']
            m = comp['metrics']
            detailed_analysis += f"{ticker}:\n"
            detailed_analysis += f"  Price: ${m['current_price']:.2f} ({m['price_change_pct']:+.2f}%)\n"
            detailed_analysis += f"  Range: ${m['low']:.2f} - ${m['high']:.2f}\n"
            detailed_analysis += f"  Volatility: ${m['volatility']:.2f}\n"
            detailed_analysis += f"  Avg Volume: {m['avg_volume']:,.0f}\n\n"
        
        # Key findings
        key_findings = [
            f"Best performer: {best_performer['ticker']} ({best_performer['metrics']['price_change_pct']:+.2f}%)",
            f"Worst performer: {worst_performer['ticker']} ({worst_performer['metrics']['price_change_pct']:+.2f}%)",
            f"Most volatile: {most_volatile['ticker']} (stdev: ${most_volatile['metrics']['volatility']:.2f})",
            f"Highest volume: {highest_volume['ticker']} ({highest_volume['metrics']['avg_volume']:,.0f} avg)"
        ]
        
        return {
            'tickers': tickers,
            'summary': summary,
            'detailed_analysis': detailed_analysis,
            'key_findings': key_findings,
            'comparative_metrics': comparisons,
            'period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def summarize_news(self, ticker: str, days: int = 7) -> Dict:
        """
        Summarize recent news for a stock
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of news to analyze
        
        Returns:
            News summary and analysis
        """
        logger.info(f"Summarizing news for {ticker} from past {days} days")
        
        # Fetch news - CORRECTED METHOD NAME
        news_articles = self.massive_client.get_news(ticker, limit=20)
        
        if not news_articles:
            return {
                'ticker': ticker,
                'summary': f"No recent news found for {ticker}",
                'article_count': 0
            }
        
        # Filter by date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_articles = [
            article for article in news_articles
            if article.get('published_at') and 
            datetime.fromisoformat(article['published_at'].replace('Z', '+00:00')) > cutoff_date
        ]
        
        article_count = len(recent_articles)
        
        # Extract key themes (simple keyword extraction)
        all_titles = ' '.join([article.get('title', '') for article in recent_articles]).lower()
        
        keywords = {
            'earnings': all_titles.count('earnings') + all_titles.count('results'),
            'acquisition': all_titles.count('acquisition') + all_titles.count('merger'),
            'product': all_titles.count('product') + all_titles.count('launch'),
            'revenue': all_titles.count('revenue') + all_titles.count('sales'),
            'analyst': all_titles.count('analyst') + all_titles.count('rating'),
            'expansion': all_titles.count('expansion') + all_titles.count('growth'),
            'partnership': all_titles.count('partnership') + all_titles.count('deal')
        }
        
        top_themes = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:3]
        key_themes = [theme[0].capitalize() for theme in top_themes if theme[1] > 0]
        
        # Generate summary
        summary = f"{ticker} has {article_count} news articles in the past {days} days. "
        if key_themes:
            summary += f"Key themes include: {', '.join(key_themes)}. "
        else:
            summary += "Topics are diverse with no dominant theme. "
        
        # Detailed summary
        detailed_summary = f"News Summary for {ticker} (Past {days} Days):\n\n"
        detailed_summary += f"Total Articles: {article_count}\n\n"
        
        if key_themes:
            detailed_summary += f"Major Themes: {', '.join(key_themes)}\n\n"
        
        detailed_summary += "Recent Headlines:\n"
        for i, article in enumerate(recent_articles[:5], 1):
            title = article.get('title', 'No title')
            source = article.get('source', 'Unknown')
            published = article.get('published_at', '')
            detailed_summary += f"{i}. {title} - {source} ({published[:10]})\n"
        
        return {
            'ticker': ticker,
            'summary': summary,
            'detailed_summary': detailed_summary,
            'article_count': article_count,
            'key_themes': key_themes,
            'articles': recent_articles[:10],
            'period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def flag_notable_moves(self, ticker: str, threshold_pct: float = 5.0) -> Optional[Dict]:
        """
        Check if a stock has notable price movements
        
        Args:
            ticker: Stock ticker symbol
            threshold_pct: Percentage threshold for notable move
        
        Returns:
            Alert if notable movement detected, None otherwise
        """
        quote = self.massive_client.get_quote(ticker)
        
        if not quote:
            return None
        
        change_pct = quote.get('percent_change', 0)
        
        if abs(change_pct) >= threshold_pct:
            direction = "surged" if change_pct > 0 else "dropped"
            return {
                'ticker': ticker,
                'alert_type': 'notable_move',
                'message': f"{ticker} has {direction} {abs(change_pct):.2f}% today",
                'current_price': quote.get('price'),
                'change_percent': change_pct,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        return None
    
    def validate_thesis(self, ticker: str, thesis: str, days: int = 90) -> Dict:
        """
        Validate an investing thesis against recent performance and news
        
        Args:
            ticker: Stock ticker symbol
            thesis: User's investing thesis to validate
            days: Period to analyze
        
        Returns:
            Thesis validation report
        """
        logger.info(f"Validating thesis for {ticker}")
        
        # Gather data
        performance = self.analyze_performance(ticker, days=days)
        news_summary = self.summarize_news(ticker, days=min(days, 30))
        
        if 'error' in performance:
            return {
                'error': 'Unable to validate thesis due to data fetch issues',
                'ticker': ticker
            }
        
        # Simple validation logic
        price_change_pct = performance['metrics']['price_change_pct']
        
        # Check if performance aligns with bullish/bearish thesis
        is_bullish_thesis = any(word in thesis.lower() for word in ['buy', 'bull', 'growth', 'strong', 'positive'])
        is_bearish_thesis = any(word in thesis.lower() for word in ['sell', 'bear', 'decline', 'weak', 'negative'])
        
        thesis_supported = False
        confidence = "Low"
        
        if is_bullish_thesis and price_change_pct > 5:
            thesis_supported = True
            confidence = "High" if price_change_pct > 15 else "Moderate"
        elif is_bearish_thesis and price_change_pct < -5:
            thesis_supported = True
            confidence = "High" if price_change_pct < -15 else "Moderate"
        elif abs(price_change_pct) < 5:
            confidence = "Neutral"
        
        # Generate validation report
        validation_summary = f"Thesis Validation for {ticker}:\n\n"
        validation_summary += f"Your Thesis: {thesis}\n\n"
        validation_summary += f"Performance: {price_change_pct:+.2f}% over {days} days\n"
        validation_summary += f"Thesis Support: {'Supported' if thesis_supported else 'Not supported'}\n"
        validation_summary += f"Confidence: {confidence}\n\n"
        
        if news_summary.get('key_themes'):
            validation_summary += f"Recent News Themes: {', '.join(news_summary['key_themes'])}\n"
        
        return {
            'ticker': ticker,
            'thesis': thesis,
            'validation_summary': validation_summary,
            'thesis_supported': thesis_supported,
            'confidence': confidence,
            'performance_data': performance,
            'news_data': news_summary,
            'timestamp': datetime.utcnow().isoformat()
        }
