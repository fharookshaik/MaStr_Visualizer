#!/usr/bin/env python3
import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from logger import logger

load_dotenv()

async def check_db_has_data():
    """Check if database has MaStR data by checking if wind_extended table exists and has rows."""
    dsn = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    try:
        conn = await asyncpg.connect(dsn)
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'wind_extended'
            )
        """)
        if not table_exists:
            await conn.close()
            return False

        # Check if has rows
        row_count = await conn.fetchval("SELECT COUNT(*) FROM wind_extended")
        await conn.close()
        return row_count > 0
    except Exception as e:
        logger.error(f"Error checking DB: {e}")
        return False

async def main():
    logger.info("Checking if database has data...")
    has_data = await check_db_has_data()
    if has_data:
        logger.info("Database already has data. Skipping population.")
        return

    logger.info("Database is empty. Running MaStR orchestrator to populate...")
    # Import and run the orchestrator
    from mastr_orchestrator import main as run_orchestrator
    try:
        run_orchestrator(use_existing_if_available=True)
        logger.info("Database population completed successfully.")
    except Exception as e:
        logger.error(f"Error during population: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
