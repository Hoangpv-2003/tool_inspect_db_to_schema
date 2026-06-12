import yaml
from pathlib import Path
from .schema import AppConfig

class ConfigLoader:
    @staticmethod
    def load(path: str) -> AppConfig:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        return AppConfig(**data)
