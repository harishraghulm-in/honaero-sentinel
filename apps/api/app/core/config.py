import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "HonAero Sentinel API"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./sentinel_dev.db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # Toolchains
    GCC_PATH: str = shutil.which("gcc") or "gcc"
    GCOV_PATH: str = shutil.which("gcov") or "gcov"
    CLANG_PATH: str = "clang"
    CMAKE_PATH: str = "cmake"

    # Execution limits & paths
    EXECUTION_ENGINE: str = "local_process"  # local_process or docker
    EXECUTION_TIMEOUT_SECONDS: int = 10
    MAX_SOURCE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
    MAX_ARTIFACT_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB
    ARTIFACT_STORAGE_PATH: Path = Path("./storage/artifacts")
    WORKSPACE_BASE_PATH: Path = Path("./workspaces")

    # Docker Worker
    DOCKER_IMAGE: str = "honaero-sentinel/execution-worker:latest"
    DOCKER_NETWORK: str = "sentinel-isolated"
    DOCKER_MEMORY_LIMIT: str = "512m"
    DOCKER_CPU_LIMIT: float = 1.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ARTIFACT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    settings.WORKSPACE_BASE_PATH.mkdir(parents=True, exist_ok=True)
    return settings

