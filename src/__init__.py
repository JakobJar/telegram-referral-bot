"""
Telegram Referral Bot

This module contains the core functionality for the Telegram Referral Bot,
including database operations, message handling, and bot commands.

The bot allows users to create referral links, track referrals, and manage
a referral system for a Telegram channel or group.

Key components:
- Database operations for storing and retrieving referral data
- Telegram bot command handlers
- Utility functions for referral code generation and management

Usage:
    Import this module to access the bot functionality and database operations.
    The bot can be started by running the `bot.infinity_polling()` method.
"""

import telebot
import logging
from typing import Optional
from datetime import datetime

from telebot import types
from telebot.types import ChatInviteLink

from .config import (
    BOT_TOKEN,
    CHANNEL_ID,
    DEBUG, SUBSCRIPTION_PRICE,
)
from .db_setup import get_db_connection, get_db_cursor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize the Telegram bot
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)


def extract_unique_code(link: ChatInviteLink) -> Optional[str]:
    """
    Extract the unique referral code from the invite link

    Args:
        link (ChatInviteLink): The full text of the message, including the command.

    Returns:
        Optional[str]: The extracted unique code if found, or None if not present.
    """
    if link is None or link.invite_link is None:
        return None
    parts = link.invite_link.split("/")
    return parts[-1]


def get_user_message_link(user_id: int, username: str) -> str:
    """
    Generate a link to the user for a message.

    Args:
        user_id (int): The user id of the user.
        username (str): The username of the user

    Returns:
        str: Link to the user for a message.
    """
    if username is None:
        return f"<a href=\"tg://user?id={user_id}\">Unknown User</a>"
    return f"<a href=\"tg://user?id={user_id}\">{username}</a>"


def get_user_id_from_storage(unique_code: str) -> Optional[int]:
    """
    Retrieve the user id associated with a given unique code from the database.

    Args:
        unique_code (str): The unique referral code.

    Returns:
        Optional[int]: The associated user_id, or None if not found.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT user_id FROM referral_codes WHERE unique_code = %s",
                (unique_code,),
            )
            result = cur.fetchone()
            logger.debug(f"get_user_id_from_storage result: {result}")
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error in get_user_id_from_storage: {e}")
        return None


def grab_referral_code(user_id: int) -> Optional[str]:
    """
    Retrieve the referral code for a given user id from the database.

    Args:
        user_id (int): The username to look up.

    Returns:
        Optional[str]: The referral code, or None if not found.
    """
    logger.debug(f"Attempting to grab referral code for user: {user_id}")
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT unique_code FROM referral_codes WHERE user_id = %s", (user_id,)
            )
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                logger.debug(f"No referral code found for user: {user_id}")
                return None
    except Exception as e:
        logger.error(f"Error in grab_referral_code: {e}")
        return None


def create_unique_code() -> str:
    """
    Generate a new unique referral code.

    Returns:
        str: A 17-character string.
    """
    if SUBSCRIPTION_PRICE > 0:
        invite = bot.create_chat_subscription_invite_link(CHANNEL_ID, 2592000, SUBSCRIPTION_PRICE)
    else:
        invite = bot.create_chat_invite_link(CHANNEL_ID)
    return extract_unique_code(invite)


def create_referral_code(sender_user_id: int, sender_username: str) -> Optional[str]:
    """
    Create a new referral code for a user or retrieve an existing one.

    Args:
        sender_user_id (int): The user id of the user requesting a code.
        sender_username (str): The username of the user requesting a code.

    Returns:
        Optional[str]: The new or existing referral code, or None if an error occurred.
    """
    logger.debug(f"Creating new referral code for {sender_username}({sender_user_id})")
    try:
        unique_code = create_unique_code()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO referral_codes (unique_code, user_id, username)
                    VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING RETURNING unique_code
                    """,
                    (unique_code, sender_user_id, sender_username),
                )
                result = cur.fetchone()
                if result:
                    logger.debug(
                        f"Successfully inserted code {unique_code} for user {sender_username}({sender_user_id})"
                    )
                    return unique_code
                else:
                    logger.debug(f"Code already exists for user {sender_username}({sender_user_id})")
                    return grab_referral_code(sender_user_id)
    except Exception as e:
        logger.error(f"Error in create_referral_code: {e}")
        return None


