"""
BookBrain Models - Book, Author, Category and BookChunk models.
"""

from django.db import models
from django.utils.text import slugify


class Author(models.Model):
    """Represents a book author."""
    name = models.CharField(max_length=300)
    bio = models.TextField(blank=True, default='')
    birth_year = models.IntegerField(null=True, blank=True)
    photo_url = models.URLField(max_length=500, blank=True, default='')
    open_library_key = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    """Book category/genre."""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Book(models.Model):
    """Core book model with metadata and AI-generated fields."""
    # Basic metadata
    title = models.CharField(max_length=500)
    isbn = models.CharField(max_length=20, blank=True, default='', db_index=True)
    isbn13 = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True, default='')
    publish_date = models.CharField(max_length=50, blank=True, default='')
    publisher = models.CharField(max_length=300, blank=True, default='')
    page_count = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=10, default='en')

    # Cover & links
    cover_image_url = models.URLField(max_length=500, blank=True, default='')
    preview_link = models.URLField(max_length=500, blank=True, default='')
    info_link = models.URLField(max_length=500, blank=True, default='')

    # Ratings
    average_rating = models.FloatField(null=True, blank=True)
    ratings_count = models.IntegerField(null=True, blank=True)

    # Relations
    authors = models.ManyToManyField(Author, related_name='books', blank=True)
    categories = models.ManyToManyField(Category, related_name='books', blank=True)

    # Source tracking
    open_library_key = models.CharField(max_length=100, blank=True, default='')
    google_books_id = models.CharField(max_length=50, blank=True, default='')

    # AI-generated fields
    ai_summary = models.TextField(blank=True, default='')
    ai_themes = models.JSONField(default=list, blank=True)
    ai_sentiment = models.CharField(max_length=50, blank=True, default='')
    ai_reading_level = models.CharField(max_length=50, blank=True, default='')
    ai_key_topics = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Processing status
    is_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class BookChunk(models.Model):
    """Chunked text content for RAG retrieval."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    embedding_id = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ['book', 'chunk_index']
        unique_together = ['book', 'chunk_index']

    def __str__(self):
        return f"{self.book.title} - Chunk {self.chunk_index}"
