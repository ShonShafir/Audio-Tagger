---
name: discogs-api-architecture
description: >-
  Expertise in the Discogs REST API. Use this skill when querying releases, implementing
  rate limiting and pagination, managing authentication tokens, and accurately parsing
  complex release variations, tracklists, and image objects.
---

# Discogs API Architecture Expert

This skill ensures robust, production-grade integration with the Discogs API.

## Core Directives

1. **Strict Rate Limiting**: The Discogs API limits unauthenticated users to 25 requests/min, and authenticated users to 60 requests/min. Implement a robust `time.sleep()` or Token Bucket throttle mechanism to NEVER exceed this, otherwise the IP gets banned.
2. **User-Agent**: Always pass a custom `User-Agent` header (e.g. `AudioTagger/1.0 +https://github.com/user/Audio-Tagger`). Discogs blocks generic Python `requests` User-Agents.
3. **Master vs Release**: Understand the difference between a Master release (the overarching album) and a Release (the specific pressing). Always resolve to the exact `Release` ID to get accurate catalog numbers, labels, and exact tracklists.
4. **Artists Array parsing**: Handle the `artists` array properly, stripping Discogs disambiguation numbers (e.g. "Artist (2)" -> "Artist") using `re.sub(r'\s\(\d+\)$', '', name)`.
5. **Image Downloads**: Discogs image URLs are heavily protected. You MUST pass your Personal Access Token in the Authorization header to download images, otherwise you receive a 403 Forbidden.