def add_user(unique_code: str, sender_user_id: int, sender_username: str) -> bool:
    """
    Add a user to the used_referrals table.

    Args:
        unique_code (str): The unique referral code.
        sender_user_id (int): The user ID to add.
        sender_username (str): The username to add.

    Returns:
        bool: True if the user was added successfully, False otherwise.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO used_referrals (unique_code, referred_user_id, referred_username)
                VALUES (%s, %s, %s) ON CONFLICT (referred_user_id) DO NOTHING
                """,
                (unique_code, sender_user_id, sender_username),
            )
        return True
    except Exception as e:
        logger.error(f"Error in add_user: {e}")
        return False


def check_new_user(sender_user_id: int) -> bool:
    """
    Check if the user is new (not in the used_referrals table).

    Args:
        sender_user_id (int): The user ID to check.

    Returns:
        bool: True if the user is new, False otherwise.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT referred_user_id
                FROM used_referrals
                WHERE referred_user_id = %s;
                """,
                (sender_user_id,),
            )
            result = cur.fetchone()
            logger.debug(f"check_new_user result for user_id {sender_user_id}: {result}")
            return result is None
    except Exception as e:
        logger.error(f"Error in check_new_user: {e}")
        return False


def check_user_exists(sender_user_id: int) -> Optional[bool]:
    """
    Check if a user exists in the referrals table.

    Args:
        sender_user_id (int): The user id to check.

    Returns:
        Optional[bool]: True if the user exists, False if not, None if an error occurred.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                "SELECT * FROM referral_codes WHERE user_id = %s;",
                (sender_user_id,)
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error in check_user_exists: {e}")
        return None


def check_user_is_admin(user_id: int) -> bool:
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status == "administrator" or status == "creator"
    except Exception as e:
        logger.debug(f"Error in check_user_is_admin: {e}")
        return False


def get_referral_amount(user_id: int) -> int:
    """
    Get the referral count for a given username.

    Args:
        user_id (str): The username to look up.

    Returns:
        int: The referral count for the user, or 0 if not found or an error occurred.
    """
    logger.debug(f"Getting referral count for user: {user_id}")
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM referral_codes
                         INNER JOIN used_referrals USING (unique_code)
                WHERE user_id = %s;
                """,
                (user_id,)
            )
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                logger.debug(f"No referral count found for user: {user_id}")
                return 0
    except Exception as e:
        logger.error(f"Error in get_referral_amount: {e}")
        return 0


def get_top_referrers() -> list[tuple[int, str, int]]:
    """
    Generated a list of top referrers based on referral count.

    Returns:
        list[tuple[int, str, int]]: A list of tuples containing username and referral count.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT c.user_id, c.username, COUNT(*) AS referral_count
                FROM referral_codes c
                         INNER JOIN used_referrals r USING (unique_code)
                GROUP BY c.user_id, c.username
                HAVING COUNT(*) > 0
                ORDER BY referral_count DESC LIMIT 10;
                """,
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error in get_top_referrers: {e}")
        return []


