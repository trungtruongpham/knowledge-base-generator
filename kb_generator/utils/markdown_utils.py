"""Markdown generation utilities including YAML frontmatter."""

import yaml
from datetime import datetime
from typing import Any


def render_frontmatter(metadata: dict[str, Any]) -> str:
    """Render YAML frontmatter for Markdown files.
    
    Args:
        metadata: Dictionary of frontmatter fields
        
    Returns:
        YAML frontmatter block with --- delimiters
    """
    if not metadata:
        return ""
    
    yaml_content = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{yaml_content}---\n\n"


def create_code_block(code: str, language: str = "csharp") -> str:
    """Create a Markdown code block.
    
    Args:
        code: Code content
        language: Language identifier for syntax highlighting
        
    Returns:
        Formatted code block
    """
    return f"```{language}\n{code}\n```"


def create_table(headers: list[str], rows: list[list[str]]) -> str:
    """Create a Markdown table.
    
    Args:
        headers: Column headers
        rows: List of rows (each row is a list of cell values)
        
    Returns:
        Formatted Markdown table
    """
    if not headers or not rows:
        return ""
    
    # Create header row
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    # Create data rows
    data_rows = []
    for row in rows:
        # Pad row if necessary
        padded_row = row + [""] * (len(headers) - len(row))
        data_rows.append("| " + " | ".join(str(cell) for cell in padded_row) + " |")
    
    return "\n".join([header_row, separator] + data_rows)


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    # Escape pipe characters for tables
    return text.replace("|", "\\|")


def format_type_name(type_name: str) -> str:
    """Format a C# type name for Markdown display (escape generic brackets).
    
    Args:
        type_name: C# type name
        
    Returns:
        Formatted type name
    """
    # Escape angle brackets in generics
    return type_name.replace("<", "\\<").replace(">", "\\>")


def get_timestamp() -> str:
    """Get current timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp
    """
    return datetime.now().isoformat()
