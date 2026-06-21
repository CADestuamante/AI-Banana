from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class AppSection:
    name: str
    log_level: str


@dataclass
class InferenceSection:
    model_path: str
    device: str
    confidence_threshold: float


@dataclass
class InputSection:
    source_type: str
    camera_index: int
    file_path: str


@dataclass
class StorageSection:
    db_path: str 
    history_path: str
    reports_path: str


@dataclass
class ReportingSection:
    formats: List[str]


@dataclass
class AppConfig:
    app: AppSection
    inference: InferenceSection
    input: InputSection
    storage: StorageSection
    reporting: ReportingSection


def load_config(config_path: str = "configs/default.yaml") -> AppConfig:
    # Nếu là đường dẫn tương đối, tìm từ thư mục cha của module
    path = Path(config_path)
    if not path.is_absolute():
        # Tìm thư mục project gốc (chứa src/)
        current = Path(__file__).resolve().parent
        while current != current.parent:
            if (current.parent / "configs" / "default.yaml").exists():
                path = current.parent / config_path
                break
            current = current.parent
    
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig(
        app=AppSection(**data["app"]),
        inference=InferenceSection(**data["inference"]),
        input=InputSection(**data["input"]),
        storage=StorageSection(**data["storage"]),
        reporting=ReportingSection(**data["reporting"]),
    )
