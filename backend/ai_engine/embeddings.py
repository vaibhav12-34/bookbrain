"""
Embedding Engine - Generates and manages text embeddings using sentence-transformers.
Uses ChromaDB for persistent vector storage.
"""

import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy-load heavy imports
_model = None
_chroma_client = None
_collection = None


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully.")
    return _model


def _get_collection():
    """Lazy-load ChromaDB client and collection."""
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        from django.conf import settings

        persist_dir = str(settings.CHROMA_PERSIST_DIR)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        _collection = _chroma_client.get_or_create_collection(
            name="book_chunks",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection loaded. {_collection.count()} documents.")
    return _collection


def generate_embedding(text):
    """Generate embedding for a single text."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings(texts):
    """Generate embeddings for multiple texts."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks by words."""
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        start = end - overlap

    return chunks


def store_book_embeddings(book):
    """
    Chunk book content and store embeddings in ChromaDB.
    Returns the number of chunks created.
    """
    from books.models import BookChunk

    # Build the text to embed
    parts = []
    if book.title:
        parts.append(f"Title: {book.title}")
    if book.authors.exists():
        authors = ", ".join(a.name for a in book.authors.all())
        parts.append(f"Authors: {authors}")
    if book.description:
        parts.append(f"Description: {book.description}")
    if book.ai_summary:
        parts.append(f"Summary: {book.ai_summary}")
    if book.ai_themes:
        parts.append(f"Themes: {', '.join(book.ai_themes)}")

    full_text = "\n\n".join(parts)
    if not full_text.strip():
        return 0

    # Chunk the text
    chunks = chunk_text(full_text)
    if not chunks:
        return 0

    # Generate embeddings
    embeddings = generate_embeddings(chunks)

    # Store in ChromaDB and database
    collection = _get_collection()

    # Remove old chunks for this book
    old_chunks = BookChunk.objects.filter(book=book)
    old_ids = [c.embedding_id for c in old_chunks if c.embedding_id]
    if old_ids:
        try:
            collection.delete(ids=old_ids)
        except Exception:
            pass
    old_chunks.delete()

    # Store new chunks
    chunk_ids = []
    chunk_documents = []
    chunk_embeddings = []
    chunk_metadatas = []

    for idx, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"book_{book.id}_chunk_{idx}"
        chunk_ids.append(chunk_id)
        chunk_documents.append(chunk_text_content)
        chunk_embeddings.append(embedding)
        chunk_metadatas.append({
            'book_id': book.id,
            'book_title': book.title,
            'chunk_index': idx,
        })

        # Store in Django DB
        BookChunk.objects.create(
            book=book,
            content=chunk_text_content,
            chunk_index=idx,
            embedding_id=chunk_id,
        )

    # Batch store in ChromaDB
    collection.add(
        ids=chunk_ids,
        documents=chunk_documents,
        embeddings=chunk_embeddings,
        metadatas=chunk_metadatas,
    )

    logger.info(f"Stored {len(chunks)} chunks for '{book.title}'")
    return len(chunks)


def query_similar(query_text, n_results=5, book_id=None):
    """
    Query ChromaDB for similar chunks.
    Returns list of dicts with chunk content, book info, and distance.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    query_embedding = generate_embedding(query_text)

    where_filter = None
    if book_id:
        where_filter = {"book_id": book_id}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            where=where_filter,
            include=['documents', 'metadatas', 'distances'],
        )
    except Exception as e:
        logger.error(f"ChromaDB query error: {e}")
        return []

    chunks = []
    if results and results['documents']:
        for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            chunks.append({
                'content': doc,
                'book_id': meta.get('book_id'),
                'book_title': meta.get('book_title', ''),
                'chunk_index': meta.get('chunk_index', 0),
                'similarity': 1 - dist,  # cosine distance to similarity
            })

    return chunks
