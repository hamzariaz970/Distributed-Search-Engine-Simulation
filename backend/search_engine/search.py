import os
import json
import nltk
import numpy as np
from pathlib import Path
from fuzzywuzzy import fuzz  # For fuzzy matching
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

# ---------------------- Ensure punkt tokenizer is available ----------------------
import os
import nltk
import platform

# Check if punkt is available
try:
    nltk.data.find('tokenizers/punkt')
    print("[INFO] punkt tokenizer is already available.")
except LookupError:
    print("[INFO] punkt tokenizer not found, downloading...")
    # If you're on Windows, you might need to set an explicit path to nltk data
    if platform.system() == 'Windows':
        nltk.data.path.append(os.path.join(os.environ['APPDATA'], 'nltk_data'))
    nltk.download('punkt')

# ---------------------- Directory Setup ----------------------

BASE_DIR = Path(__file__).resolve().parents[1]
INDEX_DIR = BASE_DIR / "search_engine" / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = INDEX_DIR / "bm25_index.json"
DOCS_FILE = INDEX_DIR / "docs.json"
SIMILARITY_FILE = INDEX_DIR / "similarity_cache.npy"  # Cache for cosine similarities

# ---------------------- Load Index ----------------------

def load_index():
    """
    Loads the BM25 index and document metadata.
    """
    if not INDEX_FILE.exists() or not DOCS_FILE.exists():
        print("[ERROR] Index or documents not found.")
        return None, None

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        corpus = json.load(f)["corpus"]

    with open(DOCS_FILE, 'r', encoding='utf-8') as f:
        doc_info = json.load(f)

    return corpus, doc_info

# ---------------------- Cosine Similarity Cache ----------------------

def load_cosine_similarity():
    """
    Loads cached cosine similarities from disk.
    """
    if SIMILARITY_FILE.exists():
        return np.load(SIMILARITY_FILE)
    else:
        return None

def save_cosine_similarity(cosine_similarities):
    """
    Saves the computed cosine similarities to disk for future use.
    """
    np.save(SIMILARITY_FILE, cosine_similarities)

# ---------------------- Cosine Similarity Calculation ----------------------

def calculate_cosine_similarity(query, documents):
    """
    Calculate the cosine similarity between the query and the list of documents.
    """
    vectorizer = TfidfVectorizer()

    # Fit and transform the documents and query
    tfidf_matrix = vectorizer.fit_transform(documents + [query])

    # Calculate the cosine similarity between the query and all documents
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

    return cosine_similarities

# ---------------------- Character Level Matching ----------------------

def character_level_match(query, document):
    """
    Calculate the character-level match between query and document.
    The higher the match, the higher the score.
    """
    query = query.lower()
    document = document.lower()

    # If the query is found in the document, calculate the match length
    match_score = 0
    if query in document:
        match_score = 1.0  # Exact match

    # If only part of the query is found, we want a partial match score
    elif query[:3] in document:
        match_score = 0.5  # Partial match score

    return match_score

def fuzzy_character_level_match(query, document):
    """
    Use fuzzy matching to compare the query with the document.
    """
    return fuzz.partial_ratio(query.lower(), document.lower()) / 100  # Normalize to [0, 1]

# ---------------------- Main Search Function ----------------------

def search_query(query):
    """
    Perform a search for the query and return the ranked documents.
    """
    corpus, doc_info = load_index()
    if not corpus or not doc_info:
        print("[ERROR] Index not loaded correctly.")
        return

    # Step 1: Searching for character-level matches using fuzzy matching
    print("[INFO] Searching for character-level matches...")
    char_match_scores = []
    for doc in corpus:
        char_match_scores.append(character_level_match(query, doc))  # Exact substring matching

    # Step 2: If we have character-level matches, prioritize them and skip cosine similarity
    results = []
    for idx, (doc, char_score) in enumerate(zip(corpus, char_match_scores)):
        if char_score == 1.0:  # Exact match, give full score
            weighted_score = 1.0  # Full score for perfect match
        elif char_score > 0:
            # If a substring match was found, combine the score with cosine similarity
            cosine_similarities = calculate_cosine_similarity(query, corpus)
            weighted_score = 0.8 * cosine_similarities[idx] + 0.2 * char_score  # Weighted combination
        else:
            # If no substring match, fall back to cosine similarity
            cosine_similarities = calculate_cosine_similarity(query, corpus)
            weighted_score = cosine_similarities[idx]  # Pure cosine similarity

        results.append((doc_info[idx]['title'], doc_info[idx]['author'], weighted_score, doc_info[idx]['relative_path']))

    # Sort results by the weighted score in descending order
    results.sort(key=lambda x: x[2], reverse=True)

    # Print results
    for idx, (title, author, score, path) in enumerate(results):
        print(f"\nDocument {idx + 1}: {title}")
        print(f"Authors: {author}")
        print(f"Relevance score: {score:.3f}")
        print(f"Path: {path}")
        print("-" * 80)

# ---------------------- CLI Entry Point ----------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search for a query in the indexed documents.")
    parser.add_argument("query", type=str, help="The query to search for.")
    args = parser.parse_args()

    try:
        search_query(args.query)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
