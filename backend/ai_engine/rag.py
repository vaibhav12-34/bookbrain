"""
RAG (Retrieval-Augmented Generation) Engine.
Retrieves relevant book chunks and generates answers to questions.
"""

import logging
from .embeddings import query_similar

logger = logging.getLogger(__name__)


def _get_gemini_model():
    """Try to get Gemini model if API key is available."""
    try:
        from django.conf import settings
        api_key = settings.GEMINI_API_KEY
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logger.debug(f"Gemini not available: {e}")
    return None


def ask_question(question, book_id=None):
    """
    Answer a question about books using RAG.
    
    Returns dict with:
        - answer: The generated answer
        - sources: List of source chunks used
        - confidence: Confidence score (0-1)
    """
    # Retrieve relevant chunks
    chunks = query_similar(question, n_results=5, book_id=book_id)

    if not chunks:
        return {
            'question': question,
            'answer': "I don't have enough information in the book database to answer this question. "
                      "Try adding more books or rephrasing your question.",
            'sources': [],
            'confidence': 0.0,
        }

    # Build context from retrieved chunks
    context_parts = []
    sources = []
    for chunk in chunks:
        context_parts.append(chunk['content'])
        sources.append({
            'book_id': chunk['book_id'],
            'book_title': chunk['book_title'],
            'similarity': round(chunk['similarity'], 3),
        })

    context = "\n\n---\n\n".join(context_parts)
    avg_similarity = sum(c['similarity'] for c in chunks) / len(chunks)

    # Try Gemini for answer generation
    model = _get_gemini_model()
    if model:
        try:
            prompt = (
                f"You are a helpful book expert. Based on the following book information, "
                f"answer the user's question accurately and concisely.\n\n"
                f"Book Information:\n{context}\n\n"
                f"Question: {question}\n\n"
                f"Answer based only on the provided book information. If the information "
                f"doesn't fully answer the question, say so."
            )
            response = model.generate_content(prompt)
            return {
                'question': question,
                'answer': response.text.strip(),
                'sources': _deduplicate_sources(sources),
                'confidence': round(min(avg_similarity + 0.1, 1.0), 3),
            }
        except Exception as e:
            logger.warning(f"Gemini RAG failed: {e}")

    # Local answer generation (extractive)
    answer = _generate_local_answer(question, chunks, context)
    return {
        'question': question,
        'answer': answer,
        'sources': _deduplicate_sources(sources),
        'confidence': round(avg_similarity, 3),
    }


def _generate_local_answer(question, chunks, context):
    """Generate an answer locally using extractive approach."""
    question_lower = question.lower()

    # Check what type of question
    if any(q in question_lower for q in ['what is', 'what are', 'describe', 'tell me about', 'explain']):
        # Informational question - return most relevant content
        best_chunk = chunks[0]
        answer = (
            f"Based on the books in the database, here's what I found:\n\n"
            f"From \"{best_chunk['book_title']}\":\n"
            f"{best_chunk['content'][:800]}"
        )
        if len(chunks) > 1:
            answer += f"\n\nAlso related, from \"{chunks[1]['book_title']}\":\n"
            answer += chunks[1]['content'][:400]
        return answer

    elif any(q in question_lower for q in ['who', 'author', 'wrote', 'written by']):
        # Author question
        from books.models import Book
        best_chunk = chunks[0]
        try:
            book = Book.objects.get(id=best_chunk['book_id'])
            authors = ", ".join(a.name for a in book.authors.all())
            return (
                f"\"{book.title}\" was written by {authors}. "
                f"\n\nDescription: {book.description[:500]}"
            )
        except Book.DoesNotExist:
            pass

    elif any(q in question_lower for q in ['recommend', 'suggest', 'similar', 'like']):
        # Recommendation question
        book_titles = list(set(c['book_title'] for c in chunks))
        answer = "Based on your interest, you might enjoy these books:\n\n"
        for i, title in enumerate(book_titles[:5], 1):
            answer += f"{i}. {title}\n"
        return answer

    elif any(q in question_lower for q in ['how many', 'count', 'number']):
        # Counting question
        from books.models import Book
        total = Book.objects.count()
        return f"There are currently {total} books in the database."

    # Default: return relevant content
    answer = "Here's the most relevant information I found:\n\n"
    seen_books = set()
    for chunk in chunks[:3]:
        if chunk['book_title'] not in seen_books:
            seen_books.add(chunk['book_title'])
            answer += f"**{chunk['book_title']}**: {chunk['content'][:400]}\n\n"
    return answer


def _deduplicate_sources(sources):
    """Remove duplicate book sources, keeping highest similarity."""
    seen = {}
    for source in sources:
        book_id = source['book_id']
        if book_id not in seen or source['similarity'] > seen[book_id]['similarity']:
            seen[book_id] = source
    return list(seen.values())
