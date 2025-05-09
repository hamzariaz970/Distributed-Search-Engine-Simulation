# backend/dfs/client/delete.py

import json, requests
from pathlib import Path

# 1) project root
PROJECT_ROOT  = Path(__file__).resolve().parents[3]

# 2) backend folder
BACKEND_DIR   = PROJECT_ROOT / "backend"

# 3) DFS metadata & chunks
DFS_META_DIR = BACKEND_DIR / "dfs" / "metadata"
CHUNK_DIR     = BACKEND_DIR / "dfs" / "chunks"

# 4) Local download area
DOWNLOAD_DIR  = PROJECT_ROOT / "downloaded_files"

# 5) Originals
INPUT_DIR     = BACKEND_DIR / "input_files"

# 6) Search index
INDEX_DIR     = BACKEND_DIR / "search_engine" / "index"
DOCS_FILE     = INDEX_DIR / "docs.json"
BM25_FILE     = INDEX_DIR / "bm25_index.json"
TFIDF_CACHE   = INDEX_DIR / "cached_tfidf_matrix.pkl"

def delete_file(filename: str) -> dict:
    meta_path = DFS_META_DIR / f"{filename}.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No metadata for {filename}")

    metadata = json.loads(meta_path.read_text())

    # 1) delete each chunk remotely
    failed = []
    for chunk_id, node_url in metadata.items():
        try:
            r = requests.delete(f"{node_url}/chunk/{chunk_id}", timeout=5)
            if r.status_code != 200:
                failed.append(chunk_id)
        except Exception:
            failed.append(chunk_id)
    if failed:
        return {"error":"couldn't delete chunks","failed":failed}

    # 2) remove metadata file
    meta_path.unlink(missing_ok=True)

    # 3) cleanup local chunk files
    for chunk_id in metadata:
        (CHUNK_DIR / chunk_id).unlink(missing_ok=True)

    # 4) remove reconstructed download
    (DOWNLOAD_DIR / filename).unlink(missing_ok=True)

    # 5) remove original upload if present
    #(INPUT_DIR / filename).unlink(missing_ok=True)

    # 6) update search index (docs.json & bm25_index.json)
    try:
        docs = json.loads(DOCS_FILE.read_text())
        bm25 = json.loads(BM25_FILE.read_text()).get("corpus", [])

        idx = next((i for i,d in enumerate(docs) if d["file_name"]==filename), None)
        if idx is not None:
            docs.pop(idx)
            bm25.pop(idx)
            DOCS_FILE.write_text(json.dumps(docs, indent=2))
            BM25_FILE.write_text(json.dumps({"corpus":bm25}, indent=2))
            TFIDF_CACHE.unlink(missing_ok=True)
    except Exception as e:
        return {"warning":f"Index cleanup failed: {e}"}

    return {"status":"deleted"}
