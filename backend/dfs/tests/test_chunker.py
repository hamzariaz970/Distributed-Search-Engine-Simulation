import sys
import os
import filecmp

# Add core/ to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.chunker import split_file, reconstruct_file

# Define directories
BASE_DIR = os.path.dirname(__file__)
input_dir = os.path.join(BASE_DIR, "input_files")
output_dir = os.path.join(BASE_DIR, "output_files")
os.makedirs(output_dir, exist_ok=True)

# Define input and output file paths
input_file = os.path.join(input_dir, "sample.pdf")
output_file = os.path.join(output_dir, "reconstructed_sample.pdf")

# Run split and reconstruct
chunks = split_file(input_file)
reconstruct_file(chunks, output_file)

# Compare original and reconstructed file
match = filecmp.cmp(input_file, output_file)
print("Match:", match)
