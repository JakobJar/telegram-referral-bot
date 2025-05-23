"""
Database setup module for the Telegram Referral Bot.

This module handles the initialization, connection, and management of the PostgreSQL database.
It provides functions for creating the database, setting up tables, and managing database connections.
"""

import psycopg
from psycopg import ConnectionInfo
from psycopg_pool import ConnectionPool

from .config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

db_pool: ConnectionPool | None = None

is_testing = os.environ.get("TESTING", "False") == "True"


def init_db_pool():
    """
    Initialize the database connection pool.

    This function creates a SimpleConnectionPool with a minimum of 1 and maximum of 20 connections.
    It uses the database configuration from the config module.

    Raises:
        Exception: If there's an error initializing the connection pool.
    """
    global db_pool
    if db_pool is None:
        try:
            db_pool = ConnectionPool(f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
                                     min_size=1,
                                     max_size=20)
            db_pool.wait()
            logger.info("Database connection pool initialized.")
        except Exception as e:
            logger.error(f"Error initializing database connection pool: {e}")
            raise


def get_db_connection():
    """Get a connection from the pool."""
    return db_pool.connection()


@contextmanager
def get_db_cursor():
    """
    Context manager for database operations.

    Yields a database cursor and handles committing or rolling back transactions.
    """
    global db_pool
    if db_pool is None:
        init_db_pool()
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            yield cur
        conn.commit()


def create_database():
    """Create the database if it doesn't exist."""
    conn = None
    try:
        print(
            f"Attempting to connect to: host={DB_HOST}, port={DB_PORT}, user={DB_USER}, dbname=postgres"
        )
        conn = psycopg.connect(f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres")
        conn.autocommit = True
        with conn.cursor() as cur:
            db_name = DB_NAME if not is_testing else f"test_{DB_NAME}"
            cur.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,)
            )
            exists = cur.fetchone()
            if not exists:
                cur.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"Database '{db_name}' created.")
            else:
                logger.info(f"Database '{db_name}' already exists.")
    except psycopg.Error as e:
        logger.error(f"Error creating database: {e}")
    finally:
        if conn:
            conn.close()


def create_tables():
    """Create necessary tables if they don't exist."""
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS referral_codes (
                    unique_code VARCHAR(17) PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username VARCHAR(255),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS referral_codes_user_id ON referral_codes(user_id)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS used_referrals (
                    referred_user_id BIGINT NOT NULL PRIMARY KEY,
                    unique_code VARCHAR(17) NOT NULL REFERENCES referral_codes(unique_code),
                    referred_username VARCHAR(255),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS used_referrals_unique_code ON used_referrals(unique_code)")
        logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


def setup_database():
    """Set up the entire database: create DB, initialize pool, and create tables."""
    create_database()
    init_db_pool()
    create_tables()


def close_db_pool():
    """Close all connections in the database pool."""
    global db_pool
    if db_pool is not None:
        try:
            db_pool.close()
            logger.info("Database connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
        finally:
            db_pool = None
    else:
        logger.info("Database connection pool is already closed.")


if __name__ == "__main__":
    setup_database()
    print("Database setup complete.")
