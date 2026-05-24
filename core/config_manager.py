"""
Config Manager - Lưu / tải cấu hình stream
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

CONFIG_DIR = Path.home() / ".livestream_pro"
CONFIG_FILE = CONFIG_DIR / "config.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "profiles": {},
    "last_profile": None,
    "app": {
        "theme": "dark",
        "log_max_lines": 500,
        "ffmpeg_path": "ffmpeg",
        "ytdlp_path": "yt-dlp",
    },
}


def load_config() -> Dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge với defaults để tránh thiếu key
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def save_profile(name: str, profile_data: Dict[str, Any]) -> None:
    config = load_config()
    config["profiles"][name] = profile_data
    config["last_profile"] = name
    save_config(config)


def load_profile(name: str) -> Optional[Dict[str, Any]]:
    config = load_config()
    return config.get("profiles", {}).get(name)


def list_profiles() -> list:
    config = load_config()
    return list(config.get("profiles", {}).keys())


def delete_profile(name: str) -> None:
    config = load_config()
    config.get("profiles", {}).pop(name, None)
    if config.get("last_profile") == name:
        config["last_profile"] = None
    save_config(config)
