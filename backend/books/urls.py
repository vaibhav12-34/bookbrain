"""
BookBrain API URL routing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'books', views.BookViewSet, basename='book')

urlpatterns = [
    # Explicit paths MUST come before the router to avoid conflicts with books/<pk>/
    path('books/upload/', views.BookUploadView.as_view(), name='book-upload'),
    path('books/scrape/', views.BulkScrapeView.as_view(), name='book-scrape'),
    path('books/ask/', views.AskQuestionView.as_view(), name='book-ask'),
    path('authors/', views.AuthorListView.as_view(), name='author-list'),
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('stats/', views.StatsView.as_view(), name='stats'),
    # Router-generated URLs (includes books/ and books/<pk>/)
    path('', include(router.urls)),
]
