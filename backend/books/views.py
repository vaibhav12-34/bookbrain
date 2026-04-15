"""
BookBrain API Views - REST endpoints for books, scraping, and AI.
"""

import logging
import threading
from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Book, Author, Category
from .serializers import (
    BookListSerializer, BookDetailSerializer, BookUploadSerializer,
    BulkScrapeSerializer, QuestionSerializer, AnswerSerializer,
    AuthorSerializer, CategorySerializer,
)

logger = logging.getLogger(__name__)


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving books.
    
    list: GET /api/books/ - Lists all uploaded books
    retrieve: GET /api/books/<id>/ - Retrieves full detail about a book
    """
    queryset = Book.objects.prefetch_related('authors', 'categories').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)

        # Filter by author
        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(authors__name__icontains=author)

        # Search
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(authors__name__icontains=search)
            ).distinct()

        # Filter by processing status
        processed = self.request.query_params.get('processed')
        if processed is not None:
            queryset = queryset.filter(is_processed=processed.lower() == 'true')

        return queryset

    @action(detail=True, methods=['get'])
    def recommendations(self, request, pk=None):
        """GET /api/books/<id>/recommendations/ - Get recommended books."""
        book = self.get_object()
        
        try:
            from ai_engine.recommendations import get_recommendations
            recs = get_recommendations(book, max_results=6)

            results = []
            for rec in recs:
                rec_book = rec['book']
                results.append({
                    'id': rec_book.id,
                    'title': rec_book.title,
                    'authors': [a.name for a in rec_book.authors.all()],
                    'cover_image_url': rec_book.cover_image_url,
                    'average_rating': rec_book.average_rating,
                    'score': rec['score'],
                    'reason': rec['reason'],
                })
            
            return Response({
                'book_id': book.id,
                'book_title': book.title,
                'recommendations': results,
            })
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return Response(
                {'error': f'Failed to generate recommendations: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthorListView(generics.ListAPIView):
    """GET /api/authors/ - List all authors."""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ - List all categories."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BookUploadView(APIView):
    """POST /api/books/upload/ - Upload/search and add a book by ISBN or title."""

    def post(self, request):
        serializer = BookUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']
        search_type = serializer.validated_data.get('search_type', 'title')

        try:
            from scraper.engine import ScraperEngine
            engine = ScraperEngine()

            if search_type == 'isbn':
                book_data = engine.scrape_by_isbn(query)
                if not book_data:
                    return Response(
                        {'error': f'No book found with ISBN: {query}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                book = engine.store_book(book_data)
                books = [book]
            else:
                results = engine.scrape_by_query(query, max_results=5)
                if not results:
                    return Response(
                        {'error': f'No books found for: {query}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                books = [engine.store_book(r) for r in results]

            # Process AI insights in background
            def process_books(book_list):
                from ai_engine.insights import process_book_insights
                from ai_engine.embeddings import store_book_embeddings
                for b in book_list:
                    try:
                        if not b.is_processed:
                            process_book_insights(b)
                            store_book_embeddings(b)
                    except Exception as e:
                        logger.error(f"Error processing {b.title}: {e}")

            thread = threading.Thread(target=process_books, args=(books,))
            thread.daemon = True
            thread.start()

            return Response({
                'message': f'Successfully added {len(books)} book(s). AI processing started.',
                'books': BookListSerializer(books, many=True).data,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Book upload error: {e}")
            return Response(
                {'error': f'Failed to process book: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkScrapeView(APIView):
    """POST /api/books/scrape/ - Trigger bulk scraping by topic."""

    def post(self, request):
        serializer = BulkScrapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        topic = serializer.validated_data['topic']
        max_results = serializer.validated_data.get('max_results', 10)

        try:
            from scraper.engine import ScraperEngine
            engine = ScraperEngine()

            results = engine.scrape_by_query(topic, max_results=max_results)
            books = [engine.store_book(r) for r in results if r]

            # Process in background
            def process_books(book_list):
                from ai_engine.insights import process_book_insights
                from ai_engine.embeddings import store_book_embeddings
                for b in book_list:
                    try:
                        if not b.is_processed:
                            process_book_insights(b)
                            store_book_embeddings(b)
                    except Exception as e:
                        logger.error(f"Error processing {b.title}: {e}")

            thread = threading.Thread(target=process_books, args=(books,))
            thread.daemon = True
            thread.start()

            return Response({
                'message': f'Scraped {len(books)} books for "{topic}". AI processing started in background.',
                'books': BookListSerializer(books, many=True).data,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Bulk scrape error: {e}")
            return Response(
                {'error': f'Scraping failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AskQuestionView(APIView):
    """POST /api/books/ask/ - Ask a question about books using RAG."""

    def post(self, request):
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data['question']
        book_id = serializer.validated_data.get('book_id')

        try:
            from ai_engine.rag import ask_question
            result = ask_question(question, book_id=book_id)

            # Enrich response with full book details for matched sources
            source_book_ids = [s['book_id'] for s in result.get('sources', [])]
            matched_books = []
            if source_book_ids:
                books_qs = Book.objects.filter(
                    id__in=source_book_ids
                ).prefetch_related('authors', 'categories')
                for book in books_qs:
                    matched_books.append({
                        'id': book.id,
                        'title': book.title,
                        'authors': [a.name for a in book.authors.all()],
                        'cover_image_url': book.cover_image_url,
                        'description': book.description[:500] if book.description else '',
                        'ai_summary': book.ai_summary,
                        'ai_themes': book.ai_themes or [],
                        'ai_sentiment': book.ai_sentiment,
                        'ai_reading_level': book.ai_reading_level,
                        'ai_key_topics': book.ai_key_topics or [],
                        'categories': [c.name for c in book.categories.all()],
                        'average_rating': book.average_rating,
                        'publish_date': book.publish_date,
                        'page_count': book.page_count,
                        'language': book.language,
                    })

            result['matched_books'] = matched_books

            # Get recommendations based on matched books
            recommendations = []
            if matched_books:
                try:
                    from ai_engine.recommendations import get_recommendations
                    first_book = books_qs.first()
                    if first_book:
                        recs = get_recommendations(first_book, max_results=4)
                        for rec in recs:
                            rb = rec['book']
                            recommendations.append({
                                'id': rb.id,
                                'title': rb.title,
                                'authors': [a.name for a in rb.authors.all()],
                                'cover_image_url': rb.cover_image_url,
                                'reason': rec['reason'],
                                'score': rec['score'],
                                'categories': [c.name for c in rb.categories.all()],
                            })
                except Exception as e:
                    logger.warning(f"Recommendation enrichment failed: {e}")

            result['recommendations'] = recommendations

            return Response(result)

        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return Response(
                {'error': f'Failed to process question: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatsView(APIView):
    """GET /api/stats/ - Get database statistics."""

    def get(self, request):
        return Response({
            'total_books': Book.objects.count(),
            'processed_books': Book.objects.filter(is_processed=True).count(),
            'total_authors': Author.objects.count(),
            'total_categories': Category.objects.count(),
        })
