import subprocess
import sys
from pathlib import Path


def test_openapi_writes_file_with_lf(tmp_path: Path) -> None:
    out = tmp_path / "o.json"
    subprocess.run([sys.executable, "-m", "app.openapi", str(out)], check=True)
    data = out.read_bytes()
    assert b"/api/health" in data and b"\r" not in data
