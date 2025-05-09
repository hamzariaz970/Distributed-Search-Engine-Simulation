import os
import json
import fitz  # PyMuPDF
import requests
import pickle
from pathlib import Path
from rank_bm25 import BM25Okapi
from nltk.tokenize import word_tokenize
import nltk
import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import platform
from dfs.client.upload import upload_file
from sentence_transformers import SentenceTransformer

# ---------------------- Ensure punkt tokenizer is available ----------------------
# (existing punkt setup unchanged)
try:
    nltk.data.find('tokenizers/punkt')
    print("[INFO] punkt tokenizer is already available.")
except LookupError:
    print("[INFO] punkt tokenizer not found, downloading...")
    if platform.system() == 'Windows':
        nltk.data.path.append(os.path.join(os.environ['APPDATA'], 'nltk_data'))
    nltk.download('punkt')

# ---------------------- Directory Setup ----------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # DFS_PDC_Project root
INDEX_DIR = BASE_DIR / "search_engine" / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = INDEX_DIR / "bm25_index.json"
DOCS_FILE = INDEX_DIR / "docs.json"
TFIDF_CACHE_FILE = INDEX_DIR / "cached_tfidf_matrix.pkl"

# --- New: Semantic Embedding Cache & Model ---
EMBEDDING_CACHE = INDEX_DIR / "corpus_embeddings.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------- GROBID API for Metadata ----------------------
# (existing extract_title_author_grobid unchanged)

def extract_title_author_grobid(pdf_path):
    url = "http://localhost:8070/api/processHeaderDocument"
    try:
        with open(pdf_path, 'rb') as file:
            response = requests.post(url, files={'input': file}, headers={"Accept": "application/xml"}, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] GROBID response {response.status_code}: {response.text}")
            return None, None
        xml_root = ET.fromstring(response.content)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        title_elem = xml_root.find('.//tei:titleStmt/tei:title', ns)
        title = title_elem.text.strip() if title_elem is not None else 'Unknown Title'
        authors = []
        for pers in xml_root.findall('.//tei:author/tei:persName', ns):
            name = []
            forename = pers.find('tei:forename', ns)
            surname = pers.find('tei:surname', ns)
            if forename is not None:
                name.append(forename.text)
            if surname is not None:
                name.append(surname.text)
            full_name = ' '.join(name).strip()
            if full_name:
                authors.append(full_name)
        author_str = ', '.join(authors) if authors else 'Unknown Author'
        return title, author_str
    except Exception as e:
        print(f"[ERROR] Failed to extract metadata using GROBID: {e}")
        return None, None

# ---------------------- PyMuPDF Text Extraction ----------------------
# (existing extract_pdf_text unchanged)

def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        return "\n".join(page.get_text("text") for page in doc)
    except Exception as e:
        print(f"[ERROR] Failed to extract PDF text: {e}")
        return None

# ---------------------- Index Handling ----------------------
# (existing save_index, load_index, index_pdf unchanged except save_index extended below)

def save_index(corpus, doc_info, tfidf_matrix=None):
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump({"corpus": corpus}, f, indent=2)
        with open(DOCS_FILE, 'w', encoding='utf-8') as f:
            json.dump(doc_info, f, indent=2)
        if tfidf_matrix is not None:
            with open(TFIDF_CACHE_FILE, 'wb') as f:
                pickle.dump(tfidf_matrix, f)
        print(f"[SUCCESS] Index saved at: {INDEX_DIR}")
        # --- Build & cache semantic embeddings ---
        try:
            model = SentenceTransformer(MODEL_NAME)
            embeddings = model.encode(corpus, show_progress_bar=True, convert_to_numpy=True)
            with open(EMBEDDING_CACHE, 'wb') as ef:
                pickle.dump(embeddings, ef)
            print(f"[SUCCESS] Semantic embeddings saved at: {EMBEDDING_CACHE}")
        except Exception as e:
            print(f"[WARN] Failed to build embeddings: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to save index: {e}")


def load_index():
    if not INDEX_FILE.exists() or not DOCS_FILE.exists():
        return None, None, None, None
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            corpus = json.load(f)["corpus"]
        with open(DOCS_FILE, 'r', encoding='utf-8') as f:
            doc_info = json.load(f)
        tfidf_matrix = None
        if TFIDF_CACHE_FILE.exists():
            with open(TFIDF_CACHE_FILE, 'rb') as f:
                tfidf_matrix = pickle.load(f)
        tokenized = [word_tokenize(doc.lower()) for doc in corpus]
        bm25 = BM25Okapi(tokenized, k1=1.5, b=0.75)
        return bm25, corpus, doc_info, tfidf_matrix
    except Exception as e:
        print(f"[ERROR] Failed to load index: {e}")
        return None, None, None, None

# ---------------------- Indexing Function ----------------------
# (existing index_pdf unchanged)

def index_pdf(pdf_path):
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        return
    print(f"[INFO] Indexing file: {pdf_path.name}")
    title, author = extract_title_author_grobid(pdf_path)
    if not title or not author:
        print("[WARN] Skipping file due to metadata extraction failure.")
        return
    full_text = extract_pdf_text(pdf_path)
    if not full_text:
        print("[WARN] Skipping file due to full text extraction failure.")
        return
    bm25, corpus, doc_info, tfidf_matrix = load_index()
    if corpus is None:
        corpus, doc_info = [], []
        tfidf_matrix = None
    corpus.append(full_text)
    doc_info.append({
        "title": title,
        "author": author,
        "file_name": pdf_path.name,
        "relative_path": str(pdf_path.relative_to(BASE_DIR))
    })
    tokenized_corpus = [word_tokenize(doc.lower()) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    save_index(corpus, doc_info, tfidf_matrix)


def upload_indexed_file_to_dfs(pdf_path: Path):
    upload_file(str(pdf_path))

# ---------------------- CLI ----------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Index a PDF file for search.")
    parser.add_argument("pdf_file", type=str, help="Path to the PDF file to index")
    args = parser.parse_args()
    try:
        index_pdf(args.pdf_file)
        upload_indexed_file_to_dfs(Path(args.pdf_file))
    except Exception as e:
        print(f"[FATAL] Unexpected error during indexing: {e}")
