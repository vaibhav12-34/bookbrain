"""
AI Insights Engine - Generates summaries, themes, sentiment analysis.
Uses local heuristics (no API key needed). Can upgrade to Gemini if key is provided.
"""

import re
import logging
from collections import Counter

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


def generate_summary(text, max_sentences=4):
    """Generate a summary of the book description."""
    if not text or len(text.strip()) < 50:
        return ''

    # Try Gemini first
    model = _get_gemini_model()
    if model:
        try:
            response = model.generate_content(
                f"Summarize this book description in 3-4 concise sentences:\n\n{text[:3000]}"
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini summary failed: {e}")

    # Local extractive summary
    return _extractive_summary(text, max_sentences)


def _extractive_summary(text, max_sentences=4):
    """Simple extractive summarization using sentence scoring."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= max_sentences:
        return text

    # Score sentences by position and word frequency
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = Counter(words)

    # Remove very common words
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was',
        'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'not', 'but', 'what', 'which',
        'who', 'how', 'when', 'where', 'than', 'then', 'also', 'its',
        'his', 'her', 'their', 'about', 'into', 'over', 'after', 'before',
        'each', 'every', 'all', 'some', 'any', 'most', 'other', 'more',
    }
    for sw in stop_words:
        word_freq.pop(sw, None)

    scored = []
    for idx, sentence in enumerate(sentences):
        sent_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
        if not sent_words:
            continue

        # Word frequency score
        freq_score = sum(word_freq.get(w, 0) for w in sent_words) / len(sent_words)

        # Position score (first and last sentences are important)
        pos_score = 1.0
        if idx == 0:
            pos_score = 2.0
        elif idx == len(sentences) - 1:
            pos_score = 1.5
        elif idx < 3:
            pos_score = 1.3

        # Length penalty for very short sentences
        length_score = min(len(sent_words) / 10, 1.0)

        total_score = freq_score * pos_score * length_score
        scored.append((total_score, idx, sentence))

    scored.sort(reverse=True)
    selected = sorted(scored[:max_sentences], key=lambda x: x[1])
    return ' '.join(s[2] for s in selected)


def extract_themes(text, max_themes=6):
    """Extract key themes/topics from book description."""
    if not text:
        return []

    # Try Gemini
    model = _get_gemini_model()
    if model:
        try:
            response = model.generate_content(
                f"Extract 3-6 key themes from this book description. "
                f"Return only the themes as a comma-separated list:\n\n{text[:2000]}"
            )
            themes = [t.strip() for t in response.text.split(',')]
            return [t for t in themes if t and len(t) < 50][:max_themes]
        except Exception as e:
            logger.warning(f"Gemini theme extraction failed: {e}")

    # Local theme extraction
    return _extract_themes_local(text, max_themes)


def _extract_themes_local(text, max_themes=6):
    """Extract themes using keyword frequency analysis."""
    # Common theme-related words and bigrams
    theme_keywords = {
        'love': 'Love & Romance', 'romance': 'Love & Romance',
        'war': 'War & Conflict', 'battle': 'War & Conflict', 'fight': 'War & Conflict',
        'death': 'Life & Death', 'life': 'Life & Death', 'mortal': 'Life & Death',
        'power': 'Power & Authority', 'king': 'Power & Authority', 'empire': 'Power & Authority',
        'family': 'Family', 'mother': 'Family', 'father': 'Family', 'child': 'Family',
        'freedom': 'Freedom & Justice', 'justice': 'Freedom & Justice', 'liberty': 'Freedom & Justice',
        'mystery': 'Mystery', 'detective': 'Mystery', 'crime': 'Mystery', 'murder': 'Mystery',
        'adventure': 'Adventure', 'journey': 'Adventure', 'quest': 'Adventure', 'travel': 'Adventure',
        'magic': 'Fantasy & Magic', 'wizard': 'Fantasy & Magic', 'dragon': 'Fantasy & Magic',
        'science': 'Science & Technology', 'technology': 'Science & Technology',
        'friendship': 'Friendship', 'friend': 'Friendship', 'companion': 'Friendship',
        'identity': 'Identity & Self', 'self': 'Identity & Self',
        'society': 'Society & Class', 'class': 'Society & Class', 'social': 'Society & Class',
        'nature': 'Nature & Environment', 'wilderness': 'Nature & Environment',
        'survival': 'Survival', 'survive': 'Survival',
        'betrayal': 'Betrayal & Trust', 'trust': 'Betrayal & Trust',
        'courage': 'Courage & Bravery', 'brave': 'Courage & Bravery', 'hero': 'Courage & Bravery',
        'revenge': 'Revenge', 'vengeance': 'Revenge',
        'faith': 'Faith & Religion', 'god': 'Faith & Religion', 'religion': 'Faith & Religion',
        'knowledge': 'Knowledge & Wisdom', 'wisdom': 'Knowledge & Wisdom',
        'isolation': 'Isolation & Loneliness', 'lonely': 'Isolation & Loneliness',
    }

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    theme_counts = Counter()

    for word in words:
        if word in theme_keywords:
            theme_counts[theme_keywords[word]] += 1

    if not theme_counts:
        # Fallback: extract most frequent meaningful words
        stop_words = {
            'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was',
            'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could',
            'should', 'not', 'but', 'about', 'into', 'their', 'also', 'book',
            'story', 'novel', 'author', 'one', 'new', 'first', 'two', 'can',
            'like', 'just', 'than', 'more', 'its', 'who', 'what', 'when',
            'where', 'how', 'which', 'there', 'these', 'those', 'them',
            'they', 'she', 'her', 'his', 'him', 'our', 'your', 'you',
        }
        meaningful = [w for w in words if w not in stop_words and len(w) > 4]
        common = Counter(meaningful).most_common(max_themes)
        return [word.title() for word, _ in common]

    return [theme for theme, _ in theme_counts.most_common(max_themes)]


def analyze_sentiment(text):
    """Analyze the sentiment/tone of the book description."""
    if not text:
        return 'Neutral'

    # Try Gemini
    model = _get_gemini_model()
    if model:
        try:
            response = model.generate_content(
                f"Classify the overall tone/sentiment of this book description in ONE word "
                f"(e.g. Dark, Uplifting, Mysterious, Romantic, Thrilling, Melancholic, Humorous, "
                f"Philosophical, Adventurous, Dramatic):\n\n{text[:1500]}"
            )
            return response.text.strip().split('\n')[0].strip('.').strip()
        except Exception as e:
            logger.warning(f"Gemini sentiment failed: {e}")

    # Local sentiment analysis
    return _analyze_sentiment_local(text)


def _analyze_sentiment_local(text):
    """Simple rule-based sentiment/tone classification."""
    text_lower = text.lower()

    sentiment_keywords = {
        'Dark': ['dark', 'death', 'fear', 'horror', 'sinister', 'evil', 'shadow', 'haunting',
                 'grim', 'bleak', 'despair', 'tragic'],
        'Uplifting': ['hope', 'inspire', 'triumph', 'overcome', 'courage', 'uplifting',
                      'beautiful', 'wonderful', 'heartwarming', 'joy'],
        'Mysterious': ['mystery', 'secret', 'hidden', 'enigma', 'puzzle', 'clue', 'detective',
                       'suspicious', 'investigate', 'unknown'],
        'Romantic': ['love', 'romance', 'passion', 'heart', 'desire', 'kiss', 'relationship',
                     'beautiful', 'tender'],
        'Thrilling': ['thrill', 'suspense', 'danger', 'chase', 'escape', 'tension',
                      'adrenaline', 'race', 'fast-paced', 'action'],
        'Philosophical': ['meaning', 'existence', 'philosophy', 'truth', 'morality',
                          'consciousness', 'human condition', 'purpose', 'question'],
        'Adventurous': ['adventure', 'journey', 'explore', 'quest', 'discover', 'voyage',
                        'expedition', 'wilderness', 'travel'],
        'Humorous': ['funny', 'humor', 'comedy', 'laugh', 'witty', 'satirical', 'hilarious',
                     'amusing', 'comic'],
    }

    scores = {}
    for sentiment, keywords in sentiment_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[sentiment] = score

    if scores:
        return max(scores, key=scores.get)
    return 'Neutral'


def estimate_reading_level(text, page_count=None):
    """Estimate the reading level of a book."""
    if not text:
        return 'Unknown'

    words = text.split()
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
    sentences = re.split(r'[.!?]+', text)
    avg_sent_len = len(words) / max(len(sentences), 1)

    # Simple heuristic based on word complexity and sentence length
    complexity = (avg_word_len * 2 + avg_sent_len) / 3

    if complexity < 4:
        return 'Easy Read'
    elif complexity < 6:
        return 'Intermediate'
    elif complexity < 8:
        return 'Advanced'
    else:
        return 'Academic'


def process_book_insights(book):
    """Generate all AI insights for a book and save to model."""
    text = book.description

    if not text:
        book.is_processed = True
        book.save()
        return

    # Generate insights
    book.ai_summary = generate_summary(text)
    book.ai_themes = extract_themes(text)
    book.ai_sentiment = analyze_sentiment(text)
    book.ai_reading_level = estimate_reading_level(text, book.page_count)

    # Extract key topics (simple noun phrases)
    book.ai_key_topics = _extract_key_topics(text)

    book.is_processed = True
    book.save()

    logger.info(f"Generated insights for '{book.title}'")


def _extract_key_topics(text, max_topics=8):
    """Extract key topics from text."""
    if not text:
        return []

    # Find capitalized phrases (likely proper nouns / topics)
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    proper_counts = Counter(proper_nouns)

    # Remove very common ones
    skip = {'The', 'This', 'That', 'And', 'But', 'For', 'With', 'From', 'Not', 'His', 'Her'}
    topics = [noun for noun, count in proper_counts.most_common(max_topics + len(skip))
              if noun not in skip and len(noun) > 2]

    return topics[:max_topics]
