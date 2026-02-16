"""Configuration constants and settings."""

from pathlib import Path
from typing import TypedDict


class KBConfig(TypedDict, total=False):
    """Configuration for KB generation."""
    exclude_projects: list[str]
    exclude_paths: list[str]
    output_dir: str
    include_source_snippets: bool
    max_method_body_lines: int


# Default configuration
DEFAULT_CONFIG: KBConfig = {
    "exclude_projects": ["*.Tests", "*.AspireHost"],
    "exclude_paths": ["**/Migrations/**", "**/obj/**", "**/bin/**"],
    "output_dir": ".kb",
    "include_source_snippets": True,
    "max_method_body_lines": 10,
}

# File patterns to discover
SOLUTION_PATTERNS = ["*.sln", "*.slnx"]
PROJECT_PATTERNS = ["*.csproj"]
SOURCE_PATTERNS = ["*.cs"]

# Directories to always exclude
ALWAYS_EXCLUDE = {"bin", "obj", ".git", "node_modules", ".vs", ".vscode"}
