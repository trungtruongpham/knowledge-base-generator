"""Generate SUMMARY.md - condensed overview for LLM context."""

import logging
from pathlib import Path

from kb_generator.parsers.models import SolutionInfo, ProjectInfo, ClassInfo, DomainAggregate, UseCaseInfo
from kb_generator.utils.markdown_utils import render_frontmatter, create_table, get_timestamp

logger = logging.getLogger(__name__)


def generate_summary(
    solution: SolutionInfo,
    all_classes: list[ClassInfo],
    aggregates: list[DomainAggregate],
    use_cases: list[UseCaseInfo],
    output_dir: Path,
) -> Path:
    """Generate SUMMARY.md with condensed project overview.
    
    Args:
        solution: Parsed solution info
        all_classes: All parsed classes
        aggregates: Detected domain aggregates
        use_cases: Detected use cases
        output_dir: KB output directory
        
    Returns:
        Path to generated file
    """
    output_path = output_dir / "SUMMARY.md"
    
    # Build content
    frontmatter = render_frontmatter({
        "title": f"{solution.name} - Knowledge Base Summary",
        "type": "summary",
        "generated_at": get_timestamp(),
    })
    
    content = [frontmatter]
    
    # Title and overview
    content.append(f"# {solution.name}\n")
    content.append(f"> **Knowledge Base Summary** — Generated from .NET solution\n")
    content.append(f"**Total Projects:** {len(solution.projects)}\n")
    content.append(f"**Total Classes:** {len(all_classes)}\n")
    content.append(f"**Domain Aggregates:** {len(aggregates)}\n")
    content.append(f"**Use Cases:** {len(use_cases)}\n\n")
    
    # Project structure
    content.append("## 📦 Project Structure\n\n")
    
    project_rows = []
    for proj in solution.projects:
        proj_type = _get_project_type(proj)
        framework = proj.target_framework or "N/A"
        project_rows.append([proj.name, proj_type, framework])
    
    content.append(create_table(
        ["Project", "Type", "Framework"],
        project_rows
    ))
    content.append("\n\n")
    
    # Domain model overview
    if aggregates:
        content.append("## 🏛️ Domain Model\n\n")
        for agg in aggregates:
            content.append(f"### {agg.root_entity.name}\n\n")
            content.append(f"**Namespace:** `{agg.root_entity.namespace}`\n\n")
            
            if agg.value_objects:
                vo_names = ", ".join(f"`{vo.name}`" for vo in agg.value_objects)
                content.append(f"**Value Objects:** {vo_names}\n\n")
            
            if agg.domain_events:
                event_names = ", ".join(f"`{e.name}`" for e in agg.domain_events)
                content.append(f"**Events:** {event_names}\n\n")
            
            # Properties table
            if agg.root_entity.properties:
                prop_rows = [[p.name, p.type_name] for p in agg.root_entity.properties[:5]]  # Limit to 5
                content.append(create_table(["Property", "Type"], prop_rows))
                content.append("\n\n")
    
    # Use cases overview
    if use_cases:
        content.append("## ⚡ Use Cases\n\n")
        
        commands = [uc for uc in use_cases if uc.pattern == "Command"]
        queries = [uc for uc in use_cases if uc.pattern == "Query"]
        
        if commands:
            content.append("### Commands\n\n")
            for uc in commands[:10]:  # Limit to 10
                deps = ", ".join(uc.dependencies[:3])  # First 3 dependencies
                content.append(f"- **{uc.command_or_query.name}** → `{uc.handler.name}`\n")
                if deps:
                    content.append(f"  - Dependencies: {deps}\n")
            content.append("\n")
        
        if queries:
            content.append("### Queries\n\n")
            for uc in queries[:10]:
                content.append(f"- **{uc.command_or_query.name}** → `{uc.handler.name}`\n")
            content.append("\n")
    
    # Technology stack
    content.append("## 🛠️ Technology Stack\n\n")
    
    # Collect unique packages across all projects
    all_packages = {}
    for proj in solution.projects:
        for pkg in proj.package_references:
            if pkg.name not in all_packages:
                all_packages[pkg.name] = pkg.version or "N/A"
    
    # Show key packages
    key_packages = [
        name for name in all_packages.keys()
        if any(keyword in name for keyword in ["AspNetCore", "EntityFramework", "Mediator", "FastEndpoints", "Ardalis"])
    ]
    
    if key_packages:
        pkg_rows = [[name, all_packages[name]] for name in sorted(key_packages)[:15]]
        content.append(create_table(["Package", "Version"], pkg_rows))
        content.append("\n\n")
    
    # Write file
    output_path.write_text("\n".join(content), encoding="utf-8")
    logger.info(f"Generated SUMMARY.md")
    
    return output_path


def _get_project_type(proj: ProjectInfo) -> str:
    """Determine project type from its properties."""
    if proj.is_test_project:
        return "Test"
    elif proj.is_web_project:
        return "Web/API"
    elif "Infrastructure" in proj.name:
        return "Infrastructure"
    elif "Core" in proj.name or "Domain" in proj.name:
        return "Domain/Core"
    elif "UseCases" in proj.name or "Application" in proj.name:
        return "Application/UseCases"
    else:
        return "Library"
