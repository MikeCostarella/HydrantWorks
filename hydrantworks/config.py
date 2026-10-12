"""Settings, read once from environment variables (and a local .env file, if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=value lines, no overriding of real environment variables."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    db_path: Path
    hydrants_csv: Path
    read_key: str
    write_key: str
    chaos: str = ""
    chaos_seed: int | None = None
    request_log: Path | None = None
    seed_work_data: bool = True
    extra: dict[str, str] = field(default_factory=dict)


def load_settings() -> Settings:
    _load_dotenv(ROOT / ".env")
    log = os.environ.get("HW_REQUEST_LOG", "").strip()
    seed = os.environ.get("HW_CHAOS_SEED", "").strip()
    return Settings(
        db_path=Path(os.environ.get("HW_DB_PATH", str(ROOT / "hydrantworks.db"))),
        hydrants_csv=Path(os.environ.get("HW_HYDRANTS_CSV", str(ROOT / "data" / "hydrants.csv"))),
        read_key=os.environ.get("HW_READ_KEY", "read-key-local"),
        write_key=os.environ.get("HW_WRITE_KEY", "write-key-local"),
        chaos=os.environ.get("HW_CHAOS", "").strip(),
        chaos_seed=int(seed) if seed else None,
        request_log=Path(log) if log else None,
        seed_work_data=os.environ.get("HW_SEED_WORK_DATA", "1") != "0",
    )
