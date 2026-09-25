import re
import requests
from ytmusicapi import YTMusic
from typing import Optional, Dict, Any, List

class YouTubeClient:
    def __init__(self):
        # ytmusicapi requires no auth for public searches
        self.yt = YTMusic()

    def search_track(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a track by string (e.g. 'Avicii Levels')
        Returns the first match with filter='songs'
        """
        try:
            results = self.yt.search(query=query, filter="songs", limit=1)
            if results:
                return results[0]
        except Exception as e:
            print(f"ytmusicapi error: {e}")
        return None

    def download_image(self, url: str) -> bytes:
        """
        Download the image bytes. Modifies the url to get a high-res 1200x1200 image.
        """
        try:
            # ytmusic API usually returns URLs like: ...=w120-h120-l90-rj
            # We can replace the dimensions to get better quality
            high_res_url = re.sub(r'=w\d+-h\d+', '=w1200-h1200', url)
            resp = requests.get(high_res_url, timeout=10)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return b""
