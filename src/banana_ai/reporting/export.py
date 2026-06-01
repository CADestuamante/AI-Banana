from pathlib import Path
from typing import List


def export_report(rows: List[dict], output_dir: str, fmt: str) -> Path:
    # TODO: Implement CSV/XLSX export.
    output_path = Path(output_dir) / f"report.{fmt}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("", encoding="utf-8")
    return output_path
