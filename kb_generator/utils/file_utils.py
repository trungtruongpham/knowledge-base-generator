"""File discovery and manipulation utilities."""

import hashlib
import logging
from pathlib import Path
from typing import Iterator

from kb_generator.config import ALWAYS_EXCLUDE, SOLUTION_PATTERNS, PROJECT_PATTERNS, SOURCE_PATTERNS

logger = logging.getLogger(__name__)


def discover_solution_files(root: Path) -> list[Path]:
    """Discover all .sln and .slnx files in the directory tree.
    
    Args:
        root: Root directory to search
        
    Returns:
        List of solution file paths
    """
    solutions = []
    for pattern in SOLUTION_PATTERNS:
        solutions.extend(_glob_recursive(root, pattern))
    return sorted(set(solutions))


def discover_project_files(root: Path) -> list[Path]:
    """Discover all .csproj files in the directory tree.
    
    Args:
        root: Root directory to search
        
    Returns:
        List of project file paths
    """
    projects = []
    for pattern in PROJECT_PATTERNS:
        projects.extend(_glob_recursive(root, pattern))
    return sorted(set(projects))


def discover_cs_files(root: Path) -> list[Path]:
    """Discover all .cs source files in the directory tree.
    
    Args:
        root: Root directory to search
        
    Returns:
        List of C# source file paths
    """
    cs_files = []
    for pattern in SOURCE_PATTERNS:
        cs_files.extend(_glob_recursive(root, pattern))
    return sorted(set(cs_files))


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.
    
    Args:
        path: File path
        
    Returns:
        Hex digest of SHA256 hash
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _glob_recursive(root: Path, pattern: str) -> Iterator[Path]:
    """Recursively glob for pattern, excluding standard directories.
    
    Args:
        root: Root directory to search
        pattern: Glob pattern
        
    Yields:
        Matching file paths
    """
    for path in root.rglob(pattern):
        # Skip if any parent directory is in exclusion list
        if any(part in ALWAYS_EXCLUDE for part in path.parts):
            continue
        if path.is_file():
            yield path


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text_safe(path: Path, encoding: str = "utf-8") -> str:
    """Read text file with fallback encoding.
    
    Args:
        path: File path
        encoding: Primary encoding to try
        
    Returns:
        File contents as string
    """
    try:
        return path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        logger.warning(f"Failed to read {path} with {encoding}, trying UTF-8 with errors='ignore'")
        return path.read_text(encoding="utf-8", errors="ignore")
