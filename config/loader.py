"""
Centralized YAML configuration loader with environment overrides.

Non-secret configuration lives in config/config.yaml.
Secrets (tokens, passwords) should remain in environment variables.
"""
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_lock = threading.Lock()
_cached_config: Optional[Dict[str, Any]] = None


def _default_config_path() -> Path:
    # Default to project_root/config/config.yaml
    root = Path(__file__).resolve().parents[1]
    return root / "config" / "config.yaml"


def load_config(config_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from YAML file. Thread-safe and cached.

    Precedence:
    1) Explicit config_path argument
    2) CONFIG_FILE environment variable
    3) Default path: config/config.yaml
    """
    global _cached_config
    with _lock:
        if _cached_config is not None and not force_reload:
            return _cached_config

        # Determine path
        path_str = config_path or os.getenv("CONFIG_FILE")
        cfg_path = Path(path_str) if path_str else _default_config_path()

        config: Dict[str, Any] = {}

        if cfg_path.exists():
            try:
                with cfg_path.open("r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                # On YAML errors, fallback to empty config but do not crash
                print(f"[config] Failed to load YAML from {cfg_path}: {e}")
                config = {}
        else:
            # No file is okay; return empty config
            config = {}

        _cached_config = config
        return config


def get_config_value(path: str, default: Any = None, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Retrieve a nested configuration value using dot-separated path.

    Example:
        get_config_value("runner.time_sleep", 30)
    """
    cfg = config or load_config()
    current: Any = cfg
    for part in path.split('.'): 
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def as_dict() -> Dict[str, Any]:
    """Return the loaded configuration as a dict."""
    return load_config()