def get_latest_referrals() -> list[tuple[int, str, int, str, datetime]]:
    """
    Generated a list of top referrers based on referral count.

    Returns:
        list[tuple[int, str, int, str, datetime]]: A list of tuples containing username and referral count.
    """
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT c.user_id, c.username, r.referred_user_id, r.referred_username, r.created_at
                FROM referral_codes c
                         INNER JOIN used_referrals r USING (unique_code)
                ORDER BY r.created_at DESC LIMIT 10;
                """,
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error in get_latest_referrals: {e}")
        return []


@bot.chat_member_handler()
def handle_join(member: types.ChatMemberUpdated):
    """
    Handles the join of a new member to the channel.
    Checks if the user is a referrer and adds them to the used_referrals table.

    Args:
        member (types.ChatMemberUpdated): The incoming Telegram message.
    """
    if member.chat.username != CHANNEL_ID[1:]:
        return
    unique_code = extract_unique_code(member.invite_link)
    from_user = member.from_user
    user_id = from_user.id
    username = from_user.username if from_user.username else from_user.full_name

    logger.debug(
        f"Received member update User ID: {user_id}, Username: {username}, Unique code: {unique_code}, Old Status: {member.old_chat_member.status}, New Status: {member.new_chat_member.status}"
    )

    if not unique_code:
        return

    referrer_id = get_user_id_from_storage(unique_code)
    logger.debug(f"Referrer username: {referrer_id}")

    if referrer_id == user_id:
        return

    if referrer_id and check_new_user(user_id):
        logger.debug(f"User @{username} has been referred by @{referrer_id}!")
        add_user_result = add_user(unique_code, user_id, username)
        if not add_user_result:
            return
        bot.send_message(referrer_id, f"You have successfully referred {get_user_message_link(user_id, username)}!")
    elif referrer_id:
        logger.debug(f"User has already been referred.")
    else:
        logging.debug("No referral link found.")


@bot.message_handler(commands=["start"])
def create_code(message: types.Message):
    """
    Handle the /start command to generate a new referral code or retrieve an existing one.

    Args:
        message (telebot.types.Message): The incoming Telegram message.
    """
    from_user = message.from_user
    sender_user_id = from_user.id
    sender_username = from_user.username if from_user.username else from_user.full_name
    logger.debug(f"Creating code for user: {sender_username}({sender_user_id})")

    # First, try to get an existing code
    existing_code = grab_referral_code(sender_user_id)
    if existing_code:
        reply = f"You have already created a referral link! Your referral link is:\nhttps://t.me/{existing_code}"
        bot.reply_to(message, reply)
        return

    # If no existing code, create a new one
    unique_code = create_referral_code(sender_user_id, sender_username)
    if unique_code:
        reply = f"Your referral link is:\nhttps://t.me/{unique_code}"
    else:
        reply = "An error occurred. Please try again later."

    bot.reply_to(message, reply)


@bot.message_handler(commands=["check"])
def check_ref(message: types.Message):
    """
    Handle the /check command to retrieve and display the user's referral count.

    Args:
        message (telebot.types.Message): The incoming Telegram message.
    """
    user_id = message.from_user.id
    logger.debug(f"Checking referral for user: {user_id}")

    user_exists = check_user_exists(user_id)
    if user_exists is None:
        bot.reply_to(message, "An error occurred. Please try again later.")
        return
    if not user_exists:
        bot.reply_to(message, "You do not have a referral code! Please create one using /start")
        return

    referral_amount = get_referral_amount(user_id)
    logger.debug(f"Retrieved referral amount: {referral_amount}")
    reply = f"Referral amount: {referral_amount}"
    bot.reply_to(message, reply)


@bot.message_handler(commands=["top"])
def check_top(message: types.Message):
    """
    Handle the /top command to retrieve and display the top referrers.

    Args:
        message (telebot.types.Message): The incoming Telegram message.
    """
    top_referrers = get_top_referrers()
    logger.debug(f"Retrieved top referrers: {top_referrers}")
    reply = "<b>Top referrers:</b>\n"
    for user_id, username, referral_count in top_referrers:
        reply += f"- {get_user_message_link(user_id, username)}: {referral_count}\n"
    bot.reply_to(message, reply, parse_mode="html")


@bot.message_handler(commands=["latest"])
def check_latest(message: types.Message):
    """
    Handle the /latest command to retrieve and display the latest referrers.

    Args:
        message (telebot.types.Message): The incoming Telegram message.
    """
    if not check_user_is_admin(message.from_user.id):
        bot.reply_to(message, "You do not have permission to use this command.")
        return
    latest_referrers = get_latest_referrals()
    logger.debug(f"Retrieved latest referrers: {latest_referrers}")
    reply = "<b>Latest referrals:</b>\n"
    for referrer_user_id, referrer_username, referred_user_id, referred_username, timestamp in latest_referrers:
        reply += f"- {get_user_message_link(referrer_user_id, referrer_username)} referred {get_user_message_link(referred_user_id, referred_username)} on {str(timestamp.strftime("%Y-%m-%d %H:%M:%S"))}\n"
    bot.reply_to(message, reply, parse_mode="html")


if __name__ == "__main__":
    bot.infinity_polling()
