import sqlite3
from telegram import Update, User
from typing import Optional
import logging

BOT_USERNAME = "LosMases"


class XPDatabase:
    """SQLite database for storing XP data."""

    def __init__(self, db_name="xp_data.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self._create_tables()

    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                xp_enabled INTEGER NOT NULL DEFAULT 0
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_xp (
                chat_id INTEGER,
                user_id INTEGER,
                xp INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
            );
        """
        )
        self.conn.commit()
        cursor.close()

    def enable_chat(self, chat_id):
        try:
            """Enable XP tracking for a chat."""
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_settings (chat_id, xp_enabled)
                VALUES (?, 1)
                ON CONFLICT(chat_id) DO UPDATE SET xp_enabled=1;
            """,
                (chat_id,),
            )
            self.conn.commit()
            cursor.close()
            return True
        except sqlite3.Error as _:
            return False

    def disable_chat(self, chat_id):
        """Disable XP tracking for a chat."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_settings (chat_id, xp_enabled)
                VALUES (?, 0)
                ON CONFLICT(chat_id) DO UPDATE SET xp_enabled=0;
            """,
                (chat_id,),
            )
            self.conn.commit()
            cursor.close()
            return True
        except sqlite3.Error as _:
            return False

    def is_chat_enabled(self, chat_id):
        """Check if XP tracking is enabled for a chat."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT xp_enabled FROM chat_settings
            WHERE chat_id=?
        """,
            (chat_id,),
        )
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return False
        return bool(result[0])

    def update_user_xp(self, chat_id, user_id, xp_delta):
        """Update a user's XP in the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_xp (chat_id, user_id, xp)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET xp=xp+?;
        """,
            (chat_id, user_id, xp_delta, xp_delta),
        )
        self.conn.commit()
        cursor.close()

    def get_user_xp(self, chat_id, user_id):
        """Get a user's current XP from the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT xp FROM user_xp
            WHERE chat_id=? AND user_id=?
        """,
            (chat_id, user_id),
        )
        result = cursor.fetchone()
        cursor.close()
        if result is None:
            return 0
        return result[0]

    def get_top_users(self, chat_id, limit=10):
        """Get the top users with the highest XP."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT user_id, xp FROM user_xp
            WHERE chat_id=?
            ORDER BY xp DESC
            LIMIT ?
        """,
            (chat_id, limit),
        )
        results = cursor.fetchall()
        cursor.close()
        return results

    def get_bot_added_by(self, chat_id):
        """Returns the user_id of the user who added the bot to a given group chat."""
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM groups WHERE chat_id = ?", (chat_id,))
        result = c.fetchone()
        return result[0] if result else None

    def get_medal(self, chat_id, user_id):
        top_3_id = self.get_top_users(chat_id)[:3]
        n = len(top_3_id)

        if n > 0 and user_id in top_3_id[0]:
            return "🥇"
        elif n > 1 and user_id in top_3_id[1]:
            return "🥈"
        elif n > 2 and user_id in top_3_id[2]:
            return "🥉"
        else:
            return ""

    def remove_user(self, user_id, chat_id):
        c = self.conn.cursor()
        c.execute(
            "DELETE FROM user_xp WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        )
        self.conn.commit()
        c.close()
