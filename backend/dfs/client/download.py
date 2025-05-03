# client/download.py
import os
import sys
import json
import hashlib
import re
import requests
from dfs.core.chunker import reconstruct_file

# Base paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
CHUNK_DIR = os.path.join(BASE_DIR, "chunks")
OUTPUT_DIR = os.path.join(BASE_DIR, "tests", "output_files")
INPUT_DIR = os.path.join(BASE_DIR, "tests", "input_files")

# Ensure dirs exist
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def calculate_sha256(file_path):
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return None

def extract_chunk_number(name):
    match = re.search(r"_chunk(\d+)$", name)
    return int(match.group(1)) if match else -1

def download_and_reconstruct(file_basename):
    metadata_file = os.path.join(METADATA_DIR, f"{file_basename}.json")
    if not os.path.exists(metadata_file):
        print(f"[ERROR] Metadata not found for {file_basename}")
        return

    with open(metadata_file, "r") as f:
        metadata = json.load(f)

    # Sort chunks using safe numeric key
    chunk_names = sorted(metadata.keys(), key=extract_chunk_number)

    for chunk_id in chunk_names:
        node_url = metadata[chunk_id]
        chunk_path = os.path.join(CHUNK_DIR, chunk_id)
        try:
            r = requests.get(f"{node_url}/chunk/{chunk_id}", timeout=5)
            r.raise_for_status()
            with open(chunk_path, "wb") as out_file:
                out_file.write(r.content)
            print(f"[OK] Downloaded {chunk_id} from {node_url}")
        except requests.RequestException as e:
            print(f"[ERROR] Failed to download {chunk_id} from {node_url}: {e}")
            return

    name, ext = os.path.splitext(file_basename)
    output_path = os.path.join(OUTPUT_DIR, f"{name}_reconstructed{ext}")
    reconstruct_file(chunk_names, output_path)

    # Verify integrity
    original_path = os.path.join(INPUT_DIR, file_basename)
    orig_hash = calculate_sha256(original_path)
    recon_hash = calculate_sha256(output_path)

    print(f"\n✅ Reconstructed file saved at: {output_path}")
    print(f"Original Hash     : {orig_hash}")
    print(f"Reconstructed Hash: {recon_hash}")

    if orig_hash and recon_hash:
        if orig_hash == recon_hash:
            print("🎉 Files are identical. Hash match successful.")
        else:
            print("⚠️ Files differ. Hash mismatch.")
    else:
        print("⚠️ Could not compare hashes (missing file).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client/download.py <file_basename>")
        sys.exit(1)

    filename = sys.argv[1]
    download_and_reconstruct(filename)
