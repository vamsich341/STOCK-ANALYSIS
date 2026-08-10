#!/usr/bin/env python3
"""
Generate embeddings for all companies and news articles in the database
Run this script to populate the embedding columns for semantic search
"""

import sys
import os
import psycopg2
from services.embeddings import EmbeddingsService
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://ROOTUSER:npg_fsCrk8DWK3nj@ep-falling-thunder-d8fyunjf.database.us-east-2.cloud.databricks.com/databricks_postgres?sslmode=require'
)

def generate_company_embeddings(embedding_service, conn):
    """Generate embeddings for all companies"""
    logger.info("=" * 60)
    logger.info("GENERATING COMPANY EMBEDDINGS")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # Get all companies without embeddings
    cursor.execute("""
        SELECT company_id, ticker, name, description, sector, industry
        FROM companies
        WHERE embedding IS NULL
        ORDER BY company_id
    """)
    companies = cursor.fetchall()
    
    logger.info(f"Found {len(companies)} companies without embeddings")
    
    if not companies:
        logger.info("All companies already have embeddings!")
        return
    
    success_count = 0
    fail_count = 0
    
    for company in companies:
        company_id, ticker, name, description, sector, industry = company
        
        try:
            logger.info(f"Processing {ticker} - {name}...")
            
            # Generate embedding
            embedding = embedding_service.embed_company(
                ticker=ticker,
                name=name,
                description=description or "",
                sector=sector,
                industry=industry
            )
            
            if embedding:
                # Update database
                cursor.execute(
                    "UPDATE companies SET embedding = %s WHERE company_id = %s",
                    (embedding, company_id)
                )
                conn.commit()
                success_count += 1
                logger.info(f"  ✓ Generated embedding for {ticker}")
            else:
                fail_count += 1
                logger.warning(f"  ✗ Failed to generate embedding for {ticker}")
        
        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ Error processing {ticker}: {e}")
            conn.rollback()
    
    cursor.close()
    
    logger.info("-" * 60)
    logger.info(f"Company embeddings complete: {success_count} success, {fail_count} failed")
    logger.info("-" * 60)

def generate_news_embeddings(embedding_service, conn):
    """Generate embeddings for all news articles"""
    logger.info("=" * 60)
    logger.info("GENERATING NEWS EMBEDDINGS")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # Get all news articles without embeddings
    cursor.execute("""
        SELECT article_id, ticker, title, summary, content
        FROM news_articles
        WHERE embedding IS NULL
        ORDER BY article_id
        LIMIT 100
    """)
    articles = cursor.fetchall()
    
    logger.info(f"Found {len(articles)} news articles without embeddings (showing first 100)")
    
    if not articles:
        logger.info("All news articles already have embeddings!")
        return
    
    success_count = 0
    fail_count = 0
    
    for article in articles:
        article_id, ticker, title, summary, content = article
        
        try:
            logger.info(f"Processing news {article_id} - {title[:50]}...")
            
            # Generate embedding
            embedding = embedding_service.embed_news(
                title=title,
                summary=summary,
                content=content
            )
            
            if embedding:
                # Update database
                cursor.execute(
                    "UPDATE news_articles SET embedding = %s WHERE article_id = %s",
                    (embedding, article_id)
                )
                conn.commit()
                success_count += 1
                logger.info(f"  ✓ Generated embedding for article {article_id}")
            else:
                fail_count += 1
                logger.warning(f"  ✗ Failed to generate embedding for article {article_id}")
        
        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ Error processing article {article_id}: {e}")
            conn.rollback()
    
    cursor.close()
    
    logger.info("-" * 60)
    logger.info(f"News embeddings complete: {success_count} success, {fail_count} failed")
    logger.info("-" * 60)

def main():
    """Main function"""
    logger.info("\n" + "=" * 60)
    logger.info("STOCK ANALYSIS - EMBEDDING GENERATION")
    logger.info("=" * 60)
    
    # Check for OpenAI API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set!")
        logger.error("   Please set it before running this script:")
        logger.error("   export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Initialize services
    logger.info("Initializing embeddings service...")
    embedding_service = EmbeddingsService(api_key=api_key)
    
    # Connect to database
    logger.info("Connecting to database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("✓ Connected to database\n")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)
    
    try:
        # Generate company embeddings
        generate_company_embeddings(embedding_service, conn)
        
        # Generate news embeddings
        generate_news_embeddings(embedding_service, conn)
        
    finally:
        conn.close()
        logger.info("\nDatabase connection closed")
    
    logger.info("\n" + "=" * 60)
    logger.info("EMBEDDING GENERATION COMPLETE!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
