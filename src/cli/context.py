"""Context management commands for SBS AI Discovery.

This module provides CLI commands for managing context files that
improve AI discovery accuracy. Users can initialize template context
files for organizations and repositories.
"""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

# Import the directory constant from context_loader for consistency
from src.services.context_loader import ORG_CONTEXT_DIR, REPO_CONTEXT_FILENAME

console = Console()

# Template for organization context files
ORG_CONTEXT_TEMPLATE = """# Organization Context for {org}

This file provides context to AI agents during repository discovery.
Place organization-wide hints, patterns, and conventions here.

## Naming Conventions
<!-- Example: Our services follow the pattern: {{team}}-{{function}}-service -->

## Deployment Patterns
<!-- Example: All production services deploy to Kubernetes in namespace 'prod' -->

## Team Ownership Rules
<!-- Example: Repositories prefixed with 'platform-' belong to Platform team -->

## Technology Standards
<!-- Example: We use Python 3.11+ for all backend services -->

## Custom Indicators
<!-- Add any domain-specific hints that help identify services -->
"""

# Template for repository context files
REPO_CONTEXT_TEMPLATE = """# Repository Context

This file provides context to AI agents during discovery of this repository.
Repository-specific hints override organization defaults.

## Service Information
<!-- Example: This is a microservice handling user authentication -->

## Deployment Details
<!-- Example: Deploys to production via GitHub Actions to AWS ECS -->

## Team Ownership
<!-- Example: Owned by Identity team, contact: identity@company.com -->

## Technology Notes
<!-- Example: Uses FastAPI with PostgreSQL, Redis for caching -->

## Special Considerations
<!-- Any unusual patterns or exceptions for this repo -->
"""


@click.group(name='context')
@click.pass_context
def context_group(ctx: click.Context) -> None:
    """
    Manage context files for AI discovery.

    Context files provide hints and metadata that improve AI agent accuracy
    during repository discovery. Organization-level context applies to all
    repositories in an org, while repository-level context is specific to
    a single repository.

    Examples:

        # Initialize organization context template
        sbs-ai-discovery context init --org myorg

        # Initialize repository context template in current directory
        sbs-ai-discovery context init --repo

        # Force overwrite existing files
        sbs-ai-discovery context init --org myorg --force
    """
    pass


@context_group.command(name='init')
@click.option(
    '--org',
    type=str,
    help='Organization name (creates ~/.sbs-discovery/{org}.md)'
)
@click.option(
    '--repo',
    is_flag=True,
    help='Create repository context file in current directory'
)
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing context files'
)
@click.pass_context
def init(
    ctx: click.Context,
    org: Optional[str],
    repo: bool,
    force: bool,
) -> None:
    """
    Initialize context template files.

    Creates template context files with helpful documentation and examples.
    Organization context files are created in ~/.sbs-discovery/{org}.md,
    and repository context files are created as .sbs-discovery.md in the
    current directory.

    Examples:

        # Create organization context for 'mycompany'
        sbs-ai-discovery context init --org mycompany

        # Create repository context in current directory
        sbs-ai-discovery context init --repo

        # Create both at once
        sbs-ai-discovery context init --org mycompany --repo

        # Overwrite existing files
        sbs-ai-discovery context init --org mycompany --force
    """
    # Validate at least one option is provided
    if not org and not repo:
        console.print(
            "[red]Error:[/red] Please specify --org <name> and/or --repo\n"
        )
        console.print("Examples:")
        console.print("  sbs-ai-discovery context init --org mycompany")
        console.print("  sbs-ai-discovery context init --repo")
        console.print("  sbs-ai-discovery context init --org mycompany --repo")
        raise SystemExit(1)

    files_created = 0

    # Create organization context file
    if org:
        org_file = _create_org_context(org, force)
        if org_file:
            files_created += 1

    # Create repository context file
    if repo:
        repo_file = _create_repo_context(force)
        if repo_file:
            files_created += 1

    # Summary
    if files_created > 0:
        console.print(
            f"\n[green]Successfully created {files_created} context file(s)[/green]"
        )
        console.print(
            "[dim]Edit the files to add your organization and repository-specific context.[/dim]"
        )


def _create_org_context(org: str, force: bool) -> Optional[Path]:
    """Create organization context file.

    Args:
        org: Organization name
        force: Whether to overwrite existing file

    Returns:
        Path to created file, or None if skipped
    """
    # Ensure directory exists
    ORG_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

    org_file = ORG_CONTEXT_DIR / f"{org}.md"

    # Check if file exists
    if org_file.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Organization context file already exists: {org_file}"
        )
        console.print("[dim]Use --force to overwrite[/dim]")
        return None

    # Write template with organization name
    content = ORG_CONTEXT_TEMPLATE.format(org=org)
    org_file.write_text(content, encoding="utf-8")

    console.print(f"[green]Created:[/green] {org_file}")
    return org_file


def _create_repo_context(force: bool) -> Optional[Path]:
    """Create repository context file in current directory.

    Args:
        force: Whether to overwrite existing file

    Returns:
        Path to created file, or None if skipped
    """
    cwd = Path.cwd()

    # Safety check: don't create in home directory
    if cwd == Path.home():
        console.print(
            "[red]Error:[/red] Cannot create repository context in home directory"
        )
        console.print(
            "[dim]Please run this command from within a repository directory[/dim]"
        )
        return None

    repo_file = cwd / REPO_CONTEXT_FILENAME

    # Check if file exists
    if repo_file.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Repository context file already exists: {repo_file}"
        )
        console.print("[dim]Use --force to overwrite[/dim]")
        return None

    # Write template
    repo_file.write_text(REPO_CONTEXT_TEMPLATE, encoding="utf-8")

    console.print(f"[green]Created:[/green] {repo_file}")
    return repo_file
