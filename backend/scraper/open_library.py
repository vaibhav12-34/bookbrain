"""
Open Library API Client - Scrapes book metadata from openlibrary.org
"""

import time
import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://openlibrary.org"
COVERS_URL = "https://covers.openlibrary.org"


class OpenLibraryClient:
    """Client for querying the Open Library API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BookBrain/1.0 (Educational Project)'
        })
        self._last_request_time = 0
        self._rate_limit_delay = 0.5  # seconds between requests

    def _rate_limit(self):
        """Simple rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def search_books(self, query, max_results=10):
        """Search for books by title or general query."""
        self._rate_limit()
        try:
            resp = self.session.get(
                f"{BASE_URL}/search.json",
                params={
                    'q': query,
                    'limit': max_results,
                    'fields': 'key,title,author_name,author_key,first_publish_year,'
                              'isbn,subject,cover_i,number_of_pages_median,language,'
                              'publisher,edition_count'
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('docs', [])
        except Exception as e:
            logger.error(f"Open Library search error: {e}")
            return []

    def search_by_isbn(self, isbn):
        """Search for a specific book by ISBN."""
        self._rate_limit()
        try:
            resp = self.session.get(
                f"{BASE_URL}/isbn/{isbn}.json",
                timeout=15
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Open Library ISBN lookup error: {e}")
            return None

    def get_work_details(self, work_key):
        """Get detailed info about a work (includes description)."""
        self._rate_limit()
        try:
            # work_key looks like /works/OL12345W
            url = f"{BASE_URL}{work_key}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Open Library work details error: {e}")
            return None

    def get_author_details(self, author_key):
        """Get author information."""
        self._rate_limit()
        try:
            url = f"{BASE_URL}/authors/{author_key}.json"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Open Library author details error: {e}")
            return None

    def get_cover_url(self, cover_id, size='M'):
        """Get cover image URL from cover ID."""
        if not cover_id:
            return ''
        return f"{COVERS_URL}/b/id/{cover_id}-{size}.jpg"

    def parse_search_result(self, doc):
        """Parse a search result document into a standardized dict."""
        cover_id = doc.get('cover_i')

        # Extract description from work if available
        description = ''
        work_key = doc.get('key', '')
        if work_key:
            work = self.get_work_details(work_key)
            if work:
                desc = work.get('description', '')
                if isinstance(desc, dict):
                    description = desc.get('value', '')
                elif isinstance(desc, str):
                    description = desc

        return {
            'title': doc.get('title', ''),
            'authors': doc.get('author_name', []),
            'author_keys': doc.get('author_key', []),
            'isbn': (doc.get('isbn', [None]) or [None])[0] or '',
            'publish_date': str(doc.get('first_publish_year', '')),
            'subjects': doc.get('subject', [])[:10],
            'cover_image_url': self.get_cover_url(cover_id, 'L'),
            'page_count': doc.get('number_of_pages_median'),
            'language': (doc.get('language', ['en']) or ['en'])[0],
            'publisher': (doc.get('publisher', ['']) or [''])[0],
            'description': description,
            'open_library_key': work_key,
        }
