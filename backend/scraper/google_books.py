"""
Google Books API Client - Supplements Open Library with richer descriptions and ratings.
"""

import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksClient:
    """Client for querying the Google Books API (free tier, no key needed)."""

    def __init__(self):
        self.session = requests.Session()

    def search_books(self, query, max_results=10):
        """Search for books by title or query."""
        try:
            resp = self.session.get(
                BASE_URL,
                params={
                    'q': query,
                    'maxResults': min(max_results, 40),
                    'printType': 'books',
                    'orderBy': 'relevance',
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('items', [])
        except Exception as e:
            logger.error(f"Google Books search error: {e}")
            return []

    def search_by_isbn(self, isbn):
        """Search for a specific book by ISBN."""
        try:
            resp = self.session.get(
                BASE_URL,
                params={'q': f'isbn:{isbn}', 'maxResults': 1},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get('items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Google Books ISBN lookup error: {e}")
            return None

    def parse_result(self, item):
        """Parse a Google Books result into a standardized dict."""
        info = item.get('volumeInfo', {})
        identifiers = info.get('industryIdentifiers', [])

        isbn = ''
        isbn13 = ''
        for ident in identifiers:
            if ident.get('type') == 'ISBN_13':
                isbn13 = ident.get('identifier', '')
            elif ident.get('type') == 'ISBN_10':
                isbn = ident.get('identifier', '')

        # Get the best available cover image
        images = info.get('imageLinks', {})
        cover_url = (
            images.get('thumbnail', '') or
            images.get('smallThumbnail', '')
        )
        # Upgrade to HTTPS and larger size
        if cover_url:
            cover_url = cover_url.replace('http://', 'https://')
            cover_url = cover_url.replace('zoom=1', 'zoom=2')

        return {
            'title': info.get('title', ''),
            'authors': info.get('authors', []),
            'isbn': isbn or isbn13,
            'isbn13': isbn13,
            'description': info.get('description', ''),
            'publish_date': info.get('publishedDate', ''),
            'publisher': info.get('publisher', ''),
            'page_count': info.get('pageCount'),
            'language': info.get('language', 'en'),
            'categories': info.get('categories', []),
            'average_rating': info.get('averageRating'),
            'ratings_count': info.get('ratingsCount'),
            'cover_image_url': cover_url,
            'preview_link': info.get('previewLink', ''),
            'info_link': info.get('infoLink', ''),
            'google_books_id': item.get('id', ''),
        }
