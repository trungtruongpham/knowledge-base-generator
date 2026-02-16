"""Main pipeline orchestrating scan, analysis, and generation."""

import logging
from pathlib import Path

from kb_generator.parsers.solution_parser import parse_solution
from kb_generator.parsers.csproj_parser import parse_project, load_central_packages
from kb_generator.parsers.csharp_parser import parse_csharp_file
from kb_generator.parsers.models import SolutionInfo, ProjectInfo, ClassInfo, RequestFlow
from kb_generator.analyzers.pattern_detector import PatternDetector
from kb_generator.analyzers.dependency_graph import DependencyGraph, build_dependency_graph
from kb_generator.analyzers.flow_analyzer import analyze_flows
from kb_generator.analyzers.impact_analyzer import ImpactAnalyzer
from kb_generator.generators.summary_generator import generate_summary
from kb_generator.generators.flow_generator import generate_flow_docs
from kb_generator.generators.impact_generator import generate_impact_docs
from kb_generator.state.tracker import StateTracker
from kb_generator.state.models import KBState
from kb_generator.utils.file_utils import discover_solution_files, discover_project_files, discover_cs_files, ensure_dir
from kb_generator.utils.markdown_utils import get_timestamp

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────
# Shared helpers used by scan, update, and impact CLI
# ──────────────────────────────────────────────────────

def _parse_all_projects(solution: SolutionInfo, root: Path) -> None:
    """Parse all project files in the solution (mutates solution.projects in place)."""
    central_packages = load_central_packages(root)
    for project_info in solution.projects:
        proj_path = Path(project_info.path)
        if proj_path.exists():
            parsed = parse_project(proj_path, central_packages)
            if parsed:
                project_info.sdk = parsed.sdk
                project_info.target_framework = parsed.target_framework
                project_info.project_references = parsed.project_references
                project_info.package_references = parsed.package_references


def _parse_all_cs_files(root: Path) -> tuple[list[Path], list[ClassInfo]]:
    """Discover and parse all C# source files."""
    cs_files = discover_cs_files(root)
    logger.info(f"Found {len(cs_files)} C# files")

    all_classes: list[ClassInfo] = []
    for cs_file in cs_files:
        try:
            classes = parse_csharp_file(cs_file)
            all_classes.extend(classes)
        except Exception as e:
            logger.warning(f"Failed to parse {cs_file.name}: {e}")

    logger.info(f"Parsed {len(all_classes)} classes/types")
    return cs_files, all_classes


def _build_graph_and_flows(
    root: Path,
    solution: SolutionInfo,
    verbose: bool = False,
) -> tuple[DependencyGraph, list[RequestFlow], list[ClassInfo]]:
    """Build dependency graph and detect request flows.

    This is the shared heavy-lifting function used by both
    ``run_full_scan`` and the ``impact`` CLI command.

    Returns:
        (graph, flows, all_classes)
    """
    _parse_all_projects(solution, root)

    logger.info("📖 Parsing C# source files...")
    cs_files, all_classes = _parse_all_cs_files(root)

    logger.info("🔍 Analysing patterns and building dependency graph...")
    detector = PatternDetector()

    # Build dependency graph (Task 8.1)
    graph = build_dependency_graph(solution, all_classes, detector)

    # Trace request flows (Task 8.2)
    flows = analyze_flows(graph, detector)

    return graph, flows, all_classes


# ──────────────────────────────────────────────────────
# Pipeline commands
# ──────────────────────────────────────────────────────

def run_full_scan(root: Path, output_dir: str, verbose: bool = False) -> Path:
    """Run a full scan of a .NET project.

    Args:
        root: Root directory of the .NET project
        output_dir: Output directory name for KB files
        verbose: Enable verbose logging

    Returns:
        Path to generated KB directory
    """
    kb_path = root / output_dir
    ensure_dir(kb_path)

    logger.info("🔍 Starting full scan...")

    # Step 1: Parse solution
    solution = _parse_solution_or_projects(root)
    if not solution:
        raise ValueError("No .NET solution or projects found")

    logger.info(f"Found solution: {solution.name} with {len(solution.projects)} projects")

    # Step 2: Build graph + flows (this also parses projects and C# files)
    graph, flows, all_classes = _build_graph_and_flows(root, solution, verbose)

    # Step 3: Run pattern detection for aggregates and use cases
    detector = PatternDetector()
    aggregates = []
    for cls in all_classes:
        if detector.detect_aggregate_root(cls):
            agg = detector.find_aggregate(all_classes, cls)
            aggregates.append(agg)
    logger.info(f"Found {len(aggregates)} domain aggregates")

    use_cases = []
    for cls in all_classes:
        if detector.detect_command(cls) or detector.detect_query(cls):
            uc = detector.find_use_case(all_classes, cls)
            if uc:
                use_cases.append(uc)
    logger.info(f"Found {len(use_cases)} use cases")

    # Step 4: Generate KB files
    logger.info("📝 Generating knowledge base...")

    # SUMMARY.md
    summary_path = generate_summary(solution, all_classes, aggregates, use_cases, kb_path)

    # Flow documentation (Task 8.3)
    flow_paths = generate_flow_docs(flows, graph, kb_path)

    # Impact documentation (Task 9.3)
    impact_paths = generate_impact_docs(graph, flows, kb_path)

    # Step 5: Save state
    logger.info("💾 Saving state...")
    tracker = StateTracker(kb_path)
    state = KBState(last_full_scan=get_timestamp())

    cs_files = discover_cs_files(root)
    tracker.update_file_states(state, cs_files)

    # Track which sources contributed to each KB output
    source_paths = [str(f.resolve()) for f in cs_files]
    tracker.mark_kb_output(state, "SUMMARY.md", source_paths)
    for flow in flows:
        flow_file = f"flows/{flow.slug}.md"
        flow_sources = [s.file_path for s in flow.steps if s.file_path]
        tracker.mark_kb_output(state, flow_file, flow_sources)

    tracker.save_state(state)

    logger.info(f"✅ Full scan complete — {len(flow_paths)} flow docs, {len(impact_paths)} impact docs")
    return kb_path


