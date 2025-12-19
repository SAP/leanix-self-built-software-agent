"""Discovery comand for processing GitHub repositories."""

import signal
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

from src.cli.utils.github_utils import (
    fetch_github_repos,
    validate_repo_format,
    parse_repo_string,
    fetch_single_repo,
)
from src.cli.utils.validators import (
    validate_github_token,
    validate_database_connection,
    validate_mutually_exclusive,
    validate_ai_provider,
    validate_llm_model_availability,
)
from src.cli.utils.formatters import (
    format_summary_table,
    format_repo_status,
    export_to_json,
    repo_state_to_dict,
)
from src.converter.converters import coerce_state
from src.dto.state_dto import RootRepoState, RepoType
from src.logging.logging import get_logger, configure_structlog
from src.services.organizations import create_org_if_not_exists
from src.services.repositories import create_repository
from src.workflows.repo_type_workflow import generate_repo_type_workflow
from src.db.models import init_db

console = Console()
configure_structlog()
logger = get_logger(__name__)

# Global flag for graceful shutdown
interrupted = False


def signal_handler(signum, frame):
    """Handle interrupt signal (Ctrl+C)."""
    global interrupted
    interrupted = True
    console.print("\n[yellow]Interrupt received. Finishing current repository and stopping...[/yellow]")


