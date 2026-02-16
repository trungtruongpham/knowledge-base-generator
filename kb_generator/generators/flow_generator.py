"""Flow documentation generator (Task 8.3).

Generates:
  - flows/_index.md        — table of all flows
  - flows/<slug>.md        — per-flow Mermaid sequence diagram + step table
  - flows/_dependency-graph.md — full class dependency visualization
"""

import logging
from pathlib import Path

from kb_generator.parsers.models import RequestFlow, FlowStep
from kb_generator.analyzers.dependency_graph import DependencyGraph
from kb_generator.utils.markdown_utils import render_frontmatter, create_table, get_timestamp

logger = logging.getLogger(__name__)


def _mermaid_safe(name: str) -> str:
    """Make a class name safe for Mermaid diagrams."""
    return name.replace("<", "_").replace(">", "").replace(".", "_").replace(",", "_")


def _short_name(full_name: str) -> str:
    """Get the short class name from a full name."""
    return full_name.rsplit(".", 1)[-1] if "." in full_name else full_name


def generate_flow_docs(
    flows: list[RequestFlow],
    graph: DependencyGraph,
    output_dir: Path,
) -> list[Path]:
    """Generate all flow documentation.

    Args:
        flows: Detected request flows
        graph: The dependency graph
        output_dir: KB output directory

    Returns:
        List of generated file paths
    """
    flows_dir = output_dir / "flows"
    flows_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    # Generate per-flow files
    for flow in flows:
        path = _generate_flow_file(flow, flows_dir, graph)
        generated.append(path)

    # Generate index
    idx_path = _generate_flow_index(flows, flows_dir)
    generated.append(idx_path)

    # Generate dependency graph
    dep_path = _generate_dependency_graph_doc(graph, flows_dir)
    generated.append(dep_path)

    logger.info(f"Generated {len(generated)} flow documentation files")
    return generated


