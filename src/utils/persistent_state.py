"""
Persistent State Store for Job Alert Bot.
Synchronizes dynamic channels and dynamic keywords to a JSON state file (config/dynamic_state.json)
so that user customizations persist across server reboots, container redeploys, and ephemeral restarts.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger("persistent_state")

DEFAULT_STATE_PATH = "config/dynamic_state.json"


class PersistentStateStore:
    """Manages reading and writing persistent state to disk."""

    def __init__(self, file_path: str = DEFAULT_STATE_PATH):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not self.file_path.exists():
            default_data = {
                "dynamic_channels": [],
                "dynamic_keywords_include": [],
                "dynamic_keywords_exclude": [],
            }
            self.save_state(default_data)

    def load_state(self) -> Dict[str, List[str]]:
        """Loads state dictionary from JSON file."""
        try:
            if self.file_path.exists():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "dynamic_channels": data.get("dynamic_channels", []),
                        "dynamic_keywords_include": data.get("dynamic_keywords_include", []),
                        "dynamic_keywords_exclude": data.get("dynamic_keywords_exclude", []),
                    }
        except Exception as e:
            logger.error(f"Error loading state from {self.file_path}: {e}")
        return {
            "dynamic_channels": [],
            "dynamic_keywords_include": [],
            "dynamic_keywords_exclude": [],
        }

    def save_state(self, state: Dict[str, List[str]]) -> None:
        """Saves state dictionary to JSON file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            logger.debug(f"Flushed persistent state to {self.file_path}")
        except Exception as e:
            logger.error(f"Error saving state to {self.file_path}: {e}")
