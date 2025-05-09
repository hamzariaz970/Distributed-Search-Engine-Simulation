import os
import sys
import json
import requests
from dfs.core.chunker import split_file

# Configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHUNK_DIR = os.path.join(BASE_DIR, "chunks")
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
INPUT_DIR = os.path.join(BASE_DIR, "input_files")
LOAD_BALANCER_URL = "http://localhost:6001"

# Ensure required directories exist
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

def upload_file(file_path):
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    print(f"[INFO] Splitting file: {file_path}")
    chunk_files = split_file(file_path, output_dir=CHUNK_DIR)

    file_name = os.path.basename(file_path)
    metadata = {}

    for chunk_name in chunk_files:
        chunk_path = os.path.join(CHUNK_DIR, chunk_name)

        try:
            with open(chunk_path, "rb") as chunk_file:
                response = requests.post(
                    f"{LOAD_BALANCER_URL}/upload_chunk",
                    files={"chunk": chunk_file},
                    data={"chunk_id": chunk_name},
                    timeout=5
                )
                response.raise_for_status()
                result = response.json()
                print(f"[OK] Uploaded {chunk_name} → {result['cluster']} / {result['node']}")
                metadata[chunk_name] = result['node']
        except requests.exceptions.RequestException as e:
            print(f"[FAIL] Upload failed for {chunk_name}: {e}")
            return

    metadata_path = os.path.join(METADATA_DIR, f"{file_name}.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n[SUCCESS] File uploaded. Metadata saved at: {metadata_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client/upload.py <filename>")
        sys.exit(1)

    file_path = os.path.join(INPUT_DIR, sys.argv[1])
    upload_file(file_path)
