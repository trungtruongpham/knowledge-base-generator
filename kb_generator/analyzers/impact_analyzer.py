"""Change impact analyzer (Task 9.1).

Given a set of changed files, predicts which flows, classes,
KB documents, and tests are affected.  Uses the dependency graph
for transitive impact analysis and computes a risk level.
"""

import logging
from pathlib import Path
from typing import Optional

from kb_generator.parsers.models import (
    ImpactedItem,
    ImpactReport,
    RequestFlow,
)
from kb_generator.analyzers.dependency_graph import DependencyGraph
from kb_generator.utils.markdown_utils import get_timestamp

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Analyzes the blast-radius of file changes."""

    def __init__(
        self,
        graph: DependencyGraph,
        flows: list[RequestFlow],
        test_map: Optional[dict[str, list[str]]] = None,
        kb_outputs: Optional[dict[str, list[str]]] = None,
    ):
        self.graph = graph
        self.flows = flows
        self.test_map = test_map or {}       # test_project → [src_projects]
        self.kb_outputs = kb_outputs or {}   # kb_file → [source_paths]

    def analyze_impact(
        self,
        changed_files: list[Path],
        max_depth: int = 5,
    ) -> ImpactReport:
        """Run impact analysis on a set of changed files.

        Args:
            changed_files: Paths that have been modified
            max_depth: Max depth for transitive dependency traversal

        Returns:
            Complete ImpactReport
        """
        report = ImpactReport(
            changed_files=[str(f) for f in changed_files],
            timestamp=get_timestamp(),
        )

        # 1. Find all classes defined in changed files
        changed_classes: set[str] = set()
        for f in changed_files:
            f_str = str(f.resolve()) if f.is_absolute() else str(f)
            for full_name, node in self.graph.nodes.items():
                # Match by file path (use endswith for flexibility)
                node_path = node.class_info.file_path.replace("\\", "/")
                f_path = f_str.replace("\\", "/")
                if node_path == f_path or node_path.endswith(f_path) or f_path.endswith(node_path):
                    changed_classes.add(full_name)

        if not changed_classes:
            logger.info("No matching classes found for changed files")
            return report

        logger.debug(f"Changed classes: {changed_classes}")

        # 2. Compute direct, indirect, and transitive impacts
        direct_impacts: set[str] = set()
        indirect_impacts: set[str] = set()
        transitive_impacts: set[str] = set()

        for cls_name in changed_classes:
            # Direct dependents (1 hop)
            for dep_node in self.graph.get_dependents(cls_name):
                if dep_node.full_name not in changed_classes:
                    direct_impacts.add(dep_node.full_name)

            # All upstream (transitive)
            all_upstream = self.graph.get_all_upstream(cls_name, max_depth=max_depth)
            for upstream_name in all_upstream:
                if upstream_name in changed_classes:
                    continue
                if upstream_name in direct_impacts:
                    continue
                node = self.graph.nodes.get(upstream_name)
                if not node:
                    continue
                # Classify as indirect (2 hops) or transitive (3+)
                # Check if any of this node's dependencies are in direct_impacts
                is_indirect = False
                for dep in self.graph.get_dependencies(upstream_name):
                    if dep.full_name in changed_classes:
                        is_indirect = True
                        break
                if is_indirect:
                    indirect_impacts.add(upstream_name)
                else:
                    transitive_impacts.add(upstream_name)

        # Build affected_classes list
        for cls_name in direct_impacts:
            node = self.graph.nodes.get(cls_name)
            if not node:
                continue
            reason = self._build_reason(cls_name, changed_classes, "direct")
            report.affected_classes.append(ImpactedItem(
                name=node.class_info.name,
                item_type="class",
                impact_level="direct",
                reason=reason,
                file_path=node.class_info.file_path,
            ))

        for cls_name in indirect_impacts:
            node = self.graph.nodes.get(cls_name)
            if not node:
                continue
            reason = self._build_reason(cls_name, changed_classes, "indirect")
            report.affected_classes.append(ImpactedItem(
                name=node.class_info.name,
                item_type="class",
                impact_level="indirect",
                reason=reason,
                file_path=node.class_info.file_path,
            ))

        for cls_name in transitive_impacts:
            node = self.graph.nodes.get(cls_name)
            if not node:
                continue
            report.affected_classes.append(ImpactedItem(
                name=node.class_info.name,
                item_type="class",
                impact_level="transitive",
                reason=f"Transitively depends on changed classes",
                file_path=node.class_info.file_path,
            ))

        # 3. Affected flows
        all_impacted = changed_classes | direct_impacts | indirect_impacts | transitive_impacts
        for flow in self.flows:
            flow_classes = {step.class_name for step in flow.steps}
            overlap = flow_classes & all_impacted
            if overlap:
                # Determine impact level from the most direct overlap
                if flow_classes & changed_classes:
                    level = "direct"
                elif flow_classes & direct_impacts:
                    level = "direct"
                elif flow_classes & indirect_impacts:
                    level = "indirect"
                else:
                    level = "transitive"

                report.affected_flows.append(ImpactedItem(
                    name=flow.name,
                    item_type="flow",
                    impact_level=level,
                    reason=f"Flow passes through: {', '.join(overlap)}",
                    file_path=f"flows/{flow.slug}.md",
                ))

        # 4. Affected endpoints
        for flow in self.flows:
            ep_steps = [s for s in flow.steps if s.role == "endpoint"]
            for ep_step in ep_steps:
                flow_classes = {step.class_name for step in flow.steps}
                if flow_classes & all_impacted:
                    report.affected_endpoints.append(ImpactedItem(
                        name=ep_step.class_name,
                        item_type="endpoint",
                        impact_level="indirect",
                        reason=f"Endpoint for flow: {flow.name} ({flow.entry_point})",
                        file_path=ep_step.file_path,
                    ))

        # Deduplicate endpoints
        seen_eps = set()
        deduped_eps = []
        for ep in report.affected_endpoints:
            if ep.name not in seen_eps:
                seen_eps.add(ep.name)
                deduped_eps.append(ep)
        report.affected_endpoints = deduped_eps

        # 5. Affected KB docs
        changed_file_strs = {str(f.resolve()).replace("\\", "/") for f in changed_files}
        for kb_file, source_files in self.kb_outputs.items():
            source_set = {s.replace("\\", "/") for s in source_files}
            if source_set & changed_file_strs:
                report.affected_kb_docs.append(ImpactedItem(
                    name=kb_file,
                    item_type="kb_doc",
                    impact_level="direct",
                    reason="Source files changed",
                    file_path=kb_file,
                ))

        # Also always include SUMMARY.md and affected flow docs
        if report.affected_flows:
            report.affected_kb_docs.append(ImpactedItem(
                name="SUMMARY.md",
                item_type="kb_doc",
                impact_level="direct",
                reason="Flows changed — summary may need update",
                file_path="SUMMARY.md",
            ))
            for flow_item in report.affected_flows:
                report.affected_kb_docs.append(ImpactedItem(
                    name=flow_item.file_path,
                    item_type="kb_doc",
                    impact_level=flow_item.impact_level,
                    reason=f"Flow '{flow_item.name}' affected",
                    file_path=flow_item.file_path,
                ))

        # Deduplicate KB docs
        seen_docs = set()
        deduped_docs = []
        for doc in report.affected_kb_docs:
            if doc.name not in seen_docs:
                seen_docs.add(doc.name)
                deduped_docs.append(doc)
        report.affected_kb_docs = deduped_docs

        # 6. Affected tests
        for cls_name in all_impacted | changed_classes:
            node = self.graph.nodes.get(cls_name)
            if not node:
                continue
            short_name = node.class_info.name
            # Heuristic: find test classes by name pattern
            for test_full, test_node in self.graph.nodes.items():
                if test_node.layer != "Test":
                    continue
                test_name = test_node.class_info.name
                # Match patterns like ContributorTests, ContributorHandlerTests, etc.
                if (short_name in test_name and
                    ("Test" in test_name or "Spec" in test_name)):
                    report.affected_tests.append(ImpactedItem(
                        name=test_name,
                        item_type="test",
                        impact_level="direct" if cls_name in changed_classes else "indirect",
                        reason=f"Tests class: {short_name}",
                        file_path=test_node.class_info.file_path,
                    ))

        # Deduplicate tests
        seen_tests = set()
        deduped_tests = []
        for t in report.affected_tests:
            if t.name not in seen_tests:
                seen_tests.add(t.name)
                deduped_tests.append(t)
        report.affected_tests = deduped_tests

        logger.info(
            f"Impact analysis: {report.total_impact_count} items affected, "
            f"risk={report.risk_level}"
        )
        return report

    def _build_reason(self, cls_name: str, changed_classes: set[str], level: str) -> str:
        """Build a human-readable reason for why a class is impacted."""
        node = self.graph.nodes.get(cls_name)
        if not node:
            return f"{level} dependency"

        # Find which changed class this depends on
        for dep in self.graph.get_dependencies(cls_name):
            if dep.full_name in changed_classes:
                # Find the edge type
                for edge in self.graph.edges:
                    if edge.source == cls_name and edge.target == dep.full_name:
                        return f"{edge.edge_type} {dep.class_info.name}"
        return f"{level} dependency on changed classes"
