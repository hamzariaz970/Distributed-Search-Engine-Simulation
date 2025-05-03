````markdown
# DFS-PDC Project

## Overview

This project integrates a Distributed File System (DFS) with PDF chunk storage, indexing, and retrieval. It uses GROBID for metadata extraction from PDFs and supports chunked file storage and search via DFS.

---

## Setup Instructions

### **Windows Setup**

#### 1. Clone the Repository

1. Clone the repository:

   ```bash
   git clone <your-repository-url>
   cd DFS_PDC_PROJECT
````

#### 2. Set Up GROBID

1. Clone the GROBID repository:

   ```bash
   git clone https://github.com/kermitt2/grobid.git
   cd grobid
   ```

2. Install Gradle:

   * Download and install Gradle from [the official site](https://gradle.org/install/).
   * Alternatively, use **Chocolatey** if you have it installed:

     ```bash
     choco install gradle
     ```

3. Build GROBID:

   Once Gradle is installed, build GROBID using:

   ```bash
   gradle clean install
   ```

4. Start GROBID:

   ```bash
   gradle run
   ```

   GROBID will now be running on `http://localhost:8080`.

#### 3. Set Up Python Environment

1. **Create and activate the virtual environment** using `venv` or **`conda`**:

   * **Using `venv`**:

     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```

   * **Using `conda`**:

     If you prefer to use **`conda`** instead of `venv`, follow these steps:

     ```bash
     conda create --name dfs_pdc python=3.8
     conda activate dfs_pdc
     ```

2. **Install dependencies**:

   Create a `requirements.txt` in the project folder and run the following command:

   ```bash
   pip install -r requirements.txt
   ```

3. **Download NLTK 'punkt' tokenizer**:

   Run the following Python code to download the tokenizer:

   ```python
   import nltk
   nltk.download('punkt')
   ```

#### 4. Run the DFS Cluster

1. **Start the DFS cluster** by running the following command:

   ```bash
   python start_clusters.py
   ```

#### 5. Run the Search & Index Script

Once GROBID and DFS are up and running, you can index PDFs, search for documents, and download them:

```bash
python search_and_index.py
```

---

### **macOS Setup**

#### 1. Clone the Repository

1. Clone the repository:

   ```bash
   git clone <your-repository-url>
   cd DFS_PDC_PROJECT
   ```

#### 2. Set Up GROBID

1. Clone the GROBID repository:

   ```bash
   git clone https://github.com/kermitt2/grobid.git
   cd grobid
   ```

2. Install Gradle using **Homebrew**:

   ```bash
   brew install gradle
   ```

3. Build GROBID:

   Once Gradle is installed, build GROBID with the following command:

   ```bash
   ./gradlew clean install
   ```

4. Start GROBID:

   Start GROBID using:

   ```bash
   ./gradlew run
   ```

   GROBID will be running on `http://localhost:8080`.

#### 3. Set Up Python Environment

1. **Create and activate the virtual environment**:

   You can use either **`venv`** or **`conda`** for setting up the Python environment:

   * **Using `venv`**:

     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

   * **Using `conda`**:

     ```bash
     conda create --name dfs_pdc python=3.8
     conda activate dfs_pdc
     ```

2. **Install dependencies**:

   Innstall the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Download NLTK 'punkt' tokenizer (if not downloaded)**:

   Run the following Python code in `setup.py` file to download the tokenizer:

   ```python
    import nltk
    import platform
    import os

    def setup_nltk_data():
        # Check if the punkt tokenizer is available
        try:
            nltk.data.find('tokenizers/punkt')
            print("[INFO] punkt tokenizer is already available.")
        except LookupError:
            print("[INFO] punkt tokenizer not found, downloading...")
            nltk.download('punkt')

        # If you're on Windows, you might need to set an explicit path to nltk data
        if platform.system() == 'Windows':
            nltk.data.path.append(os.path.join(os.environ['APPDATA'], 'nltk_data'))

    if __name__ == "__main__":
        setup_nltk_data()
   ```

#### 4. Run the DFS Cluster

1. **Start the DFS cluster**:

   Start the DFS cluster by running:

   ```bash
   python start_clusters.py
   ```

#### 5. Run the Search & Index Script

Once GROBID and DFS are up and running, you can index PDFs, search for documents, and download them:

```bash
python search_and_index.py
```

---

## Project Structure

```
DFS_PDC_PROJECT/
│
├── dfs/                   # DFS Cluster and client scripts
├── downloaded_files/      # Files will be downloaded here
├── grobid/                 # GROBID repository (metadata extraction)
├── input_files/           # Input PDFs for indexing
├── search_engine/         # Search and indexing logic
├── .gitattributes          # Git configuration
├── README.md              # Project documentation
├── search_and_index.py    # Main script for searching and indexing PDFs
├── setup.py               # Setup file for dependencies
├── start_clusters.py      # Script to start the DFS cluster
└── venv/                  # Virtual environment
```

---

## Notes

* **GROBID** must be running locally on port `8080` for metadata extraction.
* **DFS** is used to store and reconstruct PDF chunks based on search results.
* **Python virtual environment**: Make sure you activate your `venv` or `conda` environment before running any Python scripts.

---

### **Conclusion**

These instructions will guide you through setting up the project on both Windows and macOS systems, configuring GROBID, setting up the DFS clusters, and running the indexing and search system.


```

---
