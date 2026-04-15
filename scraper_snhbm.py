# scraper_snhbm.py — fetch SNHBM vente properties via WP AJAX
# Run: uv run python scraper_snhbm.py
# Output: data/raw/snhbm_vente.json

import re
import json
import html as htmllib
from pathlib import Path
import requests
from bs4 import BeautifulSoup

VENTE_URL  = "https://snhbm.lu/projets/vente/"
AJAX_URL   = "https://snhbm.lu/wp-admin/admin-ajax.php"
HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; SNHBMBot/1.0)"}
OUT_RAW    = Path("data/raw/snhbm_vente.json")
OUT_HTML   = Path("data/processed/SHNBM_Properties.html")


def get_nonce() -> str:
    r = requests.get(VENTE_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    m = re.search(r'"nonce":"([^"]+)"', r.text)
    if not m:
        raise RuntimeError("Nonce not found on SNHBM page")
    return m.group(1)


def fetch_properties(nonce: str) -> list[dict]:
    r = requests.post(AJAX_URL, headers={**HEADERS, "Referer": VENTE_URL},
                      data={"action": "ajax_biens", "security": nonce}, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.find_all("article"):
        h3   = a.find("h3")
        link = h3.find("a")["href"] if h3 and h3.find("a") else ""
        title = htmllib.unescape(h3.get_text(strip=True)) if h3 else ""
        paras = a.find_all("p")
        loc_size = htmllib.unescape(paras[0].get_text(strip=True)) if paras else ""
        price    = htmllib.unescape(paras[1].get_text(strip=True)) if len(paras) > 1 else ""
        cats = [li.get_text(strip=True) for li in a.find_all("li")]
        img  = a.find("img")
        location, size = "", ""
        if " - " in loc_size:
            parts = loc_size.split(" - ", 1)
            location, size = parts[0].strip(), parts[1].strip()
        else:
            location = loc_size
        results.append({
            "title":      title,
            "link":       link,
            "location":   location,
            "size":       size,
            "price":      price,
            "categories": cats,
            "image":      img["src"] if img else "",
        })
    return results


def main():
    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    print("Fetching nonce...")
    nonce = get_nonce()
    print(f"Nonce: {nonce}")
    print("Fetching properties...")
    props = fetch_properties(nonce)
    print(f"Found {len(props)} properties")
    OUT_RAW.write_text(json.dumps(props, indent=2, ensure_ascii=False))
    print(f"Saved raw → {OUT_RAW}")
    return props


if __name__ == "__main__":
    main()
