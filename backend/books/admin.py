"""BookBrain Admin Configuration."""

from django.contrib import admin
from .models import Book, Author, Category, BookChunk


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'birth_year', 'created_at']
    search_fields = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'isbn', 'publish_date', 'average_rating', 'is_processed', 'created_at']
    list_filter = ['is_processed', 'language', 'categories']
    search_fields = ['title', 'isbn', 'description']
    filter_horizontal = ['authors', 'categories']
    readonly_fields = ['ai_summary', 'ai_themes', 'ai_sentiment', 'ai_reading_level', 'ai_key_topics']


@admin.register(BookChunk)
class BookChunkAdmin(admin.ModelAdmin):
    list_display = ['book', 'chunk_index', 'embedding_id']
    list_filter = ['book']
