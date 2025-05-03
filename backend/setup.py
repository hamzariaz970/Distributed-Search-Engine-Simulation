import os
import nltk
import platform
from pathlib import Path

def setup_nltk_data():
    # Check if the punkt tokenizer is available
    try:
        nltk.data.find('tokenizers/punkt')
        print("[INFO] punkt tokenizer is already available.")
            # If you're on Windows, you might need to set an explicit path to nltk data
        if platform.system() == 'Windows':
            nltk.data.path.append(os.path.join(os.environ['APPDATA'], 'nltk_data'))
            nltk.download('punkt')
    except LookupError:
        print("[INFO] punkt tokenizer not found, downloading...")
        nltk.download('punkt')

if __name__ == "__main__":
    setup_nltk_data()
