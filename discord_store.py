"""
Thread-safe persistent store for mapping Roblox usernames to Discord IDs.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional, Dict, Union


class DiscordStore:
    """Manages thread-safe persistence for Roblox-to-Discord ID mappings."""

    def __init__(self, filepath: Optional[Union[Path, str]] = None) -> None:
        if filepath is None:
            self.filepath = Path(__file__).resolve().parent / "discord_mappings.json"
        else:
            self.filepath = Path(filepath)
        self._lock = threading.Lock()
        self._mappings: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            if self.filepath.exists():
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self._mappings = {
                                str(k).strip().lower(): str(v).strip()
                                for k, v in data.items()
                                if str(k).strip() and str(v).strip()
                            }
                        else:
                            self._mappings = {}
                except (json.JSONDecodeError, OSError):
                    self._mappings = {}
            else:
                self._mappings = {}

    def _save(self) -> None:
        # Assumes caller holds self._lock
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._mappings, f, indent=2, ensure_ascii=False)

    def get_all(self) -> Dict[str, str]:
        """Returns a copy of all mappings {lower_username: discord_id}."""
        with self._lock:
            return dict(self._mappings)

    def get(self, username: str) -> Optional[str]:
        """Returns the discord_id for the given username, or None if not mapped."""
        if not username:
            return None
        with self._lock:
            return self._mappings.get(username.strip().lower())

    def set(self, username: str, discord_id: Optional[str] = None) -> Dict[str, str]:
        """Sets or removes (if empty) a mapping, writes to disk, and returns all mappings."""
        clean_user = username.strip().lower() if username else ""
        if not clean_user:
            return self.get_all()

        clean_id = discord_id.strip() if discord_id else ""
        with self._lock:
            if clean_id:
                self._mappings[clean_user] = clean_id
            else:
                self._mappings.pop(clean_user, None)
            self._save()
            return dict(self._mappings)

    def bulk_set(self, mappings: Dict[str, str]) -> Dict[str, str]:
        """Merges a dictionary of mappings, writes to disk, and returns all mappings."""
        with self._lock:
            for username, discord_id in mappings.items():
                clean_user = str(username).strip().lower() if username else ""
                clean_id = str(discord_id).strip() if discord_id else ""
                if not clean_user:
                    continue
                if clean_id:
                    self._mappings[clean_user] = clean_id
                else:
                    self._mappings.pop(clean_user, None)
            self._save()
            return dict(self._mappings)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_mappings.json"
        store = DiscordStore(test_file)

        # 1. Test set & get
        store.set("PlayerOne", "123456789")
        assert store.get("playerone") == "123456789"
        assert store.get("PlayerOne") == "123456789"
        assert store.get("nonexistent") is None

        # 2. Test get_all
        all_maps = store.get_all()
        assert all_maps == {"playerone": "123456789"}

        # 3. Test bulk_set
        store.bulk_set({"PlayerTwo": "987654321", "PLAYERTHREE": "1122334455"})
        assert store.get("playertwo") == "987654321"
        assert store.get("playerthree") == "1122334455"

        # 4. Test removal via set with empty discord_id
        store.set("PlayerOne", "")
        assert store.get("playerone") is None
        assert "playerone" not in store.get_all()

        # 5. Verify file persistence on reload
        store_reloaded = DiscordStore(test_file)
        assert store_reloaded.get("playertwo") == "987654321"
        assert store_reloaded.get("playerthree") == "1122334455"
        assert len(store_reloaded.get_all()) == 2

        print("All DiscordStore tests passed successfully.")
