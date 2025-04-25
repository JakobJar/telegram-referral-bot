"""
Main entry point for the Telegram Referral Bot.

This script initializes the bot and starts the polling process.
It also ensures proper cleanup of database connections on exit.
"""

import atexit
from src import bot, get_top_referrers
from src.db_setup import close_db_pool, init_db_pool, create_database, create_tables
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Connecting to database...")
    init_db_pool()
    logger.debug("Creating database and tables if they don't exist...")
    create_database()
    create_tables()
    logger.info("Starting the bot...")
    # Register the database cleanup function to be called on exit
    atexit.register(close_db_pool)
    try:
        # Start the bot's polling process
        bot.infinity_polling(allowed_updates=['chat_member', 'message'])
    finally:
        # Ensure database connections are closed even if an exception occurs
        close_db_pool()
