"""Validation utility functions for CLI."""

import os
from typing import Optional

from rich.console import Console
from sqlalchemy import text

from src.db.conn import get_session
from src.logging.logging import get_logger

console = Console()
logger = get_logger(__name__)


def validate_github_token(token: Optional[str]) -> Optional[str]:
    """
    Validate that a GitHub token is available.

    Checks in order:
    1. Provided token parameter
    2. GITHUB_TOKEN environment variable
    3. GH_TOKEN environment variable

    Args:
        token: GitHub token from command line or None

    Returns:
        The GitHub token if found

    Raises:
        ValueError: If no token is found
    """
    github_token = token or os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')

    if not github_token:
        raise ValueError(
            "GitHub token not found\n"
            "Set GITHUB_TOKEN in environment or .env file, or use --github-token option\n\n"
            "Example:\n"
            "  export GITHUB_TOKEN=ghp_xxxxxxxxxxxx\n"
            "  sbs-ai-discovery discover --org myorg\n"
            "\n"
            "Or:\n"
            "  sbs-ai-discovery discover --org myorg --github-token ghp_xxxxxxxxxxxx"
        )

    return github_token


def validate_database_connection() -> bool:
    """
    Test database connectivity.

    Returns:
        True if database is accessible

    Raises:
        ValueError: If database connection fails
    """
    try:
        with get_session() as session:
            # Simple query to test connection
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise ValueError(
            f"Database connection failed: {e}\n"
            "Please check your DATABASE_URL configuration and ensure the database is accessible."
        )


def validate_mutually_exclusive(org: Optional[str], repo: Optional[str]) -> None:
    """
    Validate that exactly one of --org or --repo is specified.

    Args:
        org: Organization name or None
        repo: Repository string or None

    Raises:
        ValueError: If neither or both are specified
    """
    if not org and not repo:
        raise ValueError(
            "Missing required argument\n"
            "You must specify either --org or --repo\n\n"
            "Examples:\n"
            "  sbs-ai-discovery discover --org myorg\n"
            "  sbs-ai-discovery discover --repo owner/repo"
        )

    if org and repo:
        raise ValueError(
            "Conflicting options\n"
            "Cannot specify both --org and --repo. Choose one.\n\n"
            "Examples:\n"
            "  sbs-ai-discovery discover --org myorg\n"
            "  sbs-ai-discovery discover --repo owner/repo"
        )


def validate_ai_provider() -> bool:
    """
    Validate that at least one AI provider is configured.

    Checks for:
    - OPENAI_API_KEY
    - ANTHROPIC_API_KEY
    - AZURE_OPENAI_API_KEY
    - AICORE_CLIENT_ID

    Returns:
        True if at least one provider is configured

    Raises:
        ValueError: If no AI provider is configured
    """
    providers = {
        'OpenAI': os.getenv('OPENAI_API_KEY'),
        'Anthropic': os.getenv('ANTHROPIC_API_KEY'),
        'Azure OpenAI': os.getenv('AZURE_OPENAI_API_KEY'),
        'SAP AI Core': os.getenv('AICORE_CLIENT_ID'),
    }

    configured = [name for name, key in providers.items() if key]

    if not configured:
        raise ValueError(
            "No AI provider configured\n"
            "Configure at least one AI provider:\n"
            "  - OPENAI_API_KEY for OpenAI\n"
            "  - ANTHROPIC_API_KEY for Anthropic\n"
            "  - AZURE_OPENAI_API_KEY for Azure OpenAI\n"
            "  - AICORE_CLIENT_ID for SAP AI Core"
        )

    logger.info(f"AI provider configured: {', '.join(configured)}")
    return True


def validate_leanix_credentials(
    token: Optional[str] = None,
    domain: Optional[str] = None
) -> tuple[str, str]:
    """
    Validate that LeanIX credentials are available.

    Checks in order:
    1. Provided token/domain parameters
    2. LEANIX_TOKEN and LEANIX_DOMAIN environment variables

    Args:
        token: LeanIX token from command line or None
        domain: LeanIX domain from command line or None

    Returns:
        Tuple of (token, domain)

    Raises:
        ValueError: If credentials are missing
    """
    leanix_token = token or os.getenv('LEANIX_TOKEN')
    leanix_domain = domain or os.getenv('LEANIX_DOMAIN')

    missing = []
    if not leanix_token:
        missing.append('LEANIX_TOKEN')
    if not leanix_domain:
        missing.append('LEANIX_DOMAIN')

    if missing:
        raise ValueError(
            f"LeanIX credentials not found: {', '.join(missing)}\n"
            "Set them in environment or .env file, or use --leanix-token and --leanix-domain options\n\n"
            "Example:\n"
            "  export LEANIX_TOKEN=your-token\n"
            "  export LEANIX_DOMAIN=company.leanix.net\n"
            "  sbs-ai-discovery sync pathfinder\n"
            "\n"
            "Or:\n"
            "  sbs-ai-discovery sync pathfinder --leanix-token your-token --leanix-domain company.leanix.net"
        )

    return leanix_token, leanix_domain
