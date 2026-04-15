"""
Book Recommendation Engine.
Uses embedding similarity to find related books.
Falls back to category/author-based matching.
"""

import logging
from .embeddings import query_similar, generate_embedding, _get_collection

logger = logging.getLogger(__name__)


def get_recommendations(book, max_results=6):
    """
    Get recommended books similar to the given book.
    Uses a combination of embedding similarity and metadata matching.
    """
    from books.models import Book

    recommendations = []

    # Strategy 1: Embedding similarity via ChromaDB
    embedding_recs = _embedding_recommendations(book, max_results + 5)

    # Strategy 2: Category-based
    category_recs = _category_recommendations(book, max_results)

    # Strategy 3: Author-based
    author_recs = _author_recommendations(book, max_results)

    # Merge and score
    scored = {}

    # Embedding recommendations (highest weight)
    for rec in embedding_recs:
        book_id = rec['book_id']
        if book_id == book.id:
            continue
        scored[book_id] = scored.get(book_id, 0) + rec['similarity'] * 3

    # Category overlap (medium weight)
    for rec_book in category_recs:
        if rec_book.id == book.id:
            continue
        scored[rec_book.id] = scored.get(rec_book.id, 0) + 1.0

    # Same author (lower weight for diversity)
    for rec_book in author_recs:
        if rec_book.id == book.id:
            continue
        scored[rec_book.id] = scored.get(rec_book.id, 0) + 0.5

    # Sort by score and fetch books
    sorted_ids = sorted(scored.keys(), key=lambda x: scored[x], reverse=True)
    top_ids = sorted_ids[:max_results]

    if top_ids:
        books_map = {b.id: b for b in Book.objects.filter(id__in=top_ids)}
        for book_id in top_ids:
            if book_id in books_map:
                rec_book = books_map[book_id]
                recommendations.append({
                    'book': rec_book,
                    'score': round(scored[book_id], 3),
                    'reason': _get_recommendation_reason(book, rec_book),
                })

    return recommendations


def _embedding_recommendations(book, max_results=10):
    """Find similar books using embedding similarity."""
    # Build query from book content
    query_parts = [book.title]
    if book.description:
        query_parts.append(book.description[:500])
    if book.ai_themes:
        query_parts.append(' '.join(book.ai_themes))

    query_text = ' '.join(query_parts)

    try:
        results = query_similar(query_text, n_results=max_results)
        return [r for r in results if r['book_id'] != book.id]
    except Exception as e:
        logger.warning(f"Embedding recommendation error: {e}")
        return []


def _category_recommendations(book, max_results=10):
    """Find books with overlapping categories."""
    from books.models import Book

    categories = book.categories.all()
    if not categories:
        return []

    return Book.objects.filter(
        categories__in=categories
    ).exclude(id=book.id).distinct()[:max_results]


def _author_recommendations(book, max_results=5):
    """Find other books by the same author(s)."""
    from books.models import Book

    authors = book.authors.all()
    if not authors:
        return []

    return Book.objects.filter(
        authors__in=authors
    ).exclude(id=book.id).distinct()[:max_results]


def _get_recommendation_reason(source_book, rec_book):
    """Generate a human-readable reason for the recommendation."""
    reasons = []

    # Check shared authors
    source_authors = set(source_book.authors.values_list('id', flat=True))
    rec_authors = set(rec_book.authors.values_list('id', flat=True))
    shared_authors = source_authors & rec_authors
    if shared_authors:
        from books.models import Author
        names = Author.objects.filter(id__in=shared_authors).values_list('name', flat=True)
        reasons.append(f"Same author: {', '.join(names)}")

    # Check shared categories
    source_cats = set(source_book.categories.values_list('id', flat=True))
    rec_cats = set(rec_book.categories.values_list('id', flat=True))
    shared_cats = source_cats & rec_cats
    if shared_cats:
        from books.models import Category
        names = Category.objects.filter(id__in=shared_cats).values_list('name', flat=True)
        reasons.append(f"Similar genre: {', '.join(list(names)[:3])}")

    # Check shared themes
    if source_book.ai_themes and rec_book.ai_themes:
        shared = set(source_book.ai_themes) & set(rec_book.ai_themes)
        if shared:
            reasons.append(f"Shared themes: {', '.join(list(shared)[:3])}")

    if not reasons:
        reasons.append("Similar content based on AI analysis")

    return '; '.join(reasons)
