from pathlib import Path
from typing import List


def append_history(row: dict, history_path: str) -> None:
    # TODO: Persist history rows to CSV or database.
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("")


def load_history(history_path: str) -> List[dict]:
    # TODO: Read history back from storage.
    path = Path(history_path)
    if not path.exists():
        return []
    return []
