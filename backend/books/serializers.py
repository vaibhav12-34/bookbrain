"""
BookBrain Serializers for REST API.
"""

from rest_framework import serializers
from .models import Book, Author, Category, BookChunk


class AuthorSerializer(serializers.ModelSerializer):
    book_count = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'birth_year', 'photo_url', 'book_count']

    def get_book_count(self, obj):
        return obj.books.count()


class CategorySerializer(serializers.ModelSerializer):
    book_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'book_count']

    def get_book_count(self, obj):
        return obj.books.count()


class BookListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    authors = serializers.StringRelatedField(many=True, read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'isbn', 'authors', 'categories',
            'cover_image_url', 'average_rating', 'ratings_count',
            'publish_date', 'language', 'is_processed', 'created_at',
        ]


class BookDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer with AI insights."""
    authors = AuthorSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'isbn', 'isbn13', 'description',
            'publish_date', 'publisher', 'page_count', 'language',
            'cover_image_url', 'preview_link', 'info_link',
            'average_rating', 'ratings_count',
            'authors', 'categories',
            'ai_summary', 'ai_themes', 'ai_sentiment',
            'ai_reading_level', 'ai_key_topics',
            'is_processed', 'created_at', 'updated_at',
        ]


class BookUploadSerializer(serializers.Serializer):
    """For uploading/searching books by ISBN or title."""
    query = serializers.CharField(
        max_length=500,
        help_text="ISBN or book title to search and add"
    )
    search_type = serializers.ChoiceField(
        choices=['isbn', 'title'],
        default='title',
        help_text="Type of search: 'isbn' or 'title'"
    )


class BulkScrapeSerializer(serializers.Serializer):
    """For triggering bulk scraping."""
    topic = serializers.CharField(
        max_length=200,
        help_text="Topic/category to scrape books for"
    )
    max_results = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        help_text="Maximum number of books to scrape"
    )


class QuestionSerializer(serializers.Serializer):
    """For RAG question-answering."""
    question = serializers.CharField(
        max_length=1000,
        help_text="Question to ask about the books"
    )
    book_id = serializers.IntegerField(
        required=False,
        help_text="Optional: limit question to a specific book"
    )


class AnswerSerializer(serializers.Serializer):
    """Response from RAG query."""
    question = serializers.CharField()
    answer = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField())
    confidence = serializers.FloatField()
