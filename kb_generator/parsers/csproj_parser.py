"""Parser for .csproj project files."""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from kb_generator.parsers.models import ProjectInfo, PackageRef

logger = logging.getLogger(__name__)


def parse_project(csproj_path: Path, central_packages: Optional[dict[str, str]] = None) -> Optional[ProjectInfo]:
    """Parse a .csproj file.
    
    Args:
        csproj_path: Path to .csproj file
        central_packages: Dictionary of package name -> version from Directory.Packages.props
        
    Returns:
        ProjectInfo or None if parsing fails
    """
    if not csproj_path.exists():
        logger.error(f"Project file not found: {csproj_path}")
        return None
    
    try:
        tree = ET.parse(csproj_path)
        root = tree.getroot()
        
        # Extract SDK from root element
        sdk = root.get("Sdk", "Microsoft.NET.Sdk")
        
        project = ProjectInfo(
            name=csproj_path.stem,
            path=str(csproj_path),
            sdk=sdk,
        )
        
        # Parse target framework
        target_framework_elem = root.find(".//TargetFramework")
        if target_framework_elem is not None and target_framework_elem.text:
            project.target_framework = target_framework_elem.text
        
        # Parse project references
        for proj_ref in root.findall(".//ProjectReference"):
            ref_path = proj_ref.get("Include")
            if ref_path:
                abs_ref_path = (csproj_path.parent / ref_path).resolve()
                project.project_references.append(str(abs_ref_path))
        
        # Parse package references
        for pkg_ref in root.findall(".//PackageReference"):
            pkg_name = pkg_ref.get("Include")
            if pkg_name:
                # Try to get version from attribute first
                pkg_version = pkg_ref.get("Version")
                
                # Fall back to central package management
                if not pkg_version and central_packages:
                    pkg_version = central_packages.get(pkg_name)
                
                project.package_references.append(
                    PackageRef(name=pkg_name, version=pkg_version)
                )
        
        logger.debug(f"Parsed project: {project.name} ({sdk})")
        return project
        
    except ET.ParseError as e:
        logger.error(f"Failed to parse .csproj file {csproj_path}: {e}")
        return None


def load_central_packages(root_dir: Path) -> dict[str, str]:
    """Load central package versions from Directory.Packages.props.
    
    Args:
        root_dir: Root directory of the solution
        
    Returns:
        Dictionary mapping package name to version
    """
    props_path = root_dir / "Directory.Packages.props"
    if not props_path.exists():
        return {}
    
    try:
        tree = ET.parse(props_path)
        root = tree.getroot()
        
        packages = {}
        for pkg_version in root.findall(".//PackageVersion"):
            pkg_name = pkg_version.get("Include")
            version = pkg_version.get("Version")
            if pkg_name and version:
                packages[pkg_name] = version
        
        logger.debug(f"Loaded {len(packages)} central package versions")
        return packages
        
    except ET.ParseError as e:
        logger.warning(f"Failed to parse Directory.Packages.props: {e}")
        return {}
