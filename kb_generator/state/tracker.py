"""State tracker for incremental updates."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from kb_generator.state.models import KBState, FileState
from kb_generator.utils.file_utils import compute_file_hash

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    """Represents changes detected between scans."""
    added: list[Path] = field(default_factory=list)
    modified: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.modified or self.deleted)
    
    @property
    def all_changed(self) -> list[Path]:
        """Get all changed files (added + modified)."""
        return self.added + self.modified


class StateTracker:
    """Tracks file state for incremental updates."""
    
    STATE_FILENAME = ".kb-state.json"
    
    def __init__(self, kb_dir: Path):
        """Initialize state tracker.
        
        Args:
            kb_dir: Knowledge base output directory
        """
        self.kb_dir = kb_dir
        self.state_path = kb_dir / self.STATE_FILENAME
    
    def load_state(self) -> Optional[KBState]:
        """Load existing state from disk.
        
        Returns:
            KBState if found, None otherwise
        """
        if not self.state_path.exists():
            logger.debug("No existing state found")
            return None
        
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = KBState.from_dict(data)
            logger.info(f"Loaded state with {len(state.files)} tracked files")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def save_state(self, state: KBState) -> None:
        """Save state to disk.
        
        Args:
            state: State to save
        """
        try:
            # Ensure KB directory exists
            self.kb_dir.mkdir(parents=True, exist_ok=True)
            
            # Update timestamps
            now = datetime.now().isoformat()
            state.last_update = now
            
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(f"Saved state to {self.state_path}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def compute_changes(self, source_files: list[Path], state: KBState) -> ChangeSet:
        """Compute changes between current files and stored state.
        
        Args:
            source_files: List of current source files
            state: Previous state
            
        Returns:
            ChangeSet with added/modified/deleted files
        """
        changeset = ChangeSet()
        
        # Build set of current file paths (as strings)
        current_paths = {str(f.resolve()) for f in source_files}
        
        # Find added and modified files
        for file_path in source_files:
            path_str = str(file_path.resolve())
            
            if path_str not in state.files:
                # New file
                changeset.added.append(file_path)
                logger.debug(f"Added: {file_path.name}")
            else:
                # Check if modified
                current_hash = compute_file_hash(file_path)
                if current_hash != state.files[path_str].sha256:
                    changeset.modified.append(file_path)
                    logger.debug(f"Modified: {file_path.name}")
        
        # Find deleted files
        for path_str in state.files.keys():
            if path_str not in current_paths:
                changeset.deleted.append(Path(path_str))
                logger.debug(f"Deleted: {Path(path_str).name}")
        
        logger.info(f"Changes: +{len(changeset.added)} ~{len(changeset.modified)} -{len(changeset.deleted)}")
        return changeset
    
    def update_file_states(self, state: KBState, files: list[Path]) -> None:
        """Update file states in the KB state.
        
        Args:
            state: State to update
            files: Files to record/update
        """
        now = datetime.now().isoformat()
        
        for file_path in files:
            path_str = str(file_path.resolve())
            file_hash = compute_file_hash(file_path)
            file_size = file_path.stat().st_size
            
            state.files[path_str] = FileState(
                path=path_str,
                sha256=file_hash,
                last_scanned=now,
                size_bytes=file_size,
            )
    
    def mark_kb_output(self, state: KBState, kb_file: str, source_files: list[str]) -> None:
        """Mark which source files contributed to a KB output file.
        
        Args:
            state: State to update
            kb_file: Relative path to KB output file
            source_files: Source files that contributed (absolute paths)
        """
        state.kb_outputs[kb_file] = source_files
    
    def get_affected_kb_files(self, state: KBState, changed_files: list[Path]) -> set[str]:
        """Get KB files that need regeneration based on changed source files.
        
        Args:
            state: Current state
            changed_files: Files that have changed
            
        Returns:
            Set of KB file paths that need regeneration
        """
        changed_paths = {str(f.resolve()) for f in changed_files}
        affected = set()
        
        for kb_file, source_files in state.kb_outputs.items():
            # If any source file for this KB file has changed, mark it for regeneration
            if any(src in changed_paths for src in source_files):
                affected.add(kb_file)
        
        return affected