@click.command()
@click.option(
    '--org',
    type=str,
    help='GitHub organization name'
)
@click.option(
    '--repo',
    type=str,
    help='Repository in format OWNER/REPO'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Save results to JSON file'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Analyze without writing to database'
)
@click.option(
    '--skip-archived',
    is_flag=True,
    default=True,
    help='Skip archived repositories (default: True)'
)
@click.option(
    '--limit',
    type=int,
    help='Max number of repositories to process'
)
@click.option(
    '--github-token',
    type=str,
    help='Override GITHUB_TOKEN from environment'
)
@click.option(
    '--llm',
    type=str,
    metavar='MODEL_NAME',
    help='LLM model to use for discovery (e.g., gpt-4o, claude-sonnet, gpt-4o-mini)'
)
@click.pass_context
def discover(
    ctx: click.Context,
    org: Optional[str],
    repo: Optional[str],
    output: Optional[str],
    dry_run: bool,
    skip_archived: bool,
    limit: Optional[int],
    github_token: Optional[str],
    llm: Optional[str]
):
    """
    Discover self-built software in GitHub repositories.

    Process repositories from an organization or a single repository,
    analyze their structure, detect deployment signals, discover services,
    and store results in the database.

    Examples:

        # Discover all repositories in organization
        sbs-ai-discovery discover --org myorg

        # Discover single repository
        sbs-ai-discovery discover --repo owner/repo

        # Use specific LLM model
        sbs-ai-discovery discover --org myorg --llm gpt-4o
        sbs-ai-discovery discover --repo owner/repo --llm claude-sonnet

        # Dry run without saving to database
        sbs-ai-discovery discover --org myorg --dry-run

        # Save results to JSON file
        sbs-ai-discovery discover --org myorg --output results.json

        # Limit number of repositories
        sbs-ai-discovery discover --org myorg --limit 10
    """
    global interrupted

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Validation
        validate_mutually_exclusive(org, repo)
        github_token = validate_github_token(github_token)
        validate_ai_provider()

        if not dry_run:
            validate_database_connection()
            init_db()

        # Display mode indicators
        if dry_run:
            console.print("[yellow][DRY RUN MODE] - No data will be saved to database[/yellow]\n")

        # Display LLM model if specified
        if llm:
            console.print(f"[cyan]Using LLM model:[/cyan] {llm}\n")

        # Validate LLM availability with a test call
        console.print("[cyan]Validating LLM availability...[/cyan]")
        validate_llm_model_availability(llm)
        console.print("[green]✓[/green] LLM model is available and accessible\n")

        # Determine source and fetch repositories
        if org:
            source = "organization"
            source_name = org
            console.print(f"[bold]Discovering repositories in organization:[/bold] {org}\n")

            # Create organization record
            if not dry_run:
                create_org_if_not_exists(org)

            # Fetch all repos in organization
            try:
                repos = fetch_github_repos(org, github_token, skip_archived)
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                sys.exit(3)
            except Exception as e:
                console.print(f"[red]Error fetching repositories:[/red] {e}")
                sys.exit(3)

            if not repos:
                console.print(f"[yellow]No repositories found in organization '{org}'[/yellow]")
                sys.exit(0)

            console.print(f"Found [cyan]{len(repos)}[/cyan] repositories")

            # Apply limit if specified
            if limit and limit > 0:
                repos = repos[:limit]
                console.print(f"Processing first [cyan]{len(repos)}[/cyan] repositories (--limit {limit})\n")
            else:
                console.print()

        else:  # repo mode
            source = "repository"
            source_name = repo

            # Validate and parse repository format
            if not validate_repo_format(repo):
                console.print(
                    f"[red]Error: Invalid repository format[/red]\n"
                    f"Expected format: OWNER/REPO\n"
                    f"Example: myorg/myrepo"
                )
                sys.exit(5)

            owner, repo_name = parse_repo_string(repo)
            console.print(f"[bold]Discovering repository:[/bold] {repo}\n")

            # Create organization for the owner
            if not dry_run:
                create_org_if_not_exists(owner)

            # Fetch single repository
            try:
                repo_data = fetch_single_repo(owner, repo_name, github_token)
                repos = [repo_data]
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                sys.exit(3)
            except Exception as e:
                console.print(f"[red]Error fetching repository:[/red] {e}")
                sys.exit(3)

        # Initialize statistics
        stats = {
            'total_repositories': 0,
            'deployable': 0,
            'non_deployable': 0,
            'mono_repos': 0,
            'single_purpose_repos': 0,
            'total_services': 0,
            'unique_teams': 0,
            'total_tech_stacks': 0,
            'failed': 0,
            'errors': []
        }

        # Track unique teams and tech stacks
        unique_teams = set()
        total_tech_stacks = 0

        # Store results for JSON export
        results = []

        # Process repositories with progress bar
        workflow = generate_repo_type_workflow()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task(
                f"[cyan]Processing repositories...",
                total=len(repos)
            )

            for idx, repo_data in enumerate(repos, 1):
                if interrupted:
                    console.print("\n[yellow]Processing interrupted by user[/yellow]")
                    break

                repo_url = repo_data.get('html_url')
                progress.update(
                    task,
                    description=f"[cyan]Processing [{idx}/{len(repos)}]..."
                )

                try:
                    # Create initial state
                    initial_state = RootRepoState(repo_root_url=repo_url)

                    # Prepare config with model name if specified
                    config = {
                        "configurable": {
                            "model_name": llm
                        }
                    } if llm else {}

                    # Invoke workflow
                    logger.info(f"Processing repository: {repo_url}")
                    response = workflow.invoke(initial_state, config=config)

                    # Convert and coerce state
                    pred_state = coerce_state(response)

                    # Save to database (unless dry run)
                    if not dry_run:
                        create_repository(pred_state)

                    # Update statistics
                    stats['total_repositories'] += 1

                    if pred_state.deployable:
                        stats['deployable'] += 1

                        if pred_state.repo_type == RepoType.MONO_REPO:
                            stats['mono_repos'] += 1
                        elif pred_state.repo_type == RepoType.SINGLE_PURPOSE_REPO:
                            stats['single_purpose_repos'] += 1

                        stats['total_services'] += len(pred_state.self_built_software)

                        # Collect team and tech stack data
                        for component in pred_state.self_built_software:
                            # Track teams
                            if component.owner and component.owner.team:
                                # Handle both string and list/array of teams
                                if isinstance(component.owner.team, list):
                                    unique_teams.update(component.owner.team)
                                else:
                                    unique_teams.add(component.owner.team)

                            # Count tech stacks
                            if component.tech_stacks:
                                total_tech_stacks += len(component.tech_stacks)
                    else:
                        stats['non_deployable'] += 1

                    # Display status
                    format_repo_status(repo_url, pred_state)

                    # Store for JSON export
                    if output:
                        results.append(repo_state_to_dict(pred_state))

                except KeyboardInterrupt:
                    # Re-raise to be caught by outer handler
                    raise
                except Exception as e:
                    stats['failed'] += 1
                    stats['errors'].append((repo_url, str(e)))
                    logger.error(f"Error processing repository {repo_url}: {e}", exc_info=True)
                    format_repo_status(repo_url, None, str(e))

                finally:
                    progress.update(task, advance=1)

        # Update final stats
        stats['unique_teams'] = len(unique_teams)
        stats['total_tech_stacks'] = total_tech_stacks

        # Display summary
        console.print()
        console.print(format_summary_table(stats))

        # Show errors if any
        if stats['errors']:
            console.print("\n[red]Errors encountered:[/red]")
            for repo_url, error in stats['errors']:
                console.print(f"  [red]•[/red] {repo_url}: {error}")

        # Export to JSON if requested
        if output:
            try:
                export_to_json(
                    results=results,
                    stats=stats,
                    output_path=output,
                    source=source,
                    org_or_repo=source_name,
                    version=ctx.obj.get('version', '0.1.0') if ctx.obj else '0.1.0'
                )
            except Exception as e:
                console.print(f"[red]Failed to export results:[/red] {e}")
                sys.exit(1)

        # Display completion message
        if dry_run:
            console.print("\n[yellow]Dry run completed - no data was saved to database[/yellow]")
        else:
            console.print(f"\n[green]Discovery completed successfully[/green]")

        # Exit with appropriate code
        if interrupted:
            sys.exit(130)
        elif stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except ValueError as e:
        # Validation or configuration errors
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2 if "token" in str(e).lower() or "provider" in str(e).lower() else 5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        logger.error(f"Unexpected error in discover command: {e}", exc_info=True)
        sys.exit(1)
