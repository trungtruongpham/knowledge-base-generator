"""Parser for .NET solution files (.sln and .slnx)."""

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from kb_generator.parsers.models import SolutionInfo, ProjectInfo

logger = logging.getLogger(__name__)


def parse_solution(sln_path: Path) -> Optional[SolutionInfo]:
    """Parse a .NET solution file.
    
    Args:
        sln_path: Path to .sln or .slnx file
        
    Returns:
        SolutionInfo or None if parsing fails
    """
    if not sln_path.exists():
        logger.error(f"Solution file not found: {sln_path}")
        return None
    
    if sln_path.suffix == ".slnx":
        return _parse_slnx(sln_path)
    elif sln_path.suffix == ".sln":
        return _parse_sln(sln_path)
    else:
        logger.error(f"Unknown solution file type: {sln_path.suffix}")
        return None


def _parse_slnx(slnx_path: Path) -> Optional[SolutionInfo]:
    """Parse XML-based .slnx solution file.
    
    Args:
        slnx_path: Path to .slnx file
        
    Returns:
        SolutionInfo or None if parsing fails
    """
    try:
        tree = ET.parse(slnx_path)
        root = tree.getroot()
        
        solution = SolutionInfo(
            name=slnx_path.stem,
            path=str(slnx_path),
        )
        
        # Find all project entries
        # .slnx format: <Project Path="relative/path/to/project.csproj" ... />
        for project_elem in root.findall(".//Project"):
            proj_path = project_elem.get("Path")
            if proj_path:
                abs_proj_path = (slnx_path.parent / proj_path).resolve()
                # Projects will be fully parsed later
                solution.projects.append(
                    ProjectInfo(
                        name=Path(proj_path).stem,
                        path=str(abs_proj_path),
                    )
                )
        
        logger.debug(f"Parsed .slnx: {solution.name} with {len(solution.projects)} projects")
        return solution
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse .slnx file {slnx_path}: {e}")
        return None


def _parse_sln(sln_path: Path) -> Optional[SolutionInfo]:
    """Parse classic .sln solution file.
    
    Args:
        sln_path: Path to .sln file
        
    Returns:
        SolutionInfo or None if parsing fails
    """
    try:
        content = sln_path.read_text(encoding="utf-8-sig")  # Handle BOM
        
        solution = SolutionInfo(
            name=sln_path.stem,
            path=str(sln_path),
        )
        
        # Regex to match project lines:
        # Project("{GUID}") = "ProjectName", "Path\To\Project.csproj", "{GUID}"
        project_pattern = re.compile(
            r'Project\("\{[^}]+\}"\)\s*=\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"\{[^}]+\}"'
        )
        
        for match in project_pattern.finditer(content):
            proj_name = match.group(1)
            proj_relative_path = match.group(2).replace("\\", "/")
            
            # Skip solution folders
            if proj_relative_path.endswith(".csproj"):
                abs_proj_path = (sln_path.parent / proj_relative_path).resolve()
                solution.projects.append(
                    ProjectInfo(
                        name=proj_name,
                        path=str(abs_proj_path),
                    )
                )
        
        logger.debug(f"Parsed .sln: {solution.name} with {len(solution.projects)} projects")
        return solution
        
    except Exception as e:
        logger.error(f"Failed to parse .sln file {sln_path}: {e}")
        return None
