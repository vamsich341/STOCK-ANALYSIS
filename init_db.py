#!/usr/bin/env python3
"""
Database Initialization Script
Run this script to initialize the database schema for the Stock Analysis application
"""

import psycopg2
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """
    Initialize the database by running the schema.sql file
    """
    logger.info("Connecting to database...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            sslmode='require'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("Database connected successfully")
        logger.info("Reading schema.sql...")
        
        # Read schema file
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        
        logger.info("Executing schema...")
        cursor.execute(schema_sql)
        
        logger.info("Schema executed successfully")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        logger.info(f"\nCreated {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        logger.info("\nDatabase initialization completed successfully!")
        logger.info("You can now run the application with: python app.py")
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except FileNotFoundError:
        logger.error("schema.sql file not found. Make sure you're running this from the project root.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("="*60)
    print("Stock Analysis Application - Database Initialization")
    print("="*60)
    print()
    print(f"Database: {Config.DB_NAME}")
    print(f"Host: {Config.DB_HOST}")
    print()
    print("This will create all required tables for the application.")
    print()
    
    response = input("Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = init_database()
        exit(0 if success else 1)
    else:
        print("Initialization cancelled.")
        exit(0)