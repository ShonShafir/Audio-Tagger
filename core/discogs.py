import requests
import time
import os

DISCOGS_BASE = "https://api.discogs.com"

# A realistic browser User-Agent allows anonymous Discogs API access without a personal token.
# Discogs checks UA to filter bots; a token additionally increases the rate limit from 25 to 60 req/min.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)

class DiscogsClient:
    def __init__(self, token: str = "", rate_limit: float = 2.0):
        self.token = token
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": BROWSER_UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        if token:
            self.session.headers["Authorization"] = f"Discogs token={token}"

    def _get(self, url: str, params: dict = None, retries: int = 3) -> dict:
        for attempt in range(retries):
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 429 and attempt < retries - 1:
                # Discogs rate limit exceeded. Wait 60 seconds (reset window) and retry.
                time.sleep(60)
                continue
            resp.raise_for_status()
            time.sleep(self.rate_limit)
            return resp.json()
        return {}

    def get_label_releases(self, label_id: int) -> list:
        """Fetch all releases for a label. Returns list of {catno, id, title, year, thumb}."""
        releases = []
        page = 1
        while True:
            data = self._get(f"{DISCOGS_BASE}/labels/{label_id}/releases", params={"page": page, "per_page": 100})
            releases.extend(data.get("releases", []))
            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 1):
                break
            page += 1
        return releases

    def get_release_images(self, release_id: int) -> list:
        """Fetch the images list for a specific release. Returns list of image dicts."""
        data = self._get(f"{DISCOGS_BASE}/releases/{release_id}")
        return data.get("images", [])

    def download_image(self, url: str, retries: int = 3) -> bytes:
        """Download an image from a Discogs CDN URL. Returns raw bytes."""
        for attempt in range(retries):
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 429 and attempt < retries - 1:
                time.sleep(60)
                continue
            resp.raise_for_status()
            time.sleep(self.rate_limit)
            return resp.content
        return b""

    def search_release(self, query: str) -> list:
        """Search for a release by string query. Returns list of results."""
        data = self._get(f"{DISCOGS_BASE}/database/search", params={"q": query, "type": "release"})
        return data.get("results", [])
