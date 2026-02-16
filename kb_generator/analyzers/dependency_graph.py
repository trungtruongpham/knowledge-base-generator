"""Class-level dependency graph builder (Task 8.1).

Builds a directed graph of class relationships by analysing:
- Constructor injection parameters  → "injects" edges
- Base classes                      → "inherits" edges
- Implemented interfaces            → "implements" edges
- Command/Query → Handler pairings  → "handles"  edges
- Endpoint → Command dispatching    → "sends"    edges
"""

import logging
import re
from collections import defaultdict
from typing import Optional

from kb_generator.parsers.models import (
    ClassInfo,
    GraphNode,
    GraphEdge,
    ProjectInfo,
    SolutionInfo,
)
from kb_generator.analyzers.pattern_detector import PatternDetector

logger = logging.getLogger(__name__)


def _strip_generic(name: str) -> str:
    """Strip generic type parameters: 'IRepository<Contributor>' → 'IRepository'."""
    idx = name.find("<")
    return name[:idx] if idx != -1 else name


def _extract_generic_arg(name: str) -> Optional[str]:
    """Extract first generic type argument: 'IRepository<Contributor>' → 'Contributor'."""
    match = re.search(r"<\s*([^<>,\s]+)", name)
    return match.group(1) if match else None


def _classify_layer(project_name: str, cls: ClassInfo, detector: PatternDetector) -> str:
    """Classify a class into an architectural layer."""
    pn = project_name.lower()
    if any(k in pn for k in ("test", "spec")):
        return "Test"
    if any(k in pn for k in ("web", "api", "host", "server")):
        return "Web"
    if any(k in pn for k in ("infrastructure", "infra", "data", "persistence")):
        return "Infrastructure"
    if any(k in pn for k in ("usecase", "application", "usecases")):
        return "Application"
    if any(k in pn for k in ("core", "domain", "shared", "kernel")):
        return "Core"
    # Fallback: try to guess from patterns
    if detector.detect_endpoint(cls):
        return "Web"
    if detector.detect_handler(cls) or detector.detect_command(cls) or detector.detect_query(cls):
        return "Application"
    if detector.detect_aggregate_root(cls) or detector.detect_domain_event(cls):
        return "Core"
    if detector.detect_repository(cls) or detector.detect_ef_configuration(cls):
        return "Infrastructure"
    return "Other"


def _classify_role(cls: ClassInfo, detector: PatternDetector) -> str:
    """Classify a class into a role."""
    if detector.detect_endpoint(cls):
        return "endpoint"
    if detector.detect_command(cls):
        return "command"
    if detector.detect_query(cls):
        return "query"
    if detector.detect_handler(cls):
        return "handler"
    if detector.detect_repository(cls):
        return "repository"
    if detector.detect_aggregate_root(cls):
        return "entity"
    if detector.detect_ef_configuration(cls):
        return "config"
    if detector.detect_dto(cls):
        return "dto"
    if detector.detect_specification(cls):
        return "specification"
    if detector.detect_value_object(cls):
        return "value_object"
    if detector.detect_domain_event(cls):
        return "domain_event"
    if detector.detect_event_handler(cls):
        return "event_handler"
    if cls.class_kind == "interface":
        return "interface"
    return "other"


class DependencyGraph:
    """Directed graph of class-level dependencies."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.interface_map: dict[str, list[str]] = defaultdict(list)  # interface → [implementations]
        # Reverse index: target → list of edges pointing at it
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        # Forward index: source → list of edges going out
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
        # Short-name → set of full names (for fuzzy resolution)
        self._short_name_index: dict[str, set[str]] = defaultdict(set)

    # ──────── Graph construction ────────

    def add_node(self, cls: ClassInfo, role: str, project: str, layer: str) -> None:
        node = GraphNode(class_info=cls, role=role, project=project, layer=layer)
        self.nodes[cls.full_name] = node
        self._short_name_index[cls.name].add(cls.full_name)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)
        self._incoming[edge.target].append(edge)
        self._outgoing[edge.source].append(edge)

    # ──────── Resolution helpers ────────

    def resolve_name(self, short_name: str) -> list[str]:
        """Resolve a short class name to possible full names."""
        stripped = _strip_generic(short_name)
        return list(self._short_name_index.get(stripped, set()))

    def resolve_interface(self, interface_name: str) -> list[GraphNode]:
        """Resolve an interface to its implementation nodes."""
        stripped = _strip_generic(interface_name)
        results: list[GraphNode] = []
        for full_name in self.resolve_name(stripped):
            for impl_full in self.interface_map.get(full_name, []):
                node = self.nodes.get(impl_full)
                if node:
                    results.append(node)
        return results

    # ──────── Traversal ────────

    def get_dependents(self, class_name: str) -> list[GraphNode]:
        """Get classes that directly depend on the given class (incoming edges)."""
        result = []
        for edge in self._incoming.get(class_name, []):
            node = self.nodes.get(edge.source)
            if node:
                result.append(node)
        return result

    def get_dependencies(self, class_name: str) -> list[GraphNode]:
        """Get classes that the given class directly depends on (outgoing edges)."""
        result = []
        for edge in self._outgoing.get(class_name, []):
            node = self.nodes.get(edge.target)
            if node:
                result.append(node)
        return result

    def get_all_upstream(self, class_name: str, max_depth: int = 10) -> set[str]:
        """Get all transitive dependents (classes affected by changes to class_name)."""
        visited: set[str] = set()
        queue = [(class_name, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for edge in self._incoming.get(current, []):
                if edge.source not in visited:
                    queue.append((edge.source, depth + 1))
        visited.discard(class_name)
        return visited

    def get_all_downstream(self, class_name: str, max_depth: int = 10) -> set[str]:
        """Get all transitive dependencies."""
        visited: set[str] = set()
        queue = [(class_name, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for edge in self._outgoing.get(current, []):
                if edge.target not in visited:
                    queue.append((edge.target, depth + 1))
        visited.discard(class_name)
        return visited

    # ──────── Stats ────────

    def __repr__(self) -> str:
        return f"DependencyGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"


def build_dependency_graph(
    solution: SolutionInfo,
    all_classes: list[ClassInfo],
    detector: PatternDetector,
) -> DependencyGraph:
    """Build a complete class-level dependency graph.

    Args:
        solution: Parsed solution info (for project→class mapping)
        all_classes: All parsed ClassInfo objects
        detector: PatternDetector for role classification

    Returns:
        Populated DependencyGraph
    """
    graph = DependencyGraph()

    # ── Step 0: Build project membership lookup ──
    # Map file paths to project names
    file_to_project: dict[str, str] = {}
    for proj in solution.projects:
        for src in proj.source_files:
            file_to_project[src] = proj.name
        # Also infer from project path
        # e.g. Clean.Architecture.Core → anything under that directory
    
    def _project_for_class(cls: ClassInfo) -> str:
        """Find the project name for a class by checking file paths."""
        if cls.file_path in file_to_project:
            return file_to_project[cls.file_path]
        # Fallback: match by directory structure
        for proj in solution.projects:
            proj_dir = str(proj.path).replace("\\", "/")
            cls_path = cls.file_path.replace("\\", "/")
            if proj_dir and cls_path.startswith(proj_dir.rsplit("/", 1)[0] if "/" in proj_dir else ""):
                # Try more precise: project directory is parent of .csproj
                from pathlib import Path
                proj_parent = str(Path(proj.path).parent).replace("\\", "/")
                if cls_path.startswith(proj_parent):
                    return proj.name
        # Last resort: infer from namespace
        for proj in solution.projects:
            if proj.name.replace(".", "").lower() in cls.namespace.replace(".", "").lower():
                return proj.name
        return ""

    # ── Step 1: Add all classes as nodes ──
    for cls in all_classes:
        project = _project_for_class(cls)
        role = _classify_role(cls, detector)
        layer = _classify_layer(project, cls, detector)
        graph.add_node(cls, role=role, project=project, layer=layer)

    # ── Step 2: Build interface → implementation map ──
    for cls in all_classes:
        for iface in cls.interfaces:
            stripped = _strip_generic(iface)
            for full_name in graph.resolve_name(stripped):
                graph.interface_map[full_name].append(cls.full_name)

    # ── Step 3: Add edges ──
    for cls in all_classes:
        src = cls.full_name

        # 3a: Constructor injection → "injects"
        for ctor in cls.constructors:
            for param in ctor.parameters:
                _add_resolved_edge(graph, src, param.type_name, "injects",
                                   f"constructor param: {param.name}")

        # 3b: Base classes → "inherits"
        for base in cls.base_classes:
            _add_resolved_edge(graph, src, base, "inherits", f"extends {base}")

        # 3c: Interfaces → "implements"
        for iface in cls.interfaces:
            _add_resolved_edge(graph, src, iface, "implements", f"implements {iface}")

    # ── Step 4: Handler ↔ Command/Query edges ──
    handler_nodes = [n for n in graph.nodes.values() if n.role == "handler"]
    command_query_nodes = [n for n in graph.nodes.values() if n.role in ("command", "query")]
    cq_by_name = {n.class_info.name: n for n in command_query_nodes}

    for handler_node in handler_nodes:
        handler_name = handler_node.class_info.name
        # Convention: CreateContributorHandler → CreateContributorCommand / CreateContributorQuery
        for suffix in ("Command", "Query"):
            base = handler_name.replace("Handler", "")
            candidate = base + suffix
            if candidate in cq_by_name:
                cq_node = cq_by_name[candidate]
                graph.add_edge(GraphEdge(
                    source=handler_node.full_name,
                    target=cq_node.full_name,
                    edge_type="handles",
                    label=f"handles {candidate}",
                ))
                break
        # Also try matching via handler's generic interface args
        for iface in handler_node.class_info.interfaces:
            arg = _extract_generic_arg(iface)
            if arg and arg in cq_by_name:
                # Avoid duplicate
                already = any(
                    e.source == handler_node.full_name and
                    e.target == cq_by_name[arg].full_name and
                    e.edge_type == "handles"
                    for e in graph.edges
                )
                if not already:
                    graph.add_edge(GraphEdge(
                        source=handler_node.full_name,
                        target=cq_by_name[arg].full_name,
                        edge_type="handles",
                        label=f"handles {arg}",
                    ))

    # ── Step 5: Endpoint → Command/Query edges ("sends") ──
    endpoint_nodes = [n for n in graph.nodes.values() if n.role == "endpoint"]
    for ep_node in endpoint_nodes:
        ep = ep_node.class_info
        # Check constructor params for IMediator / mediator-like types
        # Also check for command/query types in constructor or base class generics
        for ctor in ep.constructors:
            for param in ctor.parameters:
                stripped = _strip_generic(param.type_name)
                if stripped in cq_by_name:
                    graph.add_edge(GraphEdge(
                        source=ep_node.full_name,
                        target=cq_by_name[stripped].full_name,
                        edge_type="sends",
                        label=f"dispatches {stripped}",
                    ))
        # FastEndpoints: check base class generic arg for request type → may link to command
        for base in ep.base_classes:
            arg = _extract_generic_arg(base)
            if arg:
                # Check if this arg's name matches a DTO that links to a command
                for cq_name, cq_node in cq_by_name.items():
                    # Heuristic: endpoint Request type often matches command/query name pattern
                    # e.g., CreateContributorRequest → CreateContributorCommand
                    base_name = arg.replace("Request", "")
                    if cq_name.startswith(base_name):
                        graph.add_edge(GraphEdge(
                            source=ep_node.full_name,
                            target=cq_node.full_name,
                            edge_type="sends",
                            label=f"dispatches {cq_name}",
                        ))

    logger.info(f"Built dependency graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    return graph


def _add_resolved_edge(graph: DependencyGraph, source: str, target_name: str,
                       edge_type: str, label: str) -> None:
    """Add an edge, resolving the target name to a full name if possible."""
    stripped = _strip_generic(target_name)
    candidates = graph.resolve_name(stripped)
    if candidates:
        for full in candidates:
            if full != source:  # No self-edges
                graph.add_edge(GraphEdge(source=source, target=full,
                                        edge_type=edge_type, label=label))
    # else: unresolved (external type) — skip silently
