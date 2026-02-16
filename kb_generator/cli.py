"""CLI interface for KB Generator."""

import logging
from pathlib import Path
import sys

import click

from kb_generator import __version__


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """Generate LLM-friendly knowledge bases from .NET/C# projects."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=str,
    default=".kb",
    help="Output directory for KB files (default: .kb)",
)
@click.pass_context
def scan(ctx, path: Path, output_dir: str):
    """Perform full initial scan of a .NET project and generate knowledge base.
    
    PATH: Path to .NET solution or project directory
    """
    verbose = ctx.obj.get("verbose", False)
    
    logger.info(f"Starting full scan of: {path}")
    logger.info(f"Output directory: {output_dir}")
    
    # Validate path contains .NET project files
    if not _has_dotnet_files(path):
        logger.error("No .NET solution or project files found in the specified path")
        logger.error("Expected: *.sln, *.slnx, or *.csproj files")
        sys.exit(1)
    
    # Import here to avoid slow startup for --help
    from kb_generator.pipeline import run_full_scan
    
    try:
        kb_path = run_full_scan(path, output_dir, verbose)
        logger.info(f"✅ Knowledge base generated at: {kb_path}")
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=str,
    default=".kb",
    help="Output directory for KB files (default: .kb)",
)
@click.pass_context
def update(ctx, path: Path, output_dir: str):
    """Incrementally update the knowledge base (only re-process changed files).
    
    PATH: Path to .NET solution or project directory
    """
    verbose = ctx.obj.get("verbose", False)
    
    logger.info(f"Starting incremental update of: {path}")
    
    # Import here to avoid slow startup
    from kb_generator.pipeline import run_incremental_update
    
    try:
        kb_path = run_incremental_update(path, output_dir, verbose)
        logger.info(f"✅ Knowledge base updated at: {kb_path}")
    except Exception as e:
        logger.error(f"Update failed: {e}")
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    "-o",
    type=str,
    default=".kb",
    help="Output directory for KB files (default: .kb)",
)
@click.pass_context
def refresh(ctx, path: Path, output_dir: str):
    """Force full re-scan (deletes state and regenerates everything).
    
    PATH: Path to .NET solution or project directory
    """
    verbose = ctx.obj.get("verbose", False)
    
    logger.info(f"Forcing full refresh of: {path}")
    
    # Import here to avoid slow startup
    from kb_generator.pipeline import run_refresh
    
    try:
        kb_path = run_refresh(path, output_dir, verbose)
        logger.info(f"✅ Knowledge base refreshed at: {kb_path}")
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        if verbose:
            raise
        sys.exit(1)


def _has_dotnet_files(path: Path) -> bool:
    """Check if path contains .NET project files."""
    if path.is_file():
        return path.suffix in {".sln", ".slnx", ".csproj"}
    
    # Check directory
    for pattern in ["*.sln", "*.slnx", "*.csproj"]:
        if list(path.glob(pattern)):
            return True
    
    return False


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--files",
    "-f",
    multiple=True,
    type=str,
    help="File(s) to analyze impact for (relative to project root)",
)
@click.option(
    "--git-diff",
    is_flag=True,
    help="Auto-detect changed files from git diff",
)
@click.option(
    "--git-staged",
    is_flag=True,
    help="Auto-detect changed files from git diff --staged",
)
@click.option(
    "--output",
    "-o",
    type=str,
    default=None,
    help="Write report to a Markdown file instead of terminal",
)
@click.option(
    "--depth",
    "-d",
    type=int,
    default=5,
    help="Max transitive dependency depth (default: 5)",
)
@click.pass_context
def impact(ctx, path: Path, files: tuple, git_diff: bool, git_staged: bool,
           output: str | None, depth: int):
    """Analyze the impact of file changes on flows, classes, and tests.

    PATH: Path to .NET solution or project directory
    """
    verbose = ctx.obj.get("verbose", False)

    if not files and not git_diff and not git_staged:
        logger.error("Must specify --files, --git-diff, or --git-staged")
        sys.exit(1)

    # Resolve changed files
    changed_files: list[Path] = []
    if files:
        for f in files:
            fp = path / f
            if fp.exists():
                changed_files.append(fp)
            else:
                logger.warning(f"File not found: {fp}")
    if git_diff or git_staged:
        import subprocess
        cmd = ["git", "diff", "--name-only"]
        if git_staged:
            cmd.append("--staged")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(path)
            )
            for line in result.stdout.strip().splitlines():
                fp = path / line.strip()
                if fp.exists() and fp.suffix == ".cs":
                    changed_files.append(fp)
        except Exception as e:
            logger.error(f"git diff failed: {e}")
            sys.exit(1)

    if not changed_files:
        logger.error("No changed files found to analyze")
        sys.exit(1)

    logger.info(f"Analyzing impact of {len(changed_files)} file(s)...")

    # Build the dependency graph and flows — reuse the pipeline helpers
    from kb_generator.pipeline import (
        _parse_solution_or_projects,
        _build_graph_and_flows,
    )

    solution = _parse_solution_or_projects(path)
    if not solution:
        logger.error("No .NET solution or projects found")
        sys.exit(1)

    graph, flows, all_classes = _build_graph_and_flows(path, solution, verbose)

    # Load existing KB state for kb_outputs mapping
    from kb_generator.state.tracker import StateTracker
    kb_path = path / ".kb"
    tracker = StateTracker(kb_path)
    state = tracker.load_state()
    kb_outputs = state.kb_outputs if state else {}

    # Run impact analysis
    from kb_generator.analyzers.impact_analyzer import ImpactAnalyzer
    analyzer = ImpactAnalyzer(
        graph=graph,
        flows=flows,
        kb_outputs=kb_outputs,
    )
    report = analyzer.analyze_impact(changed_files, max_depth=depth)

    # Output
    from kb_generator.generators.impact_generator import (
        format_impact_report_terminal,
        format_impact_report_markdown,
    )

    if output:
        md_content = format_impact_report_markdown(report)
        out_path = Path(output)
        out_path.write_text(md_content, encoding="utf-8")
        logger.info(f"✅ Impact report saved to: {out_path}")
    else:
        click.echo(format_impact_report_terminal(report))


if __name__ == "__main__":
    cli()
