import os
import sys
from pathlib import Path

# Add the dfs directory to the Python path
sys.path.append(str(Path(__file__).resolve().parents[1] / 'dfs'))


def split_file(file_path, output_dir="chunks", chunk_size=1024 * 1024):
    """
    Splits a file into binary chunks.

    Args:
        file_path (str): Path to the input file.
        output_dir (str): Directory to save chunks.
        chunk_size (int): Size of each chunk in bytes (default: 1MB).

    Returns:
        List[str]: Ordered list of chunk file names.
    """
    os.makedirs(output_dir, exist_ok=True)
    chunks = []
    file_name = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        i = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunk_name = f"{file_name}_chunk{i:05d}" 
            chunk_path = os.path.join(output_dir, chunk_name)
            with open(chunk_path, 'wb') as cf:
                cf.write(chunk)
            chunks.append(chunk_name)
            i += 1

    return chunks



def reconstruct_file(chunk_files, output_path, input_dir="chunks"):
    """
    Reconstructs a file from its chunks.

    Args:
        chunk_files (List[str]): Ordered list of chunk filenames.
        output_path (str): Path to the output file.
        input_dir (str): Directory where chunks are located.
    """
    with open(output_path, 'wb') as out_file:
        for chunk_name in chunk_files:
            chunk_path = os.path.join(input_dir, chunk_name)
            with open(chunk_path, 'rb') as cf:
                out_file.write(cf.read())