def run_incremental_update(root: Path, output_dir: str, verbose: bool = False) -> Path:
    """Run an incremental update (only reprocess changed files).

    Uses the impact analyser (Task 9.4) to determine which KB
    documents need regeneration, instead of falling back to a
    full scan.

    Args:
        root: Root directory of the .NET project
        output_dir: Output directory name for KB files
        verbose: Enable verbose logging

    Returns:
        Path to KB directory
    """
    kb_path = root / output_dir

    logger.info("🔄 Starting incremental update...")

    # Load existing state
    tracker = StateTracker(kb_path)
    state = tracker.load_state()

    if not state:
        logger.warning("No existing state found, falling back to full scan")
        return run_full_scan(root, output_dir, verbose)

    # Find current files
    cs_files = discover_cs_files(root)

    # Compute changes
    changes = tracker.compute_changes(cs_files, state)

    if not changes.has_changes:
        logger.info("No changes detected")
        return kb_path

    logger.info(f"Processing {len(changes.all_changed)} changed file(s)...")

    # Build graph + flows on the full codebase (needed for accurate impact)
    solution = _parse_solution_or_projects(root)
    if not solution:
        raise ValueError("No .NET solution or projects found")

    graph, flows, all_classes = _build_graph_and_flows(root, solution, verbose)

    # Run impact analysis on changed files
    analyzer = ImpactAnalyzer(
        graph=graph,
        flows=flows,
        kb_outputs=state.kb_outputs,
    )
    report = analyzer.analyze_impact(changes.all_changed)

    logger.info(
        f"Impact: {report.total_impact_count} items affected, "
        f"risk={report.risk_level}"
    )

    # Determine which KB docs to regenerate
    docs_to_regen = {item.name for item in report.affected_kb_docs}
    docs_to_regen.add("SUMMARY.md")  # Always regenerate summary

    # Regenerate affected KB files
    detector = PatternDetector()

    # Always regenerate SUMMARY.md
    aggregates = [
        detector.find_aggregate(all_classes, cls)
        for cls in all_classes
        if detector.detect_aggregate_root(cls)
    ]
    use_cases = [
        uc for cls in all_classes
        if detector.detect_command(cls) or detector.detect_query(cls)
        for uc in [detector.find_use_case(all_classes, cls)]
        if uc
    ]
    generate_summary(solution, all_classes, aggregates, use_cases, kb_path)

    # Regenerate flow docs if any flow is affected
    affected_flow_slugs = {
        item.name.replace("flows/", "").replace(".md", "")
        for item in report.affected_kb_docs
        if item.name.startswith("flows/")
    }
    if affected_flow_slugs or any("flow" in d for d in docs_to_regen):
        generate_flow_docs(flows, graph, kb_path)

    # Regenerate impact docs
    generate_impact_docs(graph, flows, kb_path)

    # Update state
    new_state = KBState(
        last_full_scan=state.last_full_scan,
        last_update=get_timestamp(),
    )
    tracker.update_file_states(new_state, cs_files)
    source_paths = [str(f.resolve()) for f in cs_files]
    tracker.mark_kb_output(new_state, "SUMMARY.md", source_paths)
    for flow in flows:
        flow_file = f"flows/{flow.slug}.md"
        flow_sources = [s.file_path for s in flow.steps if s.file_path]
        tracker.mark_kb_output(new_state, flow_file, flow_sources)
    tracker.save_state(new_state)

    logger.info(f"✅ Incremental update complete — regenerated {len(docs_to_regen)} KB doc(s)")
    return kb_path


def run_refresh(root: Path, output_dir: str, verbose: bool = False) -> Path:
    """Force a full refresh (delete state and rescan).

    Args:
        root: Root directory of the .NET project
        output_dir: Output directory name for KB files
        verbose: Enable verbose logging

    Returns:
        Path to KB directory
    """
    kb_path = root / output_dir

    logger.info("🔄 Forcing full refresh...")

    # Delete state file if it exists
    tracker = StateTracker(kb_path)
    if tracker.state_path.exists():
        tracker.state_path.unlink()
        logger.info("Deleted existing state")

    # Run full scan
    return run_full_scan(root, output_dir, verbose)


def _parse_solution_or_projects(root: Path) -> SolutionInfo | None:
    """Find and parse solution, or create virtual solution from projects.

    Args:
        root: Root directory

    Returns:
        SolutionInfo or None
    """
    # Try to find solution file
    sln_files = discover_solution_files(root)
    if sln_files:
        return parse_solution(sln_files[0])

    # Fall back to discovering projects directly
    proj_files = discover_project_files(root)
    if proj_files:
        logger.info(f"No solution file found, creating virtual solution from {len(proj_files)} projects")
        solution = SolutionInfo(
            name=root.name,
            path=str(root),
        )
        for proj_path in proj_files:
            solution.projects.append(
                ProjectInfo(name=proj_path.stem, path=str(proj_path))
            )
        return solution

    return None
