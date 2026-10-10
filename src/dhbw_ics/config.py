import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


def _secret(name: str) -> str:
    """Read a value from env var NAME or from the file named by NAME_FILE."""
    value = os.environ.get(name)
    if value:
        return value
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            value = Path(path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigError(f"{name}_FILE is not readable: {exc}") from exc
        if value:
            return value
    raise ConfigError(f"{name} or {name}_FILE must be set")


def _int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return value


def normalize_kurs(value: str) -> str:
    """Accept both the intranet ID (HOR-TINF2024) and the label (INF2024)."""
    value = value.strip().upper()
    return value if value.startswith("HOR-") else f"HOR-T{value}"


@dataclass(frozen=True)
class Settings:
    api_key: str
    intranet_user: str
    intranet_password: str
    kurs: str = "HOR-TINF2024"
    weeks_ahead: int = 4
    db_path: str = "/data/schedule.db"
    filters_file: str = ""
    cache_ttl: int = 3600
    min_fetch_interval: int = 300
    request_delay: float = 2.0
    login_retries: int = 2
    login_cooldown: int = 6 * 3600

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=_secret("API_KEY"),
            intranet_user=_secret("INTRANET_USER"),
            intranet_password=_secret("INTRANET_PASSWORD"),
            kurs=normalize_kurs(os.environ.get("KURS") or "HOR-TINF2024"),
            weeks_ahead=_int("WEEKS_AHEAD", 4),
            db_path=os.environ.get("DB_PATH") or "/data/schedule.db",
            filters_file=os.environ.get("FILTERS_FILE") or "/data/filters.toml",
            cache_ttl=_int("CACHE_TTL_SECONDS", 3600),
            min_fetch_interval=_int("MIN_FETCH_INTERVAL_SECONDS", 300),
            request_delay=float(_int("REQUEST_DELAY_SECONDS", 2)),
        )
