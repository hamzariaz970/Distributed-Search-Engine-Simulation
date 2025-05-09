# app.py

import os
import json
import requests
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_file, abort

# —— Paths —— 
BASE_DIR     = Path(__file__).parent.resolve()
FRONTEND_DIR = BASE_DIR / "frontend"
BACKEND_DIR  = BASE_DIR / "backend"

DFS_META     = BACKEND_DIR / "dfs" / "metadata"
CHUNK_DIR    = BASE_DIR / BACKEND_DIR / "chunks"
DOWNLOAD_DIR = BASE_DIR / "downloaded_files"
for d in (CHUNK_DIR, DOWNLOAD_DIR):
    d.mkdir(exist_ok=True)

# Make sure we can import your backend modules
sys.path.insert(0, str(BACKEND_DIR))

from backend.dfs.client.delete import delete_file
from backend.main import index_and_upload_pdf, search_query
from backend.dfs.core.chunker import reconstruct_file

# —— Flask App Setup —— 
app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path=""
)

# —— Frontend Routes —— 

@app.route("/")
def dashboard():
    return app.send_static_file("dfs_dashboard.html")

@app.route("/indexing.html")
def indexing_page():
    return app.send_static_file("indexing.html")

@app.route("/search_and_list.html")
def search_and_list_page():
    return app.send_static_file("search_and_list.html")

# —— API Endpoints —— 

# 1) Upload & index
@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file provided"}), 400

    filename = f.filename

    # Check file extension
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 415  # Unsupported Media Type

    # Check if file with same name already exists
    docs_json = BACKEND_DIR / "search_engine" / "index" / "docs.json"
    if docs_json.exists():
        docs = json.loads(docs_json.read_text())
        if any(d["file_name"] == filename for d in docs):
            return jsonify({"error": "File already exists"}), 409

    tmp_dir = BACKEND_DIR / "input_files"
    tmp_dir.mkdir(exist_ok=True)
    target = tmp_dir / filename
    f.save(target)

    index_and_upload_pdf(str(target))
    return jsonify({"status": "ok"}), 200



# 2) List all known files (with metadata)
@app.route("/api/files", methods=["GET"])
def api_list_files():
    docs_json = BACKEND_DIR / "search_engine" / "index" / "docs.json"
    if not docs_json.exists():
        return jsonify([])
    docs = json.loads(docs_json.read_text())
    return jsonify([
        {
            "file_name": d["file_name"],
            "title":     d.get("title", ""),
            "author":    d.get("author", "")
        }
        for d in docs
    ])

# 3) Search
@app.route("/api/search", methods=["POST"])
def api_search():
    body = request.get_json() or {}
    q = body.get("query", "").strip()
    if not q:
        return jsonify({"results": []})

    matched = search_query(q)
    docs_file = BACKEND_DIR / "search_engine" / "index" / "docs.json"
    all_docs = json.loads(docs_file.read_text()) if docs_file.exists() else []

    out = []
    for basename, _metadata in matched:
        info = next((d for d in all_docs if d["file_name"] == basename), {})
        out.append({
            "basename": basename,
            "title":    info.get("title"),
            "author":   info.get("author")
        })
    return jsonify({"results": out})

# 4) Download
@app.route("/api/download/<filename>", methods=["GET"])
def api_download(filename):
    meta_file = DFS_META / f"{filename}.json"
    if not meta_file.exists():
        return abort(404)

    metadata = json.loads(meta_file.read_text())
    for chunk_id, node_url in metadata.items():
        r = requests.get(f"{node_url}/chunk/{chunk_id}", timeout=5)
        r.raise_for_status()
        (CHUNK_DIR / chunk_id).write_bytes(r.content)

    out_path = DOWNLOAD_DIR / filename
    reconstruct_file(list(metadata.keys()), str(out_path), input_dir=str(CHUNK_DIR))
    return send_file(str(out_path), as_attachment=True)

# 5) View in-browser
@app.route("/api/view/<filename>", methods=["GET"])
def api_view(filename):
    meta_file = DFS_META / f"{filename}.json"
    if not meta_file.exists():
        return abort(404)
    metadata = json.loads(meta_file.read_text())
    for chunk_id, node in metadata.items():
        r = requests.get(f"{node}/chunk/{chunk_id}", timeout=5)
        r.raise_for_status()
        (CHUNK_DIR / chunk_id).write_bytes(r.content)

    out_path = DOWNLOAD_DIR / filename
    reconstruct_file(list(metadata.keys()), str(out_path), input_dir=str(CHUNK_DIR))
    return send_file(
        str(out_path),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename
    )

# 6) Snippet + metadata for hover preview
@app.route("/api/snippet/<filename>", methods=["GET"])
def api_snippet(filename):
    docs_path = BACKEND_DIR / "search_engine" / "index" / "docs.json"
    if not docs_path.exists():
        return jsonify({"snippet": "", "title": "", "author": ""}), 404

    docs = json.loads(docs_path.read_text())
    entry = next((d for d in docs if d["file_name"] == filename), None)
    if not entry:
        return jsonify({"snippet": "", "title": "", "author": ""}), 404

    idx = next((i for i,d in enumerate(docs) if d["file_name"] == filename), None)
    snippet = ""
    bm25_path = BACKEND_DIR / "search_engine" / "index" / "bm25_index.json"
    if idx is not None and bm25_path.exists():
        corpus = json.loads(bm25_path.read_text()).get("corpus", [])
        text = corpus[idx].replace("\n"," ")
        snippet = (text[:200].strip() + "…") if text else ""

    return jsonify({
        "snippet": snippet,
        "title":   entry.get("title",""),
        "author":  entry.get("author","")
    })

# 7) Delete
@app.route("/api/delete/<filename>", methods=["DELETE"])
def api_delete(filename):
    try:
        result = delete_file(filename)
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result), 200
    except FileNotFoundError:
        abort(404)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
