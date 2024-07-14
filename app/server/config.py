"""FastAPI server configuration."""

import dataclasses
import logging
import logging.config
import os
from pathlib import Path

import dotenv
from singleton import Singleton

dotenv.load_dotenv()
base_dir = Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class Settings(metaclass=Singleton):
    """Server config settings."""

    base_dir: Path = base_dir
    root_url: str = os.getenv("DOMAIN", default="http://localhost:8000")
    project_name: str = os.getenv("PROJECT_NAME", default="UFaaS")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", default="sqlite+aiosqlite:///logs/app.db"
    )
    # DATABASE_URL: str = os.getenv(
    #     "DATABASE_URL", default="sqlite:///:memory:"
    # )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC", default="sqlite:///./test.db"
    )

    testing: bool = os.getenv("TESTING", default=False)

    log_config = {
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "standard",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "INFO",
                "filename": base_dir / "logs" / f"{project_name}.log",
                "formatter": "standard",
            },
        },
        "formatters": {
            "standard": {
                "format": "[{levelname} : {filename}:{lineno} : {asctime} -> {funcName:10}] {message}",
                # "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                "style": "{",
            }
        },
        "loggers": {
            "": {
                "handlers": [
                    "console",
                    "file",
                ],
                "level": "INFO",
                "propagate": True,
            }
        },
    }

    def config_logger(self):
        if not (base_dir / "logs").exists():
            (base_dir / "logs").mkdir()

        logging.config.dictConfig(self.log_config)
