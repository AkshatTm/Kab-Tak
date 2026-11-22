import json
import sys
from pathlib import Path

from app.main import create_app

if __name__ == "__main__":
    text = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    # Write bytes: same LF output on Windows and Linux (CI diffs this file).
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_bytes(text.encode())
    else:
        sys.stdout.buffer.write(text.encode())
