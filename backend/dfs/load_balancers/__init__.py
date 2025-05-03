import os
from datetime import datetime

# ---------------- Configuration Constants ----------------

DEFAULT_TIMEOUT = 5  # default HTTP timeout in seconds
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------- Shared Logging Function ----------------

def log(message, context="GLOBAL"):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    formatted = f"[{context}] {timestamp} {message}"
    log_file = os.path.join(LOG_DIR, f"{context.lower()}.log")

    with open(log_file, "a") as f:
        f.write(formatted + "\n")

    print(formatted)

# ---------------- Public API ----------------

__all__ = ["DEFAULT_TIMEOUT", "LOG_DIR", "log"]
