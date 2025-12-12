"""Main CLI entry point for SBS AI Discovery.

This module provides the main command-line interface with global options
and command groups for discovering self-built software in GitHub repositories.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console

from src.logging.logging import configure_structlog, get_logger

# Initialize Rich console for beautiful output
console = Console()

# Package version
try:
    from importlib.metadata import version
    __version__ = version('ai-based-discovery')
except Exception:
    __version__ = '1.0.0'


@click.group()
@click.option(
    '--env-file',
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help='Path to .env file (default: .env in current directory)',
    envvar='ENV_FILE',
)
@click.version_option(version=__version__, prog_name='sbs-ai-discovery')
@click.pass_context
def cli(
    ctx: click.Context,
    env_file: Optional[str],
) -> None:
    """
    SBS AI Discovery - Automated discovery of self-built software in GitHub repositories.

    Discover self-built software running in production and identify its owners,
    dependencies, technology stacks, and runtime details using AI agents.

    Examples:

        # Discover all repositories in an organization
        sbs-ai-discovery discover --org myorg

        # Discover a single repository
        sbs-ai-discovery discover --repo owner/repo

        # Validate configuration
        sbs-ai-discovery config validate

        # Initialize database
        sbs-ai-discovery db init
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Load environment file
    load_env_file(env_file)

    # Store settings in context for child commands
    ctx.obj['env_file'] = env_file


def load_env_file(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.

    Behavior:
    1. If env_file is specified, load from that file (error if not found)
    2. If not specified, try to load from default .env in current directory
    3. If .env not found, check if required environment variables are already set
    4. If no env file and no environment variables, raise an error

    Args:
        env_file: Path to custom .env file, or None to use default .env

    Raises:
        SystemExit: If no env file found and required variables not set
    """
    # Required environment variables to check
    required_vars = ['GITHUB_TOKEN', 'DATABASE_URL']

    # Case 1: Custom env file specified
    if env_file:
        env_path = Path(env_file)
        if not env_path.exists():
            console.print(f"[red]Error: Environment file not found: {env_file}[/red]")
            sys.exit(2)
        load_dotenv(env_path)
        console.print(f"[dim]Loaded environment from: {env_file}[/dim]")
        return

    # Case 2: Try default .env file
    default_env = Path.cwd() / '.env'
    if default_env.exists():
        load_dotenv(default_env)
        console.print(f"[dim]Loaded environment from: {default_env}[/dim]")
        return

    # Case 3: Check if required environment variables are already set
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if not missing_vars:
        # All required variables are already set in environment
        console.print("[dim]Using environment variables (no .env file found)[/dim]")
        return

    # Case 4: No env file and missing required variables - raise error
    console.print("[red]Error: No .env file found and required environment variables are not set[/red]")
    console.print(f"[yellow]Missing variables: {', '.join(missing_vars)}[/yellow]")
    console.print("\n[cyan]Please either:[/cyan]")
    console.print("  1. Create a .env file in the current directory")
    console.print("  2. Specify an env file with --env-file")
    console.print("  3. Set the required environment variables")
    sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    console.print(f"[bold]SBS AI Discovery[/bold] version [cyan]{__version__}[/cyan]")


# Import and register command groups
from src.cli.discover import discover

cli.add_command(discover)

# These will be added as we implement each command module
# from src.cli.config import config_group
# from src.cli.db import db_group
# from src.cli.sync import sync_group

# cli.add_command(config_group, name='config')
# cli.add_command(db_group, name='db')
# cli.add_command(sync_group, name='sync')


if __name__ == '__main__':
    cli()

