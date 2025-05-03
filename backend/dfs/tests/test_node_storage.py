import os
import requests
import filecmp

# Define base paths
BASE_DIR = os.path.dirname(__file__)
CHUNK_NAME = "sample.pdf_chunk0"

chunk_path = os.path.join(BASE_DIR, "..", "chunks", CHUNK_NAME)
output_dir = os.path.join(BASE_DIR, "output_files")
os.makedirs(output_dir, exist_ok=True)

download_path = os.path.join(output_dir, "downloaded_chunk")

# Upload the chunk
with open(chunk_path, "rb") as f:
    r = requests.post("http://localhost:5001/store", files={"chunk": f}, data={"chunk_id": CHUNK_NAME})
    print("Upload response:", r.json())

# Download the same chunk
r = requests.get(f"http://localhost:5001/chunk/{CHUNK_NAME}")
with open(download_path, "wb") as f:
    f.write(r.content)

# Compare original and downloaded chunk
match = filecmp.cmp(chunk_path, download_path)
print("Match:", match)
