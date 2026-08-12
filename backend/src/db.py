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
    # Day 6 — learners who asked to stop receiving outbound calls. Keyed by the
    # normalized contact (SIP URI / number) we dial, so the dialer can refuse
    # to place a call before it ever rings.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opt_outs (
            contact TEXT PRIMARY KEY,
            name TEXT,
            reason TEXT,
            opted_out_at TIMESTAMP
        )
        """
    )
    # Day 7 — Human escalation tickets
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            customer_name TEXT,
            issue_summary TEXT,
            urgency TEXT,
            created_at TIMESTAMP
        )
        """
    )
    # Day 6 — the daily practice-call trigger. Each row is one learner's
    # standing request to be called at a time they picked (24h HH:MM, local).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS call_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            call_time TEXT,
            timezone TEXT DEFAULT 'local',
            active INTEGER DEFAULT 1,
            last_called_date TEXT,
            created_at TIMESTAMP
        )
        """
    )
    # Day 6 — outcome history, used for retry accounting and the demo write-up.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS call_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact TEXT,
            name TEXT,
            outcome TEXT,
            detail TEXT,
            attempt INTEGER,
            created_at TIMESTAMP
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


# =============================================================================
# Day 6 — Outbound calling: opt-out list, call schedules, call outcome log
# =============================================================================


def normalize_contact(contact: str) -> str:
    """Normalize a SIP URI / phone number into a stable lookup key.

    "sip:Aarav@example.com" and " AARAV@example.com " both map to the same key
    so the opt-out list and schedule can't be bypassed by casing/whitespace.
    """
    s = (contact or "").strip().lower()
    if s.startswith("sip:"):
        s = s[len("sip:"):]
    return s


def record_opt_out(
    contact: str, name: str = "", reason: str = "user requested"
) -> None:
    """Persist that this contact must not be called again."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    key = normalize_contact(contact)
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO opt_outs (contact, name, reason, opted_out_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(contact) DO UPDATE SET
            name=excluded.name,
            reason=excluded.reason,
            opted_out_at=excluded.opted_out_at
        """,
        (key, name, reason, now),
    )
    conn.commit()
    conn.close()
    # Stop any standing schedules for this contact too.
    deactivate_schedules_for_contact(contact)
    logger.info(f"[OPT-OUT] Recorded opt-out for contact '{key}' ({reason}).")


def is_opted_out(contact: str) -> bool:
    """True if this contact has asked us to stop calling."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    key = normalize_contact(contact)
    cursor.execute("SELECT 1 FROM opt_outs WHERE contact = ? LIMIT 1", (key,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def clear_opt_out(contact: str) -> bool:
    """Re-enable calling for a contact (e.g. they opted back in)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    key = normalize_contact(contact)
    cursor.execute("DELETE FROM opt_outs WHERE contact = ?", (key,))
    cleared = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return cleared


def add_schedule(
    name: str, contact: str, call_time: str, timezone: str = "local"
) -> int:
    """Register a standing daily practice call at the learner's chosen HH:MM.

    Returns the schedule id. Refuses to schedule an opted-out contact.
    """
    if is_opted_out(contact):
        raise ValueError(f"Contact '{contact}' has opted out; refusing to schedule.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO call_schedules
            (name, contact, call_time, timezone, active, last_called_date, created_at)
        VALUES (?, ?, ?, ?, 1, NULL, ?)
        """,
        (name, normalize_contact(contact), call_time, timezone, now),
    )
    schedule_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(
        f"[SCHEDULE] Added daily call for '{name}' at {call_time} (id={schedule_id})."
    )
    return schedule_id


def list_schedules(active_only: bool = True) -> list[dict]:
    """Return all call schedules (active only by default)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = (
        "SELECT id, name, contact, call_time, timezone, active, last_called_date "
        "FROM call_schedules"
    )
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY call_time"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "name": r[1],
            "contact": r[2],
            "call_time": r[3],
            "timezone": r[4],
            "active": bool(r[5]),
            "last_called_date": r[6],
        }
        for r in rows
    ]


def deactivate_schedule(schedule_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE call_schedules SET active = 0 WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


def deactivate_schedules_for_contact(contact: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE call_schedules SET active = 0 WHERE contact = ?",
        (normalize_contact(contact),),
    )
    conn.commit()
    conn.close()


def mark_schedule_called(schedule_id: int, date_str: str) -> None:
    """Stamp a schedule as handled for `date_str` so it won't re-fire today."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE call_schedules SET last_called_date = ? WHERE id = ?",
        (date_str, schedule_id),
    )
    conn.commit()
    conn.close()


def get_due_schedules(now_hhmm: str, today_str: str) -> list[dict]:
    """Schedules that should fire now: active, time reached, not yet called
    today, and not opted out."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, contact, call_time, timezone, active, last_called_date
        FROM call_schedules
        WHERE active = 1
          AND call_time <= ?
          AND (last_called_date IS NULL OR last_called_date != ?)
          AND contact NOT IN (SELECT contact FROM opt_outs)
        ORDER BY call_time
        """,
        (now_hhmm, today_str),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "name": r[1],
            "contact": r[2],
            "call_time": r[3],
            "timezone": r[4],
            "active": bool(r[5]),
            "last_called_date": r[6],
        }
        for r in rows
    ]


def log_call(
    contact: str, name: str, outcome: str, detail: str = "", attempt: int = 1
) -> None:
    """Record the result of one outbound call attempt."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO call_log (contact, name, outcome, detail, attempt, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (normalize_contact(contact), name, outcome, detail, attempt, now),
    )
    conn.commit()
    conn.close()
    logger.info(
        f"[CALL LOG] {name or contact}: outcome={outcome} attempt={attempt} {detail}"
    )


def count_attempts_today(contact: str, today_str: str) -> int:
    """How many call attempts we've already made to this contact today."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM call_log WHERE contact = ? AND created_at LIKE ?",
        (normalize_contact(contact), f"{today_str}%"),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def save_escalation(customer_name: str, issue_summary: str, urgency: str) -> str:
    """Save a human escalation ticket and return the ticket ID."""
    import random
    ticket_id = f"VV-{random.randint(1000, 9999)}"
    clean_name = clean_name_query(customer_name)
    now = datetime.datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tickets (ticket_id, customer_name, issue_summary, urgency, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (ticket_id, clean_name, issue_summary, urgency, now),
    )
    conn.commit()
    conn.close()
    
    logger.info("\n======================================")
    logger.info(f"🚨 NEW TICKET ESCALATION: {ticket_id}")
    logger.info(f"Learner: {clean_name}")
    logger.info(f"Issue: {issue_summary}")
    logger.info(f"Urgency: {urgency}")
    logger.info("======================================\n")
    
    return ticket_id


# Initialize DB on module import
init_db()
