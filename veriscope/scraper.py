"""veriscope/scraper.py

Lightweight on-page scraper using requests + BeautifulSoup to extract:
- <title>
- <meta name="description">
- primary <h1>

Performs simple validations (missing / too long) and returns structured results.
"""

from typing import Dict
import requests
from bs4 import BeautifulSoup


def scrape_onpage(url: str, timeout: int = 15) -> Dict:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "veriscope-bot/1.0"})
        resp.raise_for_status()
    except Exception as e:
        return {"error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_desc_tag = None
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc_tag = meta.get("content").strip()

    h1 = None
    h1_tag = soup.find("h1")
    if h1_tag and h1_tag.get_text(strip=True):
        h1 = h1_tag.get_text(strip=True)

    checks = {
        "title": title_tag,
        "title_length": len(title_tag) if title_tag else 0,
        "title_status": "missing" if not title_tag else ("too_long" if len(title_tag) > 70 else "ok"),
        "meta_description": meta_desc_tag,
        "meta_description_length": len(meta_desc_tag) if meta_desc_tag else 0,
        "meta_description_status": "missing" if not meta_desc_tag else ("too_long" if len(meta_desc_tag) > 165 else "ok"),
        "h1": h1,
        "h1_status": "missing" if not h1 else "ok",
    }

    return checks


if __name__ == "__main__":
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(json.dumps(scrape_onpage(url), indent=2))
