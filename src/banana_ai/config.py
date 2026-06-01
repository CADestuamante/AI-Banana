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
    path = Path(config_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig(
        app=AppSection(**data["app"]),
        inference=InferenceSection(**data["inference"]),
        input=InputSection(**data["input"]),
        storage=StorageSection(**data["storage"]),
        reporting=ReportingSection(**data["reporting"]),
    )
