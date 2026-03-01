"""
JSON-backed storage for TITANS disposition state.

Replaces Redis persistence with local JSON files.
Each conversation gets its own state file.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from titans_disposition.variant import TITANSVariant

logger = logging.getLogger(__name__)


def _default_storage_dir() -> Path:
    """Return platform-appropriate default storage directory."""
    # Use XDG on Linux/macOS, fallback to ~/.config on Windows
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        base = Path(config_home)
    elif os.name == "nt":
        # Windows: use APPDATA if available, else ~/.config
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / ".config"
    else:
        base = Path.home() / ".config"
    return base / "titans-disposition" / "states"


def _safe_filename(conversation_id: str) -> str:
    """Convert conversation_id to a safe filename."""
    # Replace path-unsafe characters
    safe = conversation_id.replace("/", "__").replace("\\", "__")
    safe = safe.replace(":", "_").replace(" ", "_")
    # Ensure .json extension
    if not safe.endswith(".json"):
        safe += ".json"
    return safe


class JSONBackedMemoryStore:
    """
    JSON file-backed persistence for TITANSVariant state.

    Each conversation gets its own JSON file under the storage directory.
    State includes the full variant (M matrix, projections, gates, statistics).
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = _default_storage_dir()

        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"JSONBackedMemoryStore initialized at {self.storage_dir}")

    def save(self, conversation_id: str, variant: TITANSVariant) -> None:
        """
        Save variant state to a JSON file.

        Args:
            conversation_id: Unique conversation identifier
            variant: TITANSVariant instance to persist
        """
        filepath = self.storage_dir / _safe_filename(conversation_id)
        state = variant.save_state()
        state["_conversation_id"] = conversation_id

        try:
            # Write atomically: write to temp, then rename
            tmp_path = filepath.with_suffix(".json.tmp")
            with open(tmp_path, "w") as f:
                json.dump(state, f)
            tmp_path.replace(filepath)
            logger.debug(f"Saved state for conversation={conversation_id}")
        except Exception as e:
            logger.warning(f"Failed to save state for {conversation_id}: {e}")
            # Clean up temp file on failure
            tmp_path = filepath.with_suffix(".json.tmp")
            if tmp_path.exists():
                tmp_path.unlink()

    def load(self, conversation_id: str) -> Optional[TITANSVariant]:
        """
        Load variant state from a JSON file.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            TITANSVariant instance if file exists, None otherwise
        """
        filepath = self.storage_dir / _safe_filename(conversation_id)
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r") as f:
                state = json.load(f)
            variant = TITANSVariant.load_state(state)
            logger.debug(f"Loaded state for conversation={conversation_id}")
            return variant
        except Exception as e:
            logger.warning(f"Failed to load state for {conversation_id}: {e}")
            return None

    def list_conversations(self) -> list[str]:
        """
        List all saved conversation IDs.

        Returns:
            List of conversation IDs with persisted state
        """
        conversations = []
        for filepath in self.storage_dir.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    state = json.load(f)
                conv_id = state.get("_conversation_id")
                if conv_id:
                    conversations.append(conv_id)
                else:
                    # Fallback: derive from filename
                    name = filepath.stem
                    conversations.append(name.replace("__", "/").replace("_", " "))
            except Exception:
                continue
        return conversations

    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation's state file.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if deleted, False if not found
        """
        filepath = self.storage_dir / _safe_filename(conversation_id)
        if filepath.exists():
            filepath.unlink()
            logger.debug(f"Deleted state for conversation={conversation_id}")
            return True
        return False
