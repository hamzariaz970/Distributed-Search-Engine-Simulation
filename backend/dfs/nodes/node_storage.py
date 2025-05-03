import shutil
import os
import traceback
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Directory where chunks will be stored
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'node_storage'))
os.makedirs(STORAGE_DIR, exist_ok=True)


@app.route('/store', methods=['POST'])
def store_chunk():
    """
    Receives and stores a chunk.
    Expects 'chunk_id' as form field and the file as 'chunk'.
    """
    chunk_id = request.form.get('chunk_id')
    chunk = request.files.get('chunk')

    if not chunk_id or not chunk:
        return jsonify({"error": "Missing chunk_id or chunk"}), 400

    chunk.save(os.path.join(STORAGE_DIR, chunk_id))
    return jsonify({"status": "stored", "chunk_id": chunk_id})


@app.route('/status', methods=['GET'])
def node_status():
    """
    Returns current free disk space and number of stored chunks.
    """
    try:
        total, used, free = shutil.disk_usage(STORAGE_DIR)
        chunks = [
            name for name in os.listdir(STORAGE_DIR)
            if os.path.isfile(os.path.join(STORAGE_DIR, name))
        ]
        return jsonify({
            "free_mb": round(free / (1024 * 1024), 2),
            "chunk_count": len(chunks)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve status: {str(e)}"}), 500


@app.route('/chunk/<chunk_id>', methods=['GET'])
def get_chunk(chunk_id):
    """
    Serves a chunk back to the client.
    """
    chunk_path = os.path.join(STORAGE_DIR, chunk_id)
    if not os.path.exists(chunk_path):
        return jsonify({"error": "Chunk not found"}), 404
    return send_file(chunk_path, as_attachment=True)


@app.route('/chunk/<chunk_id>', methods=['DELETE'])
def delete_chunk(chunk_id):
    """
    Deletes a chunk from local storage.
    """
    chunk_path = os.path.join(STORAGE_DIR, chunk_id)
    if os.path.exists(chunk_path):
        os.remove(chunk_path)
        return jsonify({"status": "deleted", "chunk_id": chunk_id})
    return jsonify({"error": "Chunk not found"}), 404


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001, help='Port for this node to run on')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=args.port)
