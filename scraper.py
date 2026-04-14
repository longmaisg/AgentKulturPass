# scraper.py — step functions for each scraping round
# Each step reads from DB, does work, saves back to DB.
# Steps are idempotent — safe to re-run if interrupted.

import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import db

BASE_URL   = "https://www.kulturpass.lu"
INDEX_URL  = "https://www.kulturpass.lu/en/partners/"
HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; KulturPassBot/1.0)"}
DELAY      = 1.5   # seconds between requests — be polite
RAW_DIR    = Path("data/raw")

FAMILY_KEYWORDS = [
    "family", "famille", "famil", "kanner", "children", "kids", "enfants",
    "youth", "jeunes", "junior", "atelier", "workshop", "show", "spektakel"
]


def _get(url: str) -> tuple[str, int]:
    """Fetch URL. Returns (html, status_code)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.text, r.status_code
    except Exception as e:
        db.log("fetch", f"ERROR fetching {url}: {e}")
        return "", 0


# ── Step 1: fetch the partners index page, extract all partner links ──────────

def step1_fetch_index() -> None:
    db.log("step1", f"Fetching index: {INDEX_URL}")
    html, status = _get(INDEX_URL)
    if not html:
        db.log("step1", "FAILED — empty response")
        return

    # Save raw HTML
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "index.html").write_text(html, encoding="utf-8")
    db.save_page(INDEX_URL, html, status)

    # Extract partner links
    soup = BeautifulSoup(html, "html.parser")
    links_found = 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        if not href.startswith("http"):
            href = BASE_URL + href
        if "kulturpass.lu" in href and href != INDEX_URL:
            db.save_link(href, "partner", INDEX_URL)
            links_found += 1

    db.set_progress("step1_done", "true")
    db.set_progress("current_step", "2")
    db.log("step1", f"Done. {links_found} links saved.")


# ── Step 2: fetch each partner page, save raw HTML ───────────────────────────

def step2_fetch_partners() -> bool:
    """Fetch one batch of unfetched partner links. Returns True when all done."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT url FROM links WHERE fetched=0 LIMIT 10"
        ).fetchall()

    if not rows:
        db.set_progress("step2_done", "true")
        db.set_progress("current_step", "3")
        db.log("step2", "All partner pages fetched.")
        return True

    for row in rows:
        url = row["url"]
        db.log("step2", f"Fetching: {url}")
        html, status = _get(url)
        db.save_page(url, html, status)

        # Save raw file
        fname = url.replace("https://", "").replace("/", "_")[:80] + ".html"
        (RAW_DIR / fname).write_text(html, encoding="utf-8")
        time.sleep(DELAY)

    return False


# ── Step 3: parse event details from each fetched page ───────────────────────

def step3_parse_events() -> bool:
    """Parse one batch of fetched-but-unparsed pages. Returns True when done."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT l.url, p.html FROM links l JOIN pages p ON l.url=p.url "
            "WHERE l.fetched=1 AND l.parsed=0 LIMIT 20"
        ).fetchall()

    if not rows:
        db.set_progress("step3_done", "true")
        db.set_progress("current_step", "4")
        db.log("step3", "All pages parsed.")
        return True

    for row in rows:
        url, html = row["url"], row["html"]
        if not html:
            with db.connect() as conn:
                conn.execute("UPDATE links SET parsed=1 WHERE url=?", (url,))
            continue

        soup = BeautifulSoup(html, "html.parser")
        data = _parse_page(soup, url)
        db.save_event(url, data)

    return False


def _parse_page(soup: BeautifulSoup, url: str) -> dict:
    """Extract all useful fields from a partner page."""
    title       = soup.find("h1")
    description = soup.find("meta", {"name": "description"})
    og_title    = soup.find("meta", {"property": "og:title"})
    og_desc     = soup.find("meta", {"property": "og:description"})

    text = soup.get_text(" ", strip=True).lower()
    family_score = sum(1 for kw in FAMILY_KEYWORDS if kw in text)

    # Grab all visible text blocks as raw data
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]

    return {
        "partner_name": (og_title or title or {}).get("content") or (title.get_text(strip=True) if title else ""),
        "title":        (og_title or {}).get("content") or (title.get_text(strip=True) if title else ""),
        "description":  (og_desc or description or {}).get("content", ""),
        "date_text":    "",   # extracted in later pass if available
        "location":     "",
        "category":     _guess_category(url, text),
        "family_score": family_score,
        "paragraphs":   paragraphs[:10],
        "url":          url,
    }


def _guess_category(url: str, text: str) -> str:
    cats = {"museum": "museum", "theatre": "theatre", "music": "music",
            "concert": "music", "cinema": "cinema", "sport": "sport",
            "art": "art", "gallery": "art"}
    for kw, cat in cats.items():
        if kw in url.lower() or kw in text[:500]:
            return cat
    return "other"


# ── Step 4: filter and rank family events ────────────────────────────────────

def step4_filter_family() -> None:
    with db.connect() as conn:
        events = conn.execute(
            "SELECT url, partner_name, title, description, category, family_score "
            "FROM events ORDER BY family_score DESC"
        ).fetchall()

    results = [dict(e) for e in events]
    family  = [e for e in results if e["family_score"] > 0]

    import json
    out = Path("data/processed/family_events.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(family, indent=2, ensure_ascii=False))

    db.set_progress("step4_done", "true")
    db.set_progress("current_step", "done")
    db.log("step4", f"Done. {len(family)} family-friendly events saved to {out}")
