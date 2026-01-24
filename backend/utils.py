import os
import asyncpg
from typing import Any

from dotenv import load_dotenv


load_dotenv()

class DBConfigenv:
    def __init__(self) -> None:
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")

    def get_dsn(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

class Database:
    def __init__(self, dsn: str, min_size: int = 5, max_size: int = 10):
        """
        Initialize the Database wrapper.

        :param dsn: Database connection string (e.g., "postgresql://user:password@localhost/dbname")
        :param min_size: Minimum size of the connection pool
        :param max_size: Maximum size of the connection pool
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Establish the connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
            )
        else:
            raise RuntimeError("Database pool is already connected.")

    async def disconnect(self):
        """Close the connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
        else:
            raise RuntimeError("Database pool is not connected.")

    async def execute(self, query: str, *args, timeout: float | None = None) -> str:
        """
        Execute a query that doesn't return data (e.g., INSERT, UPDATE, DELETE).

        :param query: SQL query string
        :param args: Parameters for the query
        :param timeout: Optional timeout in seconds
        :return: Status string (e.g., "INSERT 0 1")
        """
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def fetch(self, query: str, *args, timeout: float | None = None) -> list[asyncpg.Record]:
        """
        Fetch multiple rows from a query.

        :param query: SQL query string
        :param args: Parameters for the query
        :param timeout: Optional timeout in seconds
        :return: List of Record objects
        """
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchrow(self, query: str, *args, timeout: float | None = None) -> asyncpg.Record | None:
        """
        Fetch a single row from a query.

        :param query: SQL query string
        :param args: Parameters for the query
        :param timeout: Optional timeout in seconds
        :return: Record object or None if no row found
        """
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def fetchval(self, query: str, *args, column: int = 0, timeout: float | None = None) -> Any:
        """
        Fetch a single value from a query.

        :param query: SQL query string
        :param args: Parameters for the query
        :param column: Column index to return (default 0)
        :param timeout: Optional timeout in seconds
        :return: The value or None if no row found
        """
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)

    async def transaction(self):
        """
        Context manager for transactions.

        Usage:
        async with db.transaction() as conn:
            await conn.execute("...")
        """
        if self.pool is None:
            raise RuntimeError("Database pool is not connected.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn
