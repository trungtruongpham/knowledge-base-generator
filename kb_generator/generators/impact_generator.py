"""Impact report Markdown generator (Task 9.3).

Generates:
  - impact/_index.md     — usage guide and risk level reference
  - impact/impact-map.md — per-file impact reference table
"""

import logging
from pathlib import Path

from kb_generator.parsers.models import ImpactReport, ImpactedItem
from kb_generator.analyzers.dependency_graph import DependencyGraph
from kb_generator.analyzers.flow_analyzer import analyze_flows
from kb_generator.analyzers.impact_analyzer import ImpactAnalyzer
from kb_generator.utils.markdown_utils import render_frontmatter, create_table, get_timestamp

logger = logging.getLogger(__name__)


def generate_impact_docs(
    graph: DependencyGraph,
    flows: list,
    output_dir: Path,
) -> list[Path]:
    """Generate static impact reference documentation.

    Args:
        graph: The dependency graph
        flows: Detected request flows
        output_dir: KB output directory

    Returns:
        List of generated file paths
    """
    impact_dir = output_dir / "impact"
    impact_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    idx_path = _generate_impact_index(impact_dir)
    generated.append(idx_path)

    map_path = _generate_impact_map(graph, flows, impact_dir)
    generated.append(map_path)

    logger.info(f"Generated {len(generated)} impact documentation files")
    return generated


def _generate_impact_index(impact_dir: Path) -> Path:
    """Generate the impact usage guide."""
    path = impact_dir / "_index.md"

    frontmatter = render_frontmatter({
        "title": "Change Impact Analysis",
        "type": "impact_guide",
        "generated_at": get_timestamp(),
    })

    content = f"""{frontmatter}
# 💥 Change Impact Analysis

## How to Use

1. **Before making changes:** Run `kb-gen impact --files <path>` to preview blast radius
2. **After making changes:** Run `kb-gen impact --git-diff` to see what's affected
3. **In CI/CD:** Run `kb-gen impact --git-staged` in pre-commit hook

## CLI Commands

```bash
# Analyze impact of changing a single file
kb-gen impact ./MyProject --files src/Core/Entity.cs

# Analyze impact of multiple files
kb-gen impact ./MyProject --files src/Core/Entity.cs src/UseCases/Handler.cs

# Analyze all uncommitted changes
kb-gen impact ./MyProject --git-diff

# Analyze staged changes
kb-gen impact ./MyProject --git-staged

# Save report as Markdown file
kb-gen impact ./MyProject --git-diff --output report.md
```

## Risk Levels

| Level | Meaning | Action |
|-------|---------|--------|
| 🟢 Low | Leaf node change (endpoint, test, config) | Minimal review needed |
| 🟡 Medium | Affects 1-2 flows | Review affected flows |
| 🟠 High | Affects 3+ flows, core service | Thorough review + run affected tests |
| 🔴 Critical | Core entity/shared service, affects 5+ flows | Full test suite + team review |

## Impact Levels

| Level | Meaning |
|-------|---------|
| **Direct** | Class directly references or inherits from the changed class |
| **Indirect** | Class is 2 hops away in the dependency graph |
| **Transitive** | Class is 3+ hops away |

## See Also

- [Impact Map](impact-map.md) — Per-file impact reference
- [Request Flows](../flows/_index.md) — All detected request flows
- [Dependency Graph](../flows/_dependency-graph.md) — Full class dependency visualization
"""

    path.write_text(content, encoding="utf-8")
    logger.debug("Generated impact/_index.md")
    return path


def _generate_impact_map(
    graph: DependencyGraph,
    flows: list,
    impact_dir: Path,
) -> Path:
    """Generate the per-file impact reference map."""
    path = impact_dir / "impact-map.md"

    frontmatter = render_frontmatter({
        "title": "Impact Map",
        "type": "impact_map",
        "generated_at": get_timestamp(),
    })

    lines = [frontmatter]
    lines.append("# 💥 Impact Map\n")
    lines.append("> For each significant source file, shows what would be affected if it changes.")
    lines.append("> Run `kb-gen impact --files <path>` for live, up-to-date analysis.\n")

    # Group nodes by layer, then compute impact for key classes
    layers_order = ["Core", "Application", "Infrastructure", "Web"]
    layer_risk = {"Core": "High", "Application": "Medium", "Infrastructure": "Medium", "Web": "Low"}

    for layer_name in layers_order:
        layer_nodes = [
            n for n in graph.nodes.values()
            if n.layer == layer_name and n.role not in ("other", "interface", "dto")
        ]
        if not layer_nodes:
            continue

        lines.append(f"\n## {layer_name} Layer ({layer_risk.get(layer_name, 'Medium')} Impact)\n")

        for node in sorted(layer_nodes, key=lambda n: n.class_info.name)[:20]:  # Limit per layer
            cls = node.class_info
            upstream = graph.get_all_upstream(cls.full_name, max_depth=3)
            upstream_nodes = [graph.nodes[u] for u in upstream if u in graph.nodes]

            # Find flows that include this class
            affected_flows = [
                f for f in flows
                if any(s.class_name == cls.full_name for s in f.steps)
            ]

            # Find direct dependents
            dependents = graph.get_dependents(cls.full_name)

            if not upstream_nodes and not affected_flows and not dependents:
                continue  # Skip isolated nodes

            lines.append(f"### {cls.name}\n")
            lines.append(f"**File:** `{cls.file_path}`  ")
            lines.append(f"**Role:** {node.role}  ")
            lines.append(f"**Layer:** {node.layer}\n")

            rows = []
            if dependents:
                dep_names = ", ".join(d.class_info.name for d in dependents[:8])
                rows.append(["Classes", dep_names, "Direct"])
            if affected_flows:
                flow_names = ", ".join(f.name for f in affected_flows[:8])
                rows.append(["Flows", flow_names, "Direct"])

            # Count upstream for risk
            flow_count = len(affected_flows)
            if flow_count >= 5:
                risk = "🔴 **CRITICAL**"
            elif flow_count >= 3:
                risk = "🟠 **HIGH**"
            elif flow_count >= 1:
                risk = "🟡 **MEDIUM**"
            else:
                risk = "🟢 **LOW**"

            rows.append(["Risk", risk, f"{flow_count} flow(s) affected"])

            if rows:
                lines.append(create_table(["Impact Type", "Affected", "Level"], rows))
                lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug("Generated impact/impact-map.md")
    return path


