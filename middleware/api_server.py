from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import json

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

@app.route('/api/upload', methods=['POST'])
def handle_upload():
    file = request.files['file']
    if not file:
        return jsonify({"error": "No file provided"}), 400
    
    upload_dir = os.path.join(BASE_DIR, "tests", "input_files")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    try:
        result = subprocess.run(
            ["python", "client/upload.py", file.filename],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            env={"PYTHONPATH": BASE_DIR}
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    metadata_dir = os.path.join(BASE_DIR, "metadata")
    files = [f.replace('.json', '') for f in os.listdir(metadata_dir) if f.endswith('.json')]
    return jsonify(files)

@app.route('/api/download/<filename>', methods=['GET'])
def handle_download(filename):
    try:
        result = subprocess.run(
            ["python", "client/download.py", filename],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            env={"PYTHONPATH": BASE_DIR}
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
        return jsonify({"message": "Download initiated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<filename>', methods=['DELETE'])
def handle_delete(filename):
    try:
        result = subprocess.run(
            ["python", "client/delete.py", filename],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            env={"PYTHONPATH": BASE_DIR}
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
        return jsonify({"message": "File deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)