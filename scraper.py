# scraper.py — REST API scraping steps
# Site uses WordPress REST API — no HTML scraping needed.
# All 215 partners + 18 news items fetched directly from API.

import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import db

API       = "https://www.kulturpass.lu/wp-json/wp/v2"
HEADERS   = {"User-Agent": "Mozilla/5.0 (compatible; KulturPassBot/1.0)"}
RAW_DIR   = Path("data/raw")
PROC_DIR  = Path("data/processed")
DELAY     = 0.5

# Category ID 9 = Young Audiences — most relevant for families
FAMILY_CAT_ID = 9
FAMILY_KEYWORDS = [
    "family", "famille", "famil", "kanner", "children", "kids", "enfant",
    "youth", "jeunes", "junior", "atelier", "workshop", "young", "jeune"
]


def _get(url: str, params: dict = None) -> dict | list | None:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return r.json(), r.headers
    except Exception as e:
        db.log("fetch", f"ERROR {url}: {e}")
        return None, {}


# ── Step 1: fetch all categories + all partners from REST API ─────────────────

def step1_fetch_all() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1a. Categories
    db.log("step1", "Fetching categories...")
    data, _ = _get(f"{API}/partner-category", {"per_page": 100})
    if data:
        for cat in data:
            db.save_category(cat)
        (RAW_DIR / "categories.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False))
        db.log("step1", f"{len(data)} categories saved.")

    # 1b. All partners (paginated, 100 per page)
    db.log("step1", "Fetching all partners...")
    page, total_saved = 1, 0
    all_partners = []
    while True:
        data, headers = _get(f"{API}/partner", {"per_page": 100, "page": page})
        if not data:
            break
        for p in data:
            score = _family_score(p)
            db.save_partner(p, family_score=score)
            all_partners.append(p)
            total_saved += 1
        total = int(headers.get("X-WP-Total", 0))
        db.log("step1", f"  page {page}: {len(data)} partners (total so far: {total_saved}/{total})")
        if total_saved >= total:
            break
        page += 1
        time.sleep(DELAY)

    (RAW_DIR / "partners.json").write_text(
        json.dumps(all_partners, indent=2, ensure_ascii=False))
    db.log("step1", f"All {total_saved} partners saved.")
    db.set_progress("step1_done", "true")
    db.set_progress("current_step", "2")


# ── Step 2: fetch all news/events ────────────────────────────────────────────

def step2_fetch_news() -> None:
    db.log("step2", "Fetching news/events...")
    data, headers = _get(f"{API}/news", {"per_page": 100})
    if data:
        for item in data:
            db.save_news(item)
        (RAW_DIR / "news.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False))
        db.log("step2", f"{len(data)} news items saved.")

    db.set_progress("step2_done", "true")
    db.set_progress("current_step", "3")


# ── Step 3: filter + export family-friendly partners ─────────────────────────

def step3_export_family() -> None:
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    with db.connect() as conn:
        partners = conn.execute(
            "SELECT wp_id,name,link,category_ids,family_score FROM partners "
            "ORDER BY family_score DESC"
        ).fetchall()

    categories = {}
    with db.connect() as conn:
        for c in conn.execute("SELECT id,name FROM categories"):
            categories[c["id"]] = c["name"]

    results = []
    for p in partners:
        cat_ids = json.loads(p["category_ids"] or "[]")
        cat_names = [categories.get(i, str(i)) for i in cat_ids]
        results.append({
            "name":         p["name"],
            "link":         p["link"],
            "categories":   cat_names,
            "family_score": p["family_score"],
            "young_audiences": FAMILY_CAT_ID in cat_ids,
        })

    # Young Audiences (cat 9) first, then by family_score
    family = [r for r in results if r["young_audiences"] or r["family_score"] > 0]
    family.sort(key=lambda x: (x["young_audiences"], x["family_score"]), reverse=True)

    out = PROC_DIR / "family_partners.json"
    out.write_text(json.dumps(family, indent=2, ensure_ascii=False))
    db.log("step3", f"{len(family)} family-friendly partners → {out}")

    # Also print top 10
    db.log("step3", "Top family partners:")
    for p in family[:10]:
        ya = "★" if p["young_audiences"] else " "
        db.log("step3", f"  {ya} [{p['family_score']}] {p['name']} — {', '.join(p['categories'])}")

    db.set_progress("step3_done", "true")
    db.set_progress("current_step", "done")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _family_score(partner: dict) -> int:
    """Score a partner for family-friendliness."""
    score = 0
    cat_ids = partner.get("partner-category", [])
    if FAMILY_CAT_ID in cat_ids:
        score += 5  # Young Audiences category = strong signal
    text = (partner.get("title",{}).get("rendered","") + " " +
            partner.get("content",{}).get("rendered","")).lower()
    score += sum(1 for kw in FAMILY_KEYWORDS if kw in text)
    return score
