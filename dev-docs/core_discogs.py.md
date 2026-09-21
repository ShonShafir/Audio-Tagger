# `core/discogs.py`

**Purpose**: A dedicated HTTP client for interacting with the Discogs API to fetch release metadata and download cover art.

## Key Components

### `DiscogsClient`
A wrapper around the `requests` library, initialized with the user's personal API token and a configured rate limit.

- **Authentication**: Injects the API token into the `Authorization: Discogs token=XYZ` header.
- **Rate Limiting**: Includes an internal `_last_call` timestamp and utilizes `time.sleep()` before firing requests to ensure the application does not get HTTP 429 (Too Many Requests) bans from Discogs.
- **`search_release(catno)`**: Queries the `/database/search` endpoint specifically targeting `catno` (Catalog Number). It returns the top match.
- **`download_image(url)`**: A dedicated endpoint fetcher for cover art that respects the same authentication headers and rate limits.

### Error Handling
The client uses `requests.exceptions.RequestException` to catch network timeouts or API errors, safely returning empty dictionaries or `None` instead of crashing the background worker.
