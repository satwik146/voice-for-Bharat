import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("agent.db")

DB_PATH = Path(__file__).parent.parent / "memory.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database table for Day 4 persistent caller memory."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_preference TEXT DEFAULT 'Hinglish',
                facts TEXT DEFAULT '{}',
                consent_given INTEGER DEFAULT 0,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    logger.info(f"[DB INIT] SQLite Memory Database initialized at {DB_PATH}")


def lookup_caller(identifier: str):
    """
    Find caller facts by user_id or name in SQLite database.
    Supports partial name matching (e.g. 'Aarav' matches 'Aarav Kumar').
    """
    if not identifier:
        return None
    clean_name = identifier.strip().lower()
    search_pattern = f"%{clean_name}%"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users 
            WHERE LOWER(name) LIKE ? 
               OR LOWER(user_id) LIKE ? 
               OR ? LIKE '%' || LOWER(name) || '%'
            ORDER BY last_interaction DESC
            LIMIT 1
            """,
            (search_pattern, search_pattern, clean_name),
        )
        row = cursor.fetchone()
        if row:
            facts_data = json.loads(row["facts"]) if row["facts"] else {}
            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "language_preference": row["language_preference"],
                "facts": facts_data,
                "consent_given": bool(row["consent_given"]),
                "last_interaction": row["last_interaction"],
            }
    return None


def save_caller_memory(
    name: str,
    language_preference: str = "Hinglish",
    grade_or_level: str = "Beginner",
    topics_covered: str = "Vocabulary & Basic Math",
    frequent_mistakes: str = "None",
    consent_given: bool = True,
):
    """
    Save or update caller details and learning facts in SQLite database if consent is granted.
    """
    if not consent_given:
        logger.info(f"[CONSENT DECLINED] Caller {name} declined memory storage consent. Nothing saved.")
        return {"status": "declined", "message": "Memory not saved per user request."}

    user_id = name.strip().lower().replace(" ", "_")
    facts_obj = {
        "grade_or_level": grade_or_level,
        "topics_covered": topics_covered,
        "frequent_mistakes": frequent_mistakes,
    }
    facts_json = json.dumps(facts_obj)
    now_str = datetime.now().isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, name, language_preference, facts, consent_given, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                language_preference=excluded.language_preference,
                facts=excluded.facts,
                consent_given=excluded.consent_given,
                last_interaction=excluded.last_interaction
            """,
            (user_id, name, language_preference, facts_json, 1 if consent_given else 0, now_str),
        )
        conn.commit()

    logger.info(f"[MEMORY SAVED] Saved memory for returning learner '{name}' to SQLite DB.")
    return {
        "status": "saved",
        "user_id": user_id,
        "name": name,
        "facts": facts_obj,
    }


# Initialize DB on module import
init_db()
