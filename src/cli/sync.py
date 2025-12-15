"""Sync command for syncing discovery data to external systems."""
import logging
import sys
from typing import Optional

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from src.cli.utils.validators import validate_leanix_credentials
from src.logging.logging import configure_structlog, get_logger

console = Console()
configure_structlog()
logger = get_logger(__name__)


@click.group(name='sync')
@click.pass_context
def sync_group(ctx: click.Context) -> None:
    """
    Sync discovery data to external systems.

    Synchronize discovered services, tech stacks, and contributors
    from the local database to external enterprise architecture management
    systems like LeanIX Pathfinder.

    Examples:

        # Sync all data to LeanIX Pathfinder
        sbs-ai-discovery sync pathfinder

        # Sync specific repository
        sbs-ai-discovery sync pathfinder --repo owner/repo

        # Dry run to preview changes
        sbs-ai-discovery sync pathfinder --dry-run
    """
    pass


@sync_group.command(name='pathfinder')
@click.option(
    '--repo',
    type=str,
    help='Sync only a specific repository (format: OWNER/REPO)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview sync operations without making changes'
)
@click.option(
    '--leanix-token',
    type=str,
    help='Override LEANIX_TOKEN from environment'
)
@click.option(
    '--leanix-domain',
    type=str,
    help='Override LEANIX_DOMAIN from environment'
)
@click.option(
    '--skip-services',
    is_flag=True,
    help='Skip syncing services'
)
@click.option(
    '--skip-techstacks',
    is_flag=True,
    help='Skip syncing tech stacks'
)
@click.option(
    '--skip-contributors',
    is_flag=True,
    help='Skip syncing contributors'
)
@click.pass_context
def sync_pathfinder(
    ctx: click.Context,
    repo: Optional[str],
    dry_run: bool,
    leanix_token: Optional[str],
    leanix_domain: Optional[str],
    skip_services: bool,
    skip_techstacks: bool,
    skip_contributors: bool,
):
    """
    Sync data to LeanIX Pathfinder.

    Synchronizes discovered services to LeanIX Pathfinder by creating
    or updating Application fact sheets, linking tech stacks, and
    assigning contributors.

    Examples:

        # Sync all discovered services
        sbs-ai-discovery sync pathfinder

        # Sync a specific repository
        sbs-ai-discovery sync pathfinder --repo myorg/backend-api

        # Dry run to preview changes
        sbs-ai-discovery sync pathfinder --dry-run

        # Sync only services, skip tech stacks and contributors
        sbs-ai-discovery sync pathfinder --skip-techstacks --skip-contributors
    """

    # Import sync service (deferred to avoid circular imports and DB init issues)
    from sync_pathfinder import (
        get_discovery_data,
        sync_services,
        sync_tech_stacks,
        sync_contributors,
        initialize_leanix_client,
    )

    try:
        # Validate LeanIX credentials
        leanix_token, leanix_domain = validate_leanix_credentials(
            leanix_token, leanix_domain
        )

        # Initialize LeanIX client
        console.print("[cyan]Initializing LeanIX connection...[/cyan]")
        try:
            initialize_leanix_client(leanix_token, leanix_domain)
        except Exception as e:
            console.print(f"[red]Failed to connect to LeanIX:[/red] {e}")
            sys.exit(3)

        console.print("[green]✓[/green] Connected to LeanIX\n")

        # Fetch discovery data
        console.print("[cyan]Fetching discovery data from database...[/cyan]")
        try:
            services = get_discovery_data(repo_filter=repo)
        except Exception as e:
            console.print(f"[red]Failed to fetch data from database:[/red] {e}")
            sys.exit(4)

        if not services:
            if repo:
                console.print(f"[yellow]No services found for repository: {repo}[/yellow]")
            else:
                console.print("[yellow]No services found in database[/yellow]")
            console.print("\n[dim]Tip: Run 'sbs-ai-discovery discover' first to populate the database[/dim]")
            sys.exit(0)

        console.print(f"[green]✓[/green] Found {len(services)} service(s)\n")

        # Display mode indicator
        if dry_run:
            console.print("[yellow][DRY RUN MODE] - No changes will be made to LeanIX[/yellow]\n")

        # Display what will be synced
        console.print("[bold]Sync Plan:[/bold]")
        plan_table = Table(show_header=True, header_style="bold cyan")
        plan_table.add_column("Component")
        plan_table.add_column("Action")
        plan_table.add_row(
            "Services",
            "[yellow]Skip[/yellow]" if skip_services else "[green]Sync[/green]"
        )
        plan_table.add_row(
            "Tech Stacks",
            "[yellow]Skip[/yellow]" if skip_techstacks else "[green]Sync[/green]"
        )
        plan_table.add_row(
            "Contributors",
            "[yellow]Skip[/yellow]" if skip_contributors else "[green]Sync[/green]"
        )
        console.print(plan_table)
        console.print()

        # Initialize summaries
        service_summary = {"created": 0, "updated": 0, "failed": 0}
        techstack_summary = {"linked": 0, "created": 0, "failed": 0}
        contributor_summary = {"created": 0, "already_exists": 0, "failed": 0}

        # Sync services
        if not skip_services:
            console.print("[bold]Syncing Services...[/bold]")
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=False
                ) as progress:
                    task = progress.add_task("[cyan]Syncing services...", total=len(services))

                    def update_progress(current, total, name):
                        progress.update(task, completed=current, description=f"[cyan]Syncing services [{current}/{total}]: {name}")

                    updated_services, service_summary = sync_services(services, dry_run, progress_callback=update_progress)

                console.print(f"  [green]✓[/green] Created: {service_summary['created']}")
                console.print(f"  [green]✓[/green] Updated: {service_summary['updated']}")
                if service_summary['failed'] > 0:
                    console.print(f"  [red]✗[/red] Failed: {service_summary['failed']}")

                # Display errors if any
                if service_summary.get('errors'):
                    console.print("\n  [red]Errors:[/red]")
                    for error in service_summary['errors']:
                        console.print(f"    • {error['service']}: {error['error']}")

                console.print()
            except Exception as e:
                console.print(f"[red]Failed to sync services:[/red] {e}")
                logger.error(f"Service sync error: {e}", exc_info=True)
                sys.exit(1)
        else:
            updated_services = services
            console.print("[dim]Skipping service sync[/dim]\n")

        # Sync tech stacks
        if not skip_techstacks:
            console.print("[bold]Syncing Tech Stacks...[/bold]")
            try:
                # Calculate total tech stacks
                total_stacks = sum(len(s.get("tech_stacks", [])) for s in updated_services)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=False
                ) as progress:
                    task = progress.add_task("[cyan]Syncing tech stacks...", total=total_stacks)

                    def update_progress(current, total, name):
                        progress.update(task, completed=current, description=f"[cyan]Syncing tech stacks [{current}/{total}]: {name}")

                    techstack_summary = sync_tech_stacks(updated_services, dry_run, progress_callback=update_progress)

                console.print(f"  [green]✓[/green] Linked: {techstack_summary['linked']}")
                console.print(f"  [green]✓[/green] Created: {techstack_summary['created']}")
                if techstack_summary['failed'] > 0:
                    console.print(f"  [red]✗[/red] Failed: {techstack_summary['failed']}")

                # Display errors if any
                if techstack_summary.get('errors'):
                    console.print("\n  [red]Errors:[/red]")
                    for error in techstack_summary['errors']:
                        console.print(f"    • {error['techstack']} (service: {error['service']}): {error['error']}")

                console.print()
            except Exception as e:
                console.print(f"[red]Failed to sync tech stacks:[/red] {e}")
                logger.error(f"Tech stack sync error: {e}", exc_info=True)
                sys.exit(1)
        else:
            console.print("[dim]Skipping tech stack sync[/dim]\n")

        # Sync contributors
        if not skip_contributors:
            console.print("[bold]Syncing Contributors...[/bold]")
            try:
                # Calculate total contributors
                total_contributors = sum(len(s.get("contributors", [])) for s in updated_services)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=False
                ) as progress:
                    task = progress.add_task("[cyan]Syncing contributors...", total=total_contributors)

                    def update_progress(current, total, name):
                        progress.update(task, completed=current, description=f"[cyan]Syncing contributors [{current}/{total}]: {name}")

                    contributor_summary = sync_contributors(updated_services, dry_run, progress_callback=update_progress)

                console.print(f"  [green]✓[/green] Created: {contributor_summary['created']}")
                console.print(f"  [green]✓[/green] Already exists: {contributor_summary['already_exists']}")
                if contributor_summary['failed'] > 0:
                    console.print(f"  [red]✗[/red] Failed: {contributor_summary['failed']}")

                # Display errors if any
                if contributor_summary.get('errors'):
                    console.print("\n  [red]Errors:[/red]")
                    for error in contributor_summary['errors']:
                        console.print(f"    • {error['contributor']} (service: {error['service']}): {error['error']}")

                console.print()
            except Exception as e:
                console.print(f"[red]Failed to sync contributors:[/red] {e}")
                logger.error(f"Contributor sync error: {e}", exc_info=True)
                sys.exit(1)
        else:
            console.print("[dim]Skipping contributor sync[/dim]\n")

        # Display summary
        console.print("[bold]Sync Summary:[/bold]")
        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Component")
        summary_table.add_column("Created", justify="right")
        summary_table.add_column("Updated/Linked", justify="right")
        summary_table.add_column("Already Exists", justify="right")
        summary_table.add_column("Failed", justify="right")

        summary_table.add_row(
            "Services",
            str(service_summary['created']),
            str(service_summary['updated']),
            "-",
            f"[red]{service_summary['failed']}[/red]" if service_summary['failed'] > 0 else "0"
        )
        summary_table.add_row(
            "Tech Stacks",
            str(techstack_summary['created']),
            str(techstack_summary['linked']),
            "-",
            f"[red]{techstack_summary['failed']}[/red]" if techstack_summary['failed'] > 0 else "0"
        )
        summary_table.add_row(
            "Contributors",
            str(contributor_summary['created']),
            "-",
            str(contributor_summary['already_exists']),
            f"[red]{contributor_summary['failed']}[/red]" if contributor_summary['failed'] > 0 else "0"
        )
        console.print(summary_table)

        # Final message
        if dry_run:
            console.print("\n[yellow]Dry run completed - no changes were made to LeanIX[/yellow]")
        else:
            console.print("\n[green]Sync completed successfully[/green]")

        # Exit with appropriate code
        total_failed = service_summary['failed'] + techstack_summary['failed'] + contributor_summary['failed']
        if total_failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except ValueError as e:
        # Validation errors
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.error(f"Unexpected error in sync pathfinder command: {e}", exc_info=True)
        sys.exit(1)
