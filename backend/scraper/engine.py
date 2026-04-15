"""
Scraper Engine - Orchestrates both scrapers, merges data, and stores in database.
"""

import logging
from .open_library import OpenLibraryClient
from .google_books import GoogleBooksClient

logger = logging.getLogger(__name__)


class ScraperEngine:
    """Orchestrates book scraping from multiple sources."""

    def __init__(self):
        self.ol_client = OpenLibraryClient()
        self.gb_client = GoogleBooksClient()

    def scrape_by_query(self, query, max_results=10):
        """
        Scrape books by search query from both sources.
        Returns list of merged book dicts.
        """
        # Get results from both sources
        ol_results = self.ol_client.search_books(query, max_results)
        gb_results = self.gb_client.search_books(query, max_results)

        # Parse results
        ol_parsed = [self.ol_client.parse_search_result(doc) for doc in ol_results]
        gb_parsed = [self.gb_client.parse_result(item) for item in gb_results]

        # Merge by trying to match titles
        merged = self._merge_results(ol_parsed, gb_parsed)

        # If we don't have enough from merging, add remaining Google Books results
        if len(merged) < max_results:
            for gb in gb_parsed:
                if len(merged) >= max_results:
                    break
                if not any(self._titles_match(m.get('title', ''), gb.get('title', '')) for m in merged):
                    merged.append(gb)

        return merged[:max_results]

    def scrape_by_isbn(self, isbn):
        """Scrape a single book by ISBN from both sources."""
        gb_result = self.gb_client.search_by_isbn(isbn)
        gb_parsed = self.gb_client.parse_result(gb_result) if gb_result else {}

        ol_result = self.ol_client.search_by_isbn(isbn)
        ol_parsed = {}
        if ol_result:
            # ISBN endpoint returns edition data, get work for description
            works = ol_result.get('works', [])
            if works:
                work_key = works[0].get('key', '')
                work = self.ol_client.get_work_details(work_key)
                if work:
                    desc = work.get('description', '')
                    if isinstance(desc, dict):
                        desc = desc.get('value', '')
                    ol_parsed['description'] = desc
                    ol_parsed['open_library_key'] = work_key
                    ol_parsed['subjects'] = work.get('subjects', [])[:10]

            ol_parsed['title'] = ol_result.get('title', '')
            ol_parsed['page_count'] = ol_result.get('number_of_pages')
            ol_parsed['publish_date'] = ol_result.get('publish_date', '')
            publishers = ol_result.get('publishers', [])
            ol_parsed['publisher'] = publishers[0] if publishers else ''
            covers = ol_result.get('covers', [])
            if covers:
                ol_parsed['cover_image_url'] = self.ol_client.get_cover_url(covers[0], 'L')

        if gb_parsed and ol_parsed:
            return self._merge_single(ol_parsed, gb_parsed)
        return gb_parsed or ol_parsed or None

    def _merge_results(self, ol_list, gb_list):
        """Merge two lists of book results, preferring more complete data."""
        merged = []
        used_gb = set()

        for ol in ol_list:
            best_match = None
            best_idx = -1
            for idx, gb in enumerate(gb_list):
                if idx in used_gb:
                    continue
                if self._titles_match(ol.get('title', ''), gb.get('title', '')):
                    best_match = gb
                    best_idx = idx
                    break

            if best_match:
                used_gb.add(best_idx)
                merged.append(self._merge_single(ol, best_match))
            else:
                merged.append(ol)

        return merged

    def _merge_single(self, ol_data, gb_data):
        """Merge data from Open Library and Google Books, preferring richer data."""
        merged = {}

        # Prefer non-empty values, with preferences per field
        merged['title'] = gb_data.get('title') or ol_data.get('title', '')
        merged['isbn'] = gb_data.get('isbn') or ol_data.get('isbn', '')
        merged['isbn13'] = gb_data.get('isbn13', '')

        # Prefer longer description
        ol_desc = ol_data.get('description', '')
        gb_desc = gb_data.get('description', '')
        merged['description'] = gb_desc if len(gb_desc) > len(ol_desc) else ol_desc

        merged['authors'] = gb_data.get('authors') or ol_data.get('authors', [])
        merged['author_keys'] = ol_data.get('author_keys', [])
        merged['publish_date'] = gb_data.get('publish_date') or ol_data.get('publish_date', '')
        merged['publisher'] = gb_data.get('publisher') or ol_data.get('publisher', '')
        merged['page_count'] = gb_data.get('page_count') or ol_data.get('page_count')
        merged['language'] = gb_data.get('language') or ol_data.get('language', 'en')

        # Categories from both
        categories = set(gb_data.get('categories', []))
        categories.update(ol_data.get('subjects', []))
        merged['categories'] = list(categories)[:10]

        # Ratings from Google Books
        merged['average_rating'] = gb_data.get('average_rating')
        merged['ratings_count'] = gb_data.get('ratings_count')

        # Cover: prefer Google Books (usually higher quality)
        merged['cover_image_url'] = gb_data.get('cover_image_url') or ol_data.get('cover_image_url', '')
        merged['preview_link'] = gb_data.get('preview_link', '')
        merged['info_link'] = gb_data.get('info_link', '')

        # Source IDs
        merged['open_library_key'] = ol_data.get('open_library_key', '')
        merged['google_books_id'] = gb_data.get('google_books_id', '')

        return merged

    def _titles_match(self, title1, title2):
        """Check if two titles likely refer to the same book."""
        if not title1 or not title2:
            return False
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()
        return t1 == t2 or t1 in t2 or t2 in t1

    def store_book(self, book_data):
        """Store scraped book data into Django models. Returns Book instance."""
        from books.models import Book, Author, Category

        # Check for duplicates
        isbn = book_data.get('isbn', '')
        title = book_data.get('title', '')

        existing = None
        if isbn:
            existing = Book.objects.filter(isbn=isbn).first()
        if not existing and title:
            existing = Book.objects.filter(title__iexact=title).first()

        if existing:
            logger.info(f"Book already exists: {existing.title}")
            return existing

        # Create book
        book = Book.objects.create(
            title=title,
            isbn=isbn,
            isbn13=book_data.get('isbn13', ''),
            description=book_data.get('description', ''),
            publish_date=book_data.get('publish_date', ''),
            publisher=book_data.get('publisher', ''),
            page_count=book_data.get('page_count'),
            language=book_data.get('language', 'en'),
            cover_image_url=book_data.get('cover_image_url', ''),
            preview_link=book_data.get('preview_link', ''),
            info_link=book_data.get('info_link', ''),
            average_rating=book_data.get('average_rating'),
            ratings_count=book_data.get('ratings_count'),
            open_library_key=book_data.get('open_library_key', ''),
            google_books_id=book_data.get('google_books_id', ''),
        )

        # Add authors
        for author_name in book_data.get('authors', []):
            author, _ = Author.objects.get_or_create(
                name=author_name,
                defaults={'bio': ''}
            )
            book.authors.add(author)

        # Add categories
        for cat_name in book_data.get('categories', []):
            if cat_name and len(cat_name) < 200:
                from django.utils.text import slugify
                slug = slugify(cat_name)[:200]
                if slug:
                    category, _ = Category.objects.get_or_create(
                        slug=slug,
                        defaults={'name': cat_name}
                    )
                    book.categories.add(category)

        logger.info(f"Stored book: {book.title}")
        return book