def format_impact_report_terminal(report: ImpactReport) -> str:
    """Format an impact report for terminal output.

    Args:
        report: The impact report to format

    Returns:
        Formatted string for terminal display
    """
    lines = []
    lines.append(f"\n🔍 Impact Analysis for {len(report.changed_files)} changed file(s)")
    lines.append("━" * 50)

    # Changed files
    for f in report.changed_files:
        lines.append(f"\n📄 Changed: {f}")

    # Risk level
    risk_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    risk_icon = risk_icons.get(report.risk_level, "⚪")
    lines.append(f"\n⚠️  Risk Level: {risk_icon} {report.risk_level.upper()}")

    # Affected classes
    if report.affected_classes:
        lines.append(f"\n🔗 Affected Classes ({len(report.affected_classes)}):")
        for i, item in enumerate(report.affected_classes):
            connector = "└──" if i == len(report.affected_classes) - 1 else "├──"
            lines.append(f"   {connector} {item.impact_level.upper()}: {item.name} ({item.reason})")

    # Affected flows
    if report.affected_flows:
        lines.append(f"\n🔄 Affected Flows ({len(report.affected_flows)}):")
        for i, item in enumerate(report.affected_flows):
            connector = "└──" if i == len(report.affected_flows) - 1 else "├──"
            lines.append(f"   {connector} {item.name}")

    # Affected KB docs
    if report.affected_kb_docs:
        lines.append(f"\n📝 KB Docs to Regenerate ({len(report.affected_kb_docs)}):")
        for i, item in enumerate(report.affected_kb_docs):
            connector = "└──" if i == len(report.affected_kb_docs) - 1 else "├──"
            lines.append(f"   {connector} {item.name}")

    # Affected tests
    if report.affected_tests:
        lines.append(f"\n🧪 Tests Likely Affected ({len(report.affected_tests)}):")
        for i, item in enumerate(report.affected_tests):
            connector = "└──" if i == len(report.affected_tests) - 1 else "├──"
            lines.append(f"   {connector} {item.name} ({item.file_path})")

    # Affected endpoints
    if report.affected_endpoints:
        lines.append(f"\n🌐 Affected Endpoints ({len(report.affected_endpoints)}):")
        for i, item in enumerate(report.affected_endpoints):
            connector = "└──" if i == len(report.affected_endpoints) - 1 else "├──"
            lines.append(f"   {connector} {item.reason}")

    if report.total_impact_count == 0:
        lines.append("\n✅ No impact detected — change appears isolated")

    lines.append("")
    return "\n".join(lines)


def format_impact_report_markdown(report: ImpactReport) -> str:
    """Format an impact report as Markdown (for --output flag).

    Args:
        report: The impact report to format

    Returns:
        Markdown content
    """
    frontmatter = render_frontmatter({
        "title": "Impact Analysis Report",
        "type": "impact_report",
        "risk_level": report.risk_level,
        "generated_at": report.timestamp,
    })

    lines = [frontmatter]
    lines.append("# 💥 Impact Analysis Report\n")
    lines.append(f"> Risk Level: **{report.risk_level.upper()}**\n")

    lines.append("## Changed Files\n")
    for f in report.changed_files:
        lines.append(f"- `{f}`")
    lines.append("")

    if report.affected_classes:
        lines.append(f"## Affected Classes ({len(report.affected_classes)})\n")
        rows = [[i.name, i.impact_level, i.reason] for i in report.affected_classes]
        lines.append(create_table(["Class", "Level", "Reason"], rows))
        lines.append("")

    if report.affected_flows:
        lines.append(f"## Affected Flows ({len(report.affected_flows)})\n")
        rows = [[i.name, i.impact_level, i.file_path] for i in report.affected_flows]
        lines.append(create_table(["Flow", "Level", "Doc"], rows))
        lines.append("")

    if report.affected_kb_docs:
        lines.append(f"## KB Docs to Regenerate ({len(report.affected_kb_docs)})\n")
        for doc in report.affected_kb_docs:
            lines.append(f"- `{doc.name}`")
        lines.append("")

    if report.affected_tests:
        lines.append(f"## Tests Likely Affected ({len(report.affected_tests)})\n")
        for t in report.affected_tests:
            lines.append(f"- `{t.name}` — {t.file_path}")
        lines.append("")

    return "\n".join(lines)
