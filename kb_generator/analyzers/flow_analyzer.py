"""Request flow tracer (Task 8.2).

Traces complete request flows through the codebase:
  Endpoint → Command/Query → Handler → Repository → Entity

Uses the DependencyGraph to follow DI chains and resolve
interface → implementation links.
"""

import logging
import re
from typing import Optional

from kb_generator.parsers.models import (
    ClassInfo,
    FlowStep,
    RequestFlow,
    GraphNode,
)
from kb_generator.analyzers.dependency_graph import DependencyGraph, _strip_generic, _extract_generic_arg
from kb_generator.analyzers.pattern_detector import PatternDetector

logger = logging.getLogger(__name__)


def _derive_flow_name(cq_name: str) -> str:
    """Derive a human-readable flow name from a command/query class name.

    CreateContributorCommand  → "Create Contributor"
    GetContributorByIdQuery   → "Get Contributor By Id"
    ListContributorsQuery     → "List Contributors"
    """
    # Strip Command / Query suffix
    base = cq_name
    for suffix in ("Command", "Query"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    # Split PascalCase into words
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", words)
    return words.strip()


def _derive_http_method(flow_name: str, cq_role: str) -> str:
    """Guess the HTTP method from the flow name and command/query role."""
    lower = flow_name.lower()
    if cq_role == "query":
        return "GET"
    if lower.startswith("create") or lower.startswith("add") or lower.startswith("register"):
        return "POST"
    if lower.startswith("update") or lower.startswith("edit") or lower.startswith("modify"):
        return "PUT"
    if lower.startswith("delete") or lower.startswith("remove"):
        return "DELETE"
    if lower.startswith("list") or lower.startswith("get") or lower.startswith("find"):
        return "GET"
    return "POST"  # default for commands


def _derive_route(endpoint_node: Optional[GraphNode], flow_name: str) -> str:
    """Try to extract the route from the endpoint class or guess from the flow name."""
    if endpoint_node:
        ep = endpoint_node.class_info
        # FastEndpoints: look for Configure() method with route setting
        # For now, use class attributes or name-based heuristic
        for attr in ep.attributes:
            if "Route" in attr or "Http" in attr:
                return attr
        # Convention: endpoint class name often embeds entity
        # e.g., "CreateContributorEndpoint" → "/api/Contributors"
    # Fallback: derive from flow name
    parts = flow_name.split()
    if len(parts) >= 2:
        entity = parts[-1]
        # Simple pluralisation
        if not entity.endswith("s"):
            entity += "s"
        return f"/api/{entity}"
    return "/api/unknown"


def analyze_flows(
    graph: DependencyGraph,
    detector: PatternDetector,
) -> list[RequestFlow]:
    """Trace all request flows through the codebase.

    Algorithm:
      1. Find all Command/Query nodes
      2. For each, find the matching Handler (via "handles" edges)
      3. For each Handler, try to find the Endpoint that dispatches it (via "sends" edges from endpoints)
      4. Follow DI chain from Handler → Repository → Entity

    Returns:
        List of detected RequestFlow objects
    """
    flows: list[RequestFlow] = []

    # Index: command/query full_name → handler node
    cq_to_handler: dict[str, GraphNode] = {}
    for edge in graph.edges:
        if edge.edge_type == "handles":
            handler_node = graph.nodes.get(edge.source)
            cq_node = graph.nodes.get(edge.target)
            if handler_node and cq_node:
                cq_to_handler[edge.target] = handler_node

    # Index: command/query full_name → endpoint node that sends it
    cq_to_endpoint: dict[str, GraphNode] = {}
    for edge in graph.edges:
        if edge.edge_type == "sends":
            ep_node = graph.nodes.get(edge.source)
            cq_node = graph.nodes.get(edge.target)
            if ep_node and cq_node:
                cq_to_endpoint[edge.target] = ep_node

    # Find command/query nodes
    cq_nodes = [n for n in graph.nodes.values() if n.role in ("command", "query")]

    for cq_node in cq_nodes:
        cq_cls = cq_node.class_info
        cq_full = cq_node.full_name
        flow_name = _derive_flow_name(cq_cls.name)
        http_method = _derive_http_method(flow_name, cq_node.role)

        steps: list[FlowStep] = []

        # Step 1: Endpoint (if found)
        ep_node = cq_to_endpoint.get(cq_full)
        if ep_node:
            route = _derive_route(ep_node, flow_name)
            steps.append(FlowStep(
                class_name=ep_node.full_name,
                role="endpoint",
                action=f"receives HTTP {http_method}",
                file_path=ep_node.class_info.file_path,
                project=ep_node.project,
                layer=ep_node.layer,
            ))
        else:
            route = _derive_route(None, flow_name)

        # Step 2: Command/Query itself
        steps.append(FlowStep(
            class_name=cq_full,
            role=cq_node.role,
            action=f"CQRS {cq_node.role} message",
            file_path=cq_cls.file_path,
            project=cq_node.project,
            layer=cq_node.layer,
        ))

        # Step 3: Handler
        handler_node = cq_to_handler.get(cq_full)
        aggregate_name: Optional[str] = None
        side_effects: list[str] = []
        cross_cutting: list[str] = []

        if handler_node:
            handler_cls = handler_node.class_info
            steps.append(FlowStep(
                class_name=handler_node.full_name,
                role="handler",
                action=f"handles {cq_node.role}",
                file_path=handler_cls.file_path,
                project=handler_node.project,
                layer=handler_node.layer,
            ))

            # Step 4: Follow handler's DI dependencies
            for ctor in handler_cls.constructors:
                for param in ctor.parameters:
                    param_stripped = _strip_generic(param.type_name)
                    generic_arg = _extract_generic_arg(param.type_name)

                    # Repository dependency
                    if "repository" in param_stripped.lower():
                        # Find the entity (generic arg)
                        if generic_arg:
                            entity_candidates = graph.resolve_name(generic_arg)
                            for entity_full in entity_candidates:
                                entity_node = graph.nodes.get(entity_full)
                                if entity_node and entity_node.role in ("entity", "other"):
                                    aggregate_name = entity_node.class_info.name

                        # Add repository step
                        impl_nodes = graph.resolve_interface(param.type_name)
                        repo_label = param.type_name
                        if impl_nodes:
                            impl = impl_nodes[0]
                            repo_label = impl.full_name
                        steps.append(FlowStep(
                            class_name=repo_label,
                            role="repository",
                            action=f"persists/retrieves data",
                            file_path=impl_nodes[0].class_info.file_path if impl_nodes else "",
                            project=impl_nodes[0].project if impl_nodes else "",
                            layer=impl_nodes[0].layer if impl_nodes else "Infrastructure",
                        ))

                        # Also add the entity if we found it
                        if generic_arg:
                            for entity_full in graph.resolve_name(generic_arg):
                                entity_node = graph.nodes.get(entity_full)
                                if entity_node:
                                    steps.append(FlowStep(
                                        class_name=entity_full,
                                        role="entity",
                                        action="domain entity",
                                        file_path=entity_node.class_info.file_path,
                                        project=entity_node.project,
                                        layer=entity_node.layer,
                                    ))
                                    break

                    # Service / other dependency — just note it
                    elif "mediator" not in param_stripped.lower() and "logger" not in param_stripped.lower():
                        # Check for validators, pipeline behaviors
                        if "validator" in param_stripped.lower():
                            cross_cutting.append(f"Validator: {param.type_name}")
                        elif "behavior" in param_stripped.lower() or "pipeline" in param_stripped.lower():
                            cross_cutting.append(f"Pipeline: {param.type_name}")

            # Detect side effects from handler methods or body heuristics
            for method in handler_cls.methods:
                method_lower = method.name.lower()
                if "event" in method_lower or "notify" in method_lower or "publish" in method_lower:
                    side_effects.append(f"Raises event via {method.name}()")

        entry_point = f"{http_method} {route}"

        flow = RequestFlow(
            name=flow_name,
            entry_point=entry_point,
            http_method=http_method,
            steps=steps,
            command_or_query=cq_cls.name,
            aggregate=aggregate_name,
            side_effects=side_effects,
            cross_cutting=cross_cutting,
        )
        flows.append(flow)

    # Detect cross-cutting validators by matching "XxxValidator" to "XxxCommand"/"XxxQuery"
    validator_nodes = [n for n in graph.nodes.values()
                       if n.class_info.name.endswith("Validator")]
    for v_node in validator_nodes:
        v_name = v_node.class_info.name
        # Strip "Validator" suffix to get base name
        base = v_name.replace("Validator", "")
        for flow in flows:
            cq_base = flow.command_or_query.replace("Command", "").replace("Query", "")
            if base == cq_base:
                flow.cross_cutting.append(f"FluentValidation: {v_name}")

    logger.info(f"Detected {len(flows)} request flows")
    return flows
