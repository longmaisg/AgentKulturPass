# db.py — SQLite database setup and helpers
# Tables: categories, partners, news, progress, logs
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
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS progress (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY,
            name       TEXT,
            slug       TEXT,
            count      INTEGER
        );
        CREATE TABLE IF NOT EXISTS partners (
            wp_id        INTEGER PRIMARY KEY,
            name         TEXT,
            link         TEXT,
            category_ids TEXT,
            content_html TEXT,
            website      TEXT,
            address      TEXT,
            phone        TEXT,
            email        TEXT,
            family_score INTEGER DEFAULT 0,
            raw_json     TEXT,
            created_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS news (
            wp_id      INTEGER PRIMARY KEY,
            title      TEXT,
            link       TEXT,
            content    TEXT,
            date       TEXT,
            raw_json   TEXT,
            created_at TEXT
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
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (key, str(value), now)
        )


def log(step: str, message: str) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    print(f"[{step}] {message}")
    with connect() as conn:
        conn.execute("INSERT INTO logs(step,message,created_at) VALUES(?,?,?)",
                     (step, message, now))


def save_category(data: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO categories(id,name,slug,count) VALUES(?,?,?,?)",
            (data["id"], data["name"], data.get("slug",""), data.get("count",0))
        )


def save_partner(data: dict, family_score: int = 0) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    cat_ids = json.dumps(data.get("partner-category", []))
    with connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO partners
            (wp_id,name,link,category_ids,content_html,website,address,
             phone,email,family_score,raw_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["title"]["rendered"], data.get("link",""),
             cat_ids, data.get("content",{}).get("rendered",""),
             data.get("_website",""), data.get("_address",""),
             data.get("_phone",""), data.get("_email",""),
             family_score, json.dumps(data, ensure_ascii=False), now)
        )


def save_news(data: dict) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO news(wp_id,title,link,content,date,raw_json,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (data["id"], data["title"]["rendered"], data.get("link",""),
             data.get("content",{}).get("rendered",""),
             data.get("date",""), json.dumps(data, ensure_ascii=False), now)
        )
