import json
import sys

from app.main import create_app

if __name__ == "__main__":
    sys.stdout.reconfigure(newline="\n")  # type: ignore[union-attr]  # same bytes on Windows and Linux
    print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))
