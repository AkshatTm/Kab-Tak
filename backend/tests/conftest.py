from pathlib import Path

import pytest

from app.db.migrate import upgrade_with_backup


@pytest.fixture
def migrated_url(tmp_path: Path) -> str:
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    upgrade_with_backup(url)
    return url
