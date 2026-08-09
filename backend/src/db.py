import datetime
import json
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("agent.db")

# Use a relative path from the script location so it stays in backend folder
DB_PATH = Path(__file__).parent.parent / "agent_data.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            language_preference TEXT,
            facts TEXT,
            last_interaction TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    logger.info(f"[DB INIT] SQLite Memory Database initialized at {DB_PATH}")


def save_caller(name: str, facts: dict, language_preference: str = "Hinglish"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    user_id = name.lower().strip()
    facts_str = json.dumps(facts)
    now = datetime.datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO users (user_id, name, language_preference, facts, last_interaction)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name,
            facts=excluded.facts,
            language_preference=excluded.language_preference,
            last_interaction=excluded.last_interaction
        """,
        (user_id, name, language_preference, facts_str, now),
    )
    conn.commit()
    conn.close()
    logger.info(f"[MEMORY SAVED] Saved memory record for caller '{name}' in agent_data.db")


def clean_name_query(identifier: str) -> str:
    s = identifier.strip().lower()
    prefixes = [
        "my name is ", "i am ", "i'm ", "im ", "mera naam ", 
        "name is ", "naam hai ", "this is ", "it's ", "its "
    ]
    for p in prefixes:
        if s.startswith(p):
            s = s[len(p):].strip()
    return s


def lookup_caller(name: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_name = clean_name_query(name)
    user_id = clean_name.lower().strip()
    search_pattern = f"%{user_id}%"

    # Match exact user_id or partial phrase
    cursor.execute(
        """
        SELECT name, language_preference, facts, last_interaction FROM users 
        WHERE user_id = ? 
           OR LOWER(name) = ?
           OR LOWER(name) LIKE ?
           OR ? LIKE '%' || LOWER(name) || '%'
        ORDER BY last_interaction DESC
        LIMIT 1
        """,
        (user_id, clean_name, search_pattern, clean_name),
    )
    row = cursor.fetchone()
    
    # Fallback to single word match if multi-word phrase
    if not row and " " in clean_name:
        words = [w for w in clean_name.split() if len(w) > 2]
        for w in words:
            w_pattern = f"%{w}%"
            cursor.execute(
                "SELECT name, language_preference, facts, last_interaction FROM users WHERE user_id LIKE ? OR LOWER(name) LIKE ? ORDER BY last_interaction DESC LIMIT 1",
                (w_pattern, w_pattern),
            )
            row = cursor.fetchone()
            if row:
                break

    conn.close()

    if row:
        return {
            "name": row[0],
            "language_preference": row[1],
            "facts": json.loads(row[2]) if row[2] else {},
            "last_interaction": row[3],
        }
    return None


def forget_caller(name: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_name = clean_name_query(name)
    user_id = clean_name.lower().strip()

    cursor.execute("DELETE FROM users WHERE user_id = ? OR LOWER(name) = ?", (user_id, clean_name))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# Initialize DB on module import
init_db()
