# db.py — SQLite database setup and helpers
# All scraped data, progress, and logs stored here.
# File: data/kulturpass.db

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/kulturpass.db")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS progress (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS links (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url        TEXT UNIQUE,
            type       TEXT,
            source_url TEXT,
            fetched    INTEGER DEFAULT 0,
            parsed     INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url        TEXT UNIQUE,
            html       TEXT,
            status     INTEGER,
            fetched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            url            TEXT,
            partner_name   TEXT,
            title          TEXT,
            description    TEXT,
            date_text      TEXT,
            location       TEXT,
            category       TEXT,
            family_score   INTEGER DEFAULT 0,
            raw_json       TEXT,
            created_at     TEXT
        );
        CREATE TABLE IF NOT EXISTS logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            step       TEXT,
            message    TEXT,
            created_at TEXT
        );
        """)


def get_progress(key: str, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM progress WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_progress(key: str, value) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            "INSERT INTO progress(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, str(value), now)
        )


def log(step: str, message: str) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    print(f"[{step}] {message}")
    with connect() as conn:
        conn.execute("INSERT INTO logs(step,message,created_at) VALUES(?,?,?)",
                     (step, message, now))


def save_link(url: str, type_: str, source_url: str) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO links(url,type,source_url,created_at) VALUES(?,?,?,?)",
            (url, type_, source_url, now)
        )


def save_page(url: str, html: str, status: int) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pages(url,html,status,fetched_at) VALUES(?,?,?,?)",
            (url, html, status, now)
        )
        conn.execute("UPDATE links SET fetched=1 WHERE url=?", (url,))


def save_event(url: str, data: dict) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute("""
            INSERT INTO events(url,partner_name,title,description,date_text,
                               location,category,family_score,raw_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (url, data.get("partner_name",""), data.get("title",""),
             data.get("description",""), data.get("date_text",""),
             data.get("location",""), data.get("category",""),
             data.get("family_score", 0), json.dumps(data, ensure_ascii=False), now)
        )
        conn.execute("UPDATE links SET parsed=1 WHERE url=?", (url,))