def _generate_flow_file(flow: RequestFlow, flows_dir: Path, graph: DependencyGraph) -> Path:
    """Generate a single flow documentation file with Mermaid diagram."""
    path = flows_dir / f"{flow.slug}.md"

    frontmatter = render_frontmatter({
        "title": flow.name,
        "flow_type": "Command" if flow.command_or_query.endswith("Command") else "Query",
        "http_method": flow.http_method,
        "route": flow.entry_point.split(" ", 1)[-1] if " " in flow.entry_point else "",
        "aggregate": flow.aggregate or "N/A",
        "generated_at": get_timestamp(),
    })

    lines = [frontmatter]
    lines.append(f"# {flow.name}\n")
    lines.append(f"> **{flow.entry_point}**\n")

    # ── Mermaid Sequence Diagram ──
    lines.append("## 🔄 Sequence Diagram\n")
    lines.append("```mermaid")
    lines.append("sequenceDiagram")

    # Deduplicate participants while preserving order
    seen_participants = []
    for step in flow.steps:
        short = _short_name(step.class_name)
        safe = _mermaid_safe(step.class_name)
        label = f"    participant {safe} as {short}"
        if label not in seen_participants:
            seen_participants.append(label)

    for p in seen_participants:
        lines.append(p)

    lines.append("")

    # Draw arrows between consecutive steps
    for i in range(len(flow.steps) - 1):
        src = _mermaid_safe(flow.steps[i].class_name)
        tgt = _mermaid_safe(flow.steps[i + 1].class_name)
        action = flow.steps[i + 1].action
        lines.append(f"    {src}->>{tgt}: {action}")

    # Return arrow from last to first
    if len(flow.steps) >= 2:
        last = _mermaid_safe(flow.steps[-1].class_name)
        first = _mermaid_safe(flow.steps[0].class_name)
        lines.append(f"    {last}-->>{first}: response")

    lines.append("```\n")

    # ── Flow Steps Table ──
    lines.append("## 📋 Flow Steps\n")
    step_rows = []
    for i, step in enumerate(flow.steps, 1):
        step_rows.append([
            str(i),
            step.layer,
            f"`{_short_name(step.class_name)}`",
            step.action,
            step.file_path.rsplit("/", 2)[-2:] if "/" in step.file_path else [step.file_path],
        ])
    step_rows_str = [
        [r[0], r[1], r[2], r[3], "/".join(r[4]) if isinstance(r[4], list) else r[4]]
        for r in step_rows
    ]
    lines.append(create_table(
        ["#", "Layer", "Class", "Action", "File"],
        step_rows_str,
    ))
    lines.append("\n")

    # ── Dependencies ──
    if flow.steps:
        lines.append("## 🔗 Dependencies\n")
        handler_steps = [s for s in flow.steps if s.role == "handler"]
        if handler_steps:
            handler_node = graph.nodes.get(handler_steps[0].class_name)
            if handler_node:
                for ctor in handler_node.class_info.constructors:
                    for param in ctor.parameters:
                        lines.append(f"- `{param.type_name}` — injected as `{param.name}`")
        lines.append("")

    # ── Side Effects ──
    if flow.side_effects:
        lines.append("## ⚡ Side Effects\n")
        for se in flow.side_effects:
            lines.append(f"- {se}")
        lines.append("")

    # ── Cross-Cutting ──
    if flow.cross_cutting:
        lines.append("## 🛡️ Cross-Cutting\n")
        for cc in flow.cross_cutting:
            lines.append(f"- {cc}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug(f"Generated flow doc: {path.name}")
    return path


def _generate_flow_index(flows: list[RequestFlow], flows_dir: Path) -> Path:
    """Generate the flows/_index.md file."""
    path = flows_dir / "_index.md"

    frontmatter = render_frontmatter({
        "title": "Request Flows Index",
        "type": "flow_index",
        "generated_at": get_timestamp(),
    })

    lines = [frontmatter]
    lines.append("# 🔄 Request Flows\n")
    lines.append(f"> **{len(flows)} flows** detected in the codebase\n")

    # Group by aggregate
    by_aggregate: dict[str, list[RequestFlow]] = {}
    for flow in flows:
        agg = flow.aggregate or "Other"
        by_aggregate.setdefault(agg, []).append(flow)

    for agg_name, agg_flows in sorted(by_aggregate.items()):
        lines.append(f"\n## {agg_name}\n")

        rows = []
        for flow in sorted(agg_flows, key=lambda f: f.name):
            link = f"[{flow.name}]({flow.slug}.md)"
            rows.append([
                link,
                flow.http_method,
                flow.entry_point.split(" ", 1)[-1] if " " in flow.entry_point else "",
                flow.command_or_query,
                str(len(flow.steps)),
            ])

        lines.append(create_table(
            ["Flow", "Method", "Route", "Command/Query", "Steps"],
            rows,
        ))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug("Generated flows/_index.md")
    return path


def _generate_dependency_graph_doc(graph: DependencyGraph, flows_dir: Path) -> Path:
    """Generate flows/_dependency-graph.md with Mermaid flowchart."""
    path = flows_dir / "_dependency-graph.md"

    frontmatter = render_frontmatter({
        "title": "Class Dependency Graph",
        "type": "dependency_graph",
        "generated_at": get_timestamp(),
    })

    lines = [frontmatter]
    lines.append("# 🕸️ Class Dependency Graph\n")
    lines.append(f"> **{len(graph.nodes)} classes**, **{len(graph.edges)} relationships**\n")

    # Build Mermaid flowchart — group by layer
    lines.append("```mermaid")
    lines.append("flowchart TD")

    # Group nodes by layer
    layers = {"Web": [], "Application": [], "Core": [], "Infrastructure": [], "Test": [], "Other": []}
    for full_name, node in graph.nodes.items():
        bucket = node.layer if node.layer in layers else "Other"
        layers[bucket].append(node)

    # Only render layers that have interesting nodes (not "other" role)
    for layer_name, layer_nodes in layers.items():
        interesting = [n for n in layer_nodes if n.role not in ("other", "interface", "dto")]
        if not interesting:
            continue

        safe_layer = layer_name.replace(" ", "_")
        lines.append(f"    subgraph {safe_layer}[\"{layer_name} Layer\"]")
        for node in interesting[:30]:  # Limit per layer to avoid giant diagrams
            safe_name = _mermaid_safe(node.full_name)
            short = _short_name(node.full_name)
            role_icon = {
                "endpoint": "🌐", "command": "📨", "query": "📩",
                "handler": "⚙️", "repository": "💾", "entity": "🏛️",
                "service": "🔧", "config": "⚙️", "specification": "📋",
                "value_object": "💎", "domain_event": "⚡",
            }.get(node.role, "📦")
            lines.append(f"        {safe_name}[\"{role_icon} {short}\"]")
        lines.append("    end")

    lines.append("")

    # Add edges (limit to avoid unreadable diagrams)
    edge_count = 0
    for edge in graph.edges:
        if edge.edge_type in ("injects", "handles", "sends") and edge_count < 100:
            src = _mermaid_safe(edge.source)
            tgt = _mermaid_safe(edge.target)
            # Only add edge if both nodes exist in diagram
            style = {
                "injects": "-->",
                "handles": "==>",
                "sends": "-.->",
                "inherits": "--o",
                "implements": "--x",
            }.get(edge.edge_type, "-->")
            lines.append(f"    {src} {style}|{edge.edge_type}| {tgt}")
            edge_count += 1

    lines.append("```\n")

    # Legend
    lines.append("## Legend\n")
    lines.append("| Symbol | Meaning |")
    lines.append("|--------|---------|")
    lines.append("| `-->` | Injects (DI) |")
    lines.append("| `==>` | Handles (CQRS) |")
    lines.append("| `-.->` | Sends (dispatches) |")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.debug("Generated flows/_dependency-graph.md")
    return path
