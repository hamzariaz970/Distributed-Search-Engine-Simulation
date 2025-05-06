import os
import json
import requests
from pathlib import Path

# ---- DFS & Chunker imports ----
import sys
# so we can import dfs modules by path
sys.path.append(str(Path(__file__).resolve().parents[1] / "dfs"))
from dfs.client.upload import upload_file
from dfs.core.chunker import reconstruct_file

# ---- Search Engine imports ----
from search_engine.indexer import index_pdf
from search_engine.search import load_index, calculate_cosine_similarity, character_level_match

# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parents[0]
DOWNLOAD_DIR = BASE_DIR / "downloaded_files"
DOWNLOAD_DIR.mkdir(exist_ok=True)

def index_and_upload_pdf(pdf_path):
    print(f"[INFO] Indexing and uploading: {pdf_path}")
    index_pdf(pdf_path)
    upload_file(pdf_path)

def search_query(query):
    """
    Returns a list of (basename, metadata_dict) for matched documents.
    """
    corpus, docs = load_index()
    if corpus is None:
        return []

    # compute match scores
    scores = []
    for doc in corpus:
        # exact or partial substring match
        scores.append(character_level_match(query, doc))

    results = []
    for i, score in enumerate(scores):
        if score == 1.0:
            w = 1.0
        else:
            cos = calculate_cosine_similarity(query, corpus)[i]
            w = 0.8 * cos + 0.2 * score if score > 0 else cos
        title = docs[i]["title"]
        author = docs[i]["author"]
        path = docs[i]["relative_path"]
        results.append((w, title, author, path))

    results.sort(key=lambda x: x[0], reverse=True)

    matched = []
    print("\nTop results:")
    for idx, (w, title, author, relpath) in enumerate(results, start=1):
        print(f"{idx}. {title}\n   Authors: {author}\n   Score: {w:.3f}\n   Path: {relpath}")
        # load metadata for download
        basename = os.path.basename(relpath)                # e.g. sample1.pdf
        md_file = BASE_DIR / "dfs" / "metadata" / f"{basename}.json"
        if md_file.exists():
            md = json.loads(md_file.read_text())
            matched.append((basename, md))
    return matched

def download_submenu(matched):
    if not matched:
        print("[INFO] No downloadable results.")
        return
    print("\nEnter the number to download, or just press Enter to go back:")
    choice = input("> ").strip()
    if not choice.isdigit():
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(matched):
        print("[ERROR] Invalid selection.")
        return

    basename, metadata = matched[idx]
    print(f"[INFO] Downloading {basename} from DFS...")
    # download chunks
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
    # reconstruct
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
