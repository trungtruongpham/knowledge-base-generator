"""State models for tracking file changes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FileState:
    """State of a single source file."""
    path: str
    sha256: str
    last_scanned: str  # ISO datetime
    size_bytes: int


@dataclass
class KBState:
    """Complete state of the knowledge base."""
    version: str = "0.1.0"
    last_full_scan: str = ""
    last_update: str = ""
    files: dict[str, FileState] = field(default_factory=dict)  # source path → state
    kb_outputs: dict[str, list[str]] = field(default_factory=dict)  # KB file → source files it was generated from
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "last_full_scan": self.last_full_scan,
            "last_update": self.last_update,
            "files": {
                path: {
                    "path": file_state.path,
                    "sha256": file_state.sha256,
                    "last_scanned": file_state.last_scanned,
                    "size_bytes": file_state.size_bytes,
                }
                for path, file_state in self.files.items()
            },
            "kb_outputs": self.kb_outputs,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KBState":
        """Create from dictionary loaded from JSON."""
        files = {
            path: FileState(**file_data)
            for path, file_data in data.get("files", {}).items()
        }
        
        return cls(
            version=data.get("version", "0.1.0"),
            last_full_scan=data.get("last_full_scan", ""),
            last_update=data.get("last_update", ""),
            files=files,
            kb_outputs=data.get("kb_outputs", {}),
        )
