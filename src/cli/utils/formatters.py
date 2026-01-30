"""Output formatting utilities for CLI."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from src.dto.state_dto import RootRepoState 
from src.logging.logging import get_logger

console = Console()
logger = get_logger(__name__)


def format_summary_table(stats: Dict[str, int]) -> Table:
    """
    Create a Rich table from processing statistics.

    Args:
        stats: Dictionary containing statistics about processed repositories

    Returns:
        Rich Table object ready for display
    """
    table = Table(title="Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green")

    table.add_row("Repositories", str(stats.get('total_repositories', 0)))
    table.add_row("Deployable", str(stats.get('deployable', 0)))
    table.add_row("Non-deployable", str(stats.get('non_deployable', 0)))
    table.add_row("Mono-repos", str(stats.get('mono_repos', 0)))
    table.add_row("Single-purpose", str(stats.get('single_purpose_repos', 0)))
    table.add_row("Services found", str(stats.get('total_services', 0)))
    table.add_row("Unique teams", str(stats.get('unique_teams', 0)))
    table.add_row("Tech stacks", str(stats.get('total_tech_stacks', 0)))
    table.add_row("Failed", str(stats.get('failed', 0)), style="red" if stats.get('failed', 0) > 0 else "green")

    return table


def format_repo_status(repo_url: str, repo_state: RootRepoState, error: Optional[str] = None) -> None:
    """
    Display the status of a processed repository.

    Args:
        repo_url: URL of the repository
        repo_state: Processed repository state
        error: Error message if processing failed
    """
    console.print(f"\n[bold cyan]Processing:[/bold cyan] {repo_url}")

    if error:
        console.print(f"  [red]✗ Failed:[/red] {error}")
        return

    if not repo_state.deployable:
        console.print("  [yellow]✓ Not deployable[/yellow]")
        return

    console.print("  [green]✓ Repository cloned[/green]")

    if repo_state.deployable_signal_files:
        signals = ", ".join(repo_state.deployable_signal_files[:3])
        if len(repo_state.deployable_signal_files) > 3:
            signals += f", ... ({len(repo_state.deployable_signal_files)} total)"
        console.print(f"  [green]✓ Deployment signals detected:[/green] {signals}")

    if repo_state.repo_type:
        console.print(f"  [green]✓ Repository type:[/green] {repo_state.repo_type.value}")

    if repo_state.self_built_software:
        console.print(f"  [green]✓ Services discovered:[/green] {len(repo_state.self_built_software)}")
        for component in repo_state.self_built_software[:3]:
            path_info = f" (path: {component.path})" if component.path else ""
            console.print(f"    - {component.name}{path_info}")
        if len(repo_state.self_built_software) > 3:
            console.print(f"    ... and {len(repo_state.self_built_software) - 3} more")

    console.print("  [green]✓ Results saved to database[/green]")


def export_to_json(
    results: List[Dict[str, Any]],
    stats: Dict[str, int],
    output_path: str,
    source: str = "organization",
    org_or_repo: str = Optional[None],
    version: str = "0.1.0"
) -> None:
    """
    Export discovery results to a JSON file.

    Args:
        results: List of repository result dictionaries
        stats: Statistics dictionary
        output_path: Path to output JSON file
        source: Source type ("organization" or "repository")
        org_or_repo: Organization or repository name
        version: Tool version

    Raises:
        IOError: If file cannot be written
    """
    output = {
        "metadata": {
            "analyzed_at": datetime.now(timezone.utc).isoformat() + "Z",
            "source": source,
            "total_repositories": stats.get('total_repositories', 0),
            "version": version
        },
        "repositories": results,
        "summary": {
            "total_repositories": stats.get('total_repositories', 0),
            "deployable": stats.get('deployable', 0),
            "non_deployable": stats.get('non_deployable', 0),
            "mono_repos": stats.get('mono_repos', 0),
            "single_purpose_repos": stats.get('single_purpose_repos', 0),
            "total_services": stats.get('total_services', 0),
            "unique_teams": stats.get('unique_teams', 0),
            "total_tech_stacks": stats.get('total_tech_stacks', 0),
            "failed": stats.get('failed', 0)
        }
    }

    # Add organization or repository to metadata
    if source == "organization" and org_or_repo:
        output["metadata"]["organization"] = org_or_repo
    elif source == "repository" and org_or_repo:
        output["metadata"]["repository"] = org_or_repo

    try:
        output_file = Path(output_path)
        output_file.write_text(json.dumps(output, indent=2), encoding='utf-8')
        console.print(f"\n[green]Results saved to:[/green] {output_path}")
        logger.info(f"Exported results to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")
        console.print(f"[red]Error saving output file:[/red] {e}")
        raise


def repo_state_to_dict(repo_state: RootRepoState) -> Dict[str, Any]:
    """
    Convert a RootRepoState object to a dictionary for JSON export.

    Args:
        repo_state: Repository state object

    Returns:
        Dictionary representation suitable for JSON export
    """
    result = {
        "url": repo_state.repo_root_url,
        "deployable": repo_state.deployable,
        "deployment_signals": repo_state.deployable_signal_files,
    }

    if repo_state.repo_type:
        result["repo_type"] = repo_state.repo_type.value

    if repo_state.self_built_software:
        result["components"] = []
        for component in repo_state.self_built_software:
            comp_dict = {
                "name": component.name,
                "path": component.path,
                "display_url": component.display_url,
                "component_type": component.component_type.value if component.component_type else "unknown",
                "evidence": component.evidence,
                "confidence": component.confidence,
            }

            if component.language:
                comp_dict["language"] = component.language

            if component.owner:
                comp_dict["owner"] = {
                    "team": component.owner.team,
                }
                if component.owner.individuals:
                    comp_dict["owner"]["individuals"] = [
                        {
                            "name": ind.name,
                            "github": ind.github,
                            "emails": ind.emails
                        }
                        for ind in component.owner.individuals
                    ]

            if component.tech_stacks:
                comp_dict["tech_stacks"] = []
                for ts in component.tech_stacks:
                    # Handle both TechStack objects and dicts
                    if isinstance(ts, dict):
                        ts_name = ts.get("name", "")
                        ts_version = ts.get("version", "")
                        ts_confidence = ts.get("confidence", "")
                        ts_evidence = ts.get("evidence", [])
                    else:
                        # TechStack object
                        ts_name = ts.name
                        ts_version = ts.version
                        ts_confidence = ts.confidence
                        ts_evidence = ts.evidence

                    # Build tech stack dict
                    ts_dict = {
                        "name": ts_name,
                        "version": ts_version,
                        "confidence": ts_confidence,
                        "evidence": []
                    }

                    # Process evidence (same for both dict and object)
                    for ev in ts_evidence:
                        if isinstance(ev, dict):
                            ts_dict["evidence"].append({
                                "path": ev.get("path", ""),
                                "snippet": ev.get("snippet", ""),
                                "reason": ev.get("reason", "")
                            })
                        else:
                            ts_dict["evidence"].append({
                                "path": ev.path,
                                "snippet": ev.snippet,
                                "reason": ev.reason
                            })

                    comp_dict["tech_stacks"].append(ts_dict)

            result["components"].append(comp_dict)

    return result
