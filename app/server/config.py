"""FastAPI server configuration."""

import dataclasses
import os
from pathlib import Path

import dotenv
from fastapi_mongo_base.core import config

dotenv.load_dotenv()


@dataclasses.dataclass
class Settings(config.Settings):
    """Server config settings."""

    base_dir: Path = Path(__file__).resolve().parent.parent
    base_path: str = "/api/shop/v1"
    core_url: str = os.getenv("CORE_URL", "https://app.uln.me")

    coverage_dir: Path = base_dir / "htmlcov"
    currency: str = "IRR"

    @classmethod
    def get_log_config(cls, console_level: str = "INFO", **kwargs: object) -> dict:
        log_config = {
            "formatters": {
                "standard": {
                    "format": "[{levelname} {name} : {filename}:{lineno} : {asctime} -> {funcName:10}] {message}",  # noqa: E501
                    "style": "{",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": console_level,
                    "formatter": "standard",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "filename": "logs/app.log",
                },
            },
            "loggers": {
                "": {
                    "handlers": [
                        "console",
                        "file",
                    ],
                    "level": console_level,
                    "propagate": True,
                },
            },
            "version": 1,
        }
        return log_config
