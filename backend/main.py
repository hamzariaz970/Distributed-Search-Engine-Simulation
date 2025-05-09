import os
import json
import pickle
import requests
import numpy as np
from pathlib import Path

# ---- DFS & Chunker imports ----
import sys
# so we can import dfs modules by path
sys.path.append(str(Path(__file__).resolve().parents[1] / "dfs"))
from dfs.client.upload import upload_file
from dfs.core.chunker import reconstruct_file
from dfs.client.delete import delete_file

# ---- Search Engine imports ----
from search_engine.indexer import index_pdf
from search_engine.search import load_index, calculate_cosine_similarity, character_level_match

# ---- Semantic Model imports ----
from sentence_transformers import SentenceTransformer

# ---- Paths & Constants ----
BASE_DIR      = Path(__file__).resolve().parents[0]
DOWNLOAD_DIR  = BASE_DIR / "downloaded_files"
DOWNLOAD_DIR.mkdir(exist_ok=True)

INDEX_DIR     = BASE_DIR / "search_engine" / "index"
EMB_FILE      = INDEX_DIR / "corpus_embeddings.pkl"   # your SBERT embeddings
SCORE_THRESHOLD = 0.2                                  # minimum combined score to keep

# load SBERT model once
SBERT_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def index_and_upload_pdf(pdf_path):
    print(f"[INFO] Indexing and uploading: {pdf_path}")
    index_pdf(pdf_path)
    upload_file(pdf_path)


def search_query(query, top_k=3):
    """
    Hybrid semantic + lexical search:
      1. Lexical: BM25/Tf-IDF cosine + character‐level boosts
      2. Semantic: SBERT cosine
      3. Combine 50/50, threshold, and return top_k hits.
    Returns: list of (basename, metadata_dict)
    """
    # 1) load lexical index
    corpus, docs = load_index()
    if corpus is None:
        return []

    # 2) load semantic embeddings
    if not EMB_FILE.exists():
        raise FileNotFoundError(f"Missing embeddings file: {EMB_FILE}")
    corpus_emb = pickle.loads(EMB_FILE.read_bytes())          # shape (N, d)

    # 3) encode query semantically
    q_emb = SBERT_MODEL.encode(query, convert_to_numpy=True)  # shape (d,)

    # normalize both for cosine
    corpus_norm = corpus_emb / np.linalg.norm(corpus_emb, axis=1, keepdims=True)
    q_norm      = q_emb      / np.linalg.norm(q_emb)
    sem_scores  = (corpus_norm @ q_norm).tolist()            # length N

    # 4) lexical scores
    char_scores = [character_level_match(query, doc) for doc in corpus]
    lex_cos     = calculate_cosine_similarity(query, corpus)

    # 5) combine and threshold
    hits = []
    for i, (ch, lx, sm) in enumerate(zip(char_scores, lex_cos, sem_scores)):
        # boost exact/partial substring
        if ch == 1.0:
            lexical_score = 1.0
        elif ch > 0:
            lexical_score = 0.8 * lx + 0.2 * ch
        else:
            lexical_score = lx

        # final hybrid score (50% lexical, 50% semantic)
        score = 0.5 * lexical_score + 0.5 * sm
        if score < SCORE_THRESHOLD:
            continue

        entry   = docs[i]
        basename= entry["file_name"]
        relpath = entry["relative_path"]
        # load DFS metadata for download/view
        md_file = BASE_DIR / "dfs" / "metadata" / f"{basename}.json"
        md      = json.loads(md_file.read_text()) if md_file.exists() else {}
        hits.append((score, basename, entry["title"], entry["author"], md))

    # 6) sort, take top_k
    hits.sort(key=lambda x: x[0], reverse=True)
    hits = hits[:top_k]

    # 7) print for CLI and return just (basename, metadata)
    if hits:
        print(f"\nTop {len(hits)} results (score ≥ {SCORE_THRESHOLD:.2f}):")
        for idx, (sc, bn, ti, au, _) in enumerate(hits, start=1):
            print(f"{idx}. {ti}\n   Authors: {au}\n   Score: {sc:.3f}\n   Path: {bn}")
    else:
        print(f"[INFO] No documents scored ≥ {SCORE_THRESHOLD:.2f}")

    return [(bn, md) for _, bn, _, _, md in hits]


def download_submenu(matched):
    if not matched:
        print("[INFO] No downloadable results.")
        return
    print("\nEnter the number to download, or press Enter to go back:")
    choice = input("> ").strip()
    if not choice.isdigit():
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(matched):
        print("[ERROR] Invalid selection.")
        return

    basename, metadata = matched[idx]
    print(f"[INFO] Downloading {basename} from DFS...")
    chunk_dir = BASE_DIR / "chunks"
    chunk_dir.mkdir(exist_ok=True)
    for chunk_id, node_url in metadata.items():
        url = f"{node_url}/chunk/{chunk_id}"
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            (chunk_dir / chunk_id).write_bytes(r.content)
            print(f"  ▷ got {chunk_id}")
        except Exception as e:
            print(f"  ⚠️ failed {chunk_id}: {e}")
            return

    out_path = DOWNLOAD_DIR / basename
    reconstruct_file(list(metadata.keys()), str(out_path), input_dir=str(chunk_dir))
    print(f"[SUCCESS] Reconstructed to {out_path}")


def main():
    while True:
        print("\nMain Menu:")
        print("1. Index & upload a PDF")
        print("2. Search & download")
        print("3. Exit")
        choice = input("> ").strip()
        if choice == "1":
            pdf = input("Path to PDF: ").strip()
            index_and_upload_pdf(pdf)
        elif choice == "2":
            q = input("Search query: ").strip()
            matched = search_query(q)
            download_submenu(matched)
        elif choice == "3":
            break
        else:
            print("[ERROR] Invalid option. Try again.")


if __name__ == "__main__":
    main()
