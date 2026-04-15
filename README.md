# 📚 BookBrain — AI-Powered Book Intelligence Platform

A full-stack web application that collects book data, manages it with Django REST Framework, and provides AI-driven querying, summaries, and recommendations — all running locally without external API keys.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-5.x-green?logo=django)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **📖 Book Scraping** — Auto-fetches book data from Open Library & Google Books APIs
- **🧠 AI Insights** — Local AI generates summaries, themes, sentiment, and reading level
- **💬 RAG Q&A** — Ask natural language questions about your book library
- **✨ Recommendations** — AI-powered "similar books" using embedding similarity
- **🎨 Premium UI** — Dark glassmorphism theme with responsive SPA frontend
- **🔒 No API Keys Required** — All AI runs locally with sentence-transformers

## 🖼️ Screenshots

### Library View
Book cards with cover art, ratings, and category tags in a responsive grid.

### Ask AI — Structured Q&A
Question input with quick-action chips, AI answers with matched book cards showing summaries, genres, themes, and personalized recommendations.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/bookbrain.git
cd bookbrain

# Install dependencies
cd backend
pip install -r requirements.txt

# Set up database
python manage.py migrate

# Start the backend server
python manage.py runserver 0.0.0.0:8000
```

In a **second terminal**:

```bash
# Start the frontend server
cd frontend
python -m http.server 3000
```

Open **http://localhost:3000** in your browser.

### Add Your First Books

1. Click **"Discover"** in the nav bar
2. Enter a topic like "Hindi Literature" or "Science Fiction"
3. Click **"Discover Books"** — the scraper will fetch and AI-process them automatically

## 🏗️ Architecture

```
bookbrain/
├── backend/
│   ├── bookbrain/        # Django project settings
│   ├── books/            # Models, Views, Serializers, URLs
│   ├── scraper/          # Open Library + Google Books API clients
│   ├── ai_engine/        # Embeddings, RAG, Insights, Recommendations
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── index.html        # SPA shell
│   ├── css/styles.css    # Premium dark theme
│   └── js/app.js         # SPA router + API integration
├── .env                  # Environment config (optional Gemini key)
└── .gitignore
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/books/` | List all books (paginated, searchable) |
| GET | `/api/books/<id>/` | Full book detail with AI insights |
| GET | `/api/books/<id>/recommendations/` | AI-powered recommendations |
| POST | `/api/books/upload/` | Add book by title or ISBN |
| POST | `/api/books/scrape/` | Bulk scrape books by topic |
| POST | `/api/books/ask/` | RAG question answering |
| GET | `/api/stats/` | Database statistics |

## 🤖 AI Stack (Local, No API Key)

| Component | Technology |
|-----------|-----------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | ChromaDB (persistent local) |
| RAG Q&A | Embedding similarity + extractive answering |
| Summaries | Sentence scoring + extraction |
| Themes | Keyword frequency + theme mapping |
| Sentiment | Rule-based tone classification |
| Recommendations | Embedding cosine similarity + metadata overlap |

> **Optional**: Add a `GEMINI_API_KEY` to `.env` for enhanced AI responses using Google Gemini.

## 🛠️ Tech Stack

- **Backend**: Django 5.x, Django REST Framework
- **AI/ML**: sentence-transformers, ChromaDB
- **Frontend**: Vanilla HTML/CSS/JS (SPA)
- **Data Sources**: Open Library API, Google Books API
- **Database**: SQLite (development)

## 📄 License

MIT License — feel free to use and modify.
