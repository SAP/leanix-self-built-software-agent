"""GitHub API utility functions for CLI."""

import re
import time
from typing import Dict, List, Optional, Tuple

import requests
from rich.console import Console

from src.logging.logging import get_logger

console = Console()
logger = get_logger(__name__)


def fetch_github_repos(
    org_name: str,
    github_token: str,
    skip_archived: bool = True
) -> List[Dict]:
    """
    Fetch all repositories for the specified GitHub organization.

    Handles pagination and rate limiting with exponential backoff.

    Args:
        org_name: GitHub organization name
        github_token: GitHub personal access token
        skip_archived: Whether to skip archived repositories (default: True)

    Returns:
        List of repository dictionaries from GitHub API

    Raises:
        requests.HTTPError: If GitHub API returns an error
        Exception: For other unexpected errors
    """
    if not github_token:
        raise ValueError("GitHub token is required")
    if not org_name:
        raise ValueError("Organization name is required")

    headers = {"Authorization": f"token {github_token}"}
    repos = []
    page = 1
    backoff = 1

    while True:
        url = f"https://api.github.com/orgs/{org_name}/repos?per_page=100&page={page}"
        logger.debug(f"Fetching repositories from: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            # Handle rate limiting
            if response.status_code == 403 and "rate limit" in response.text.lower():
                logger.warning("GitHub API rate limit reached, backing off...")
                console.print(f"[yellow]Warning: GitHub API rate limit reached, waiting {backoff} seconds...[/yellow]")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            response.raise_for_status()
            data = response.json()

            if not data:
                break

            # Filter out archived repos if requested
            if skip_archived:
                filtered_repos = [repo for repo in data if not repo.get("archived", False)]
                repos.extend(filtered_repos)
            else:
                repos.extend(data)

            page += 1
            backoff = 1

        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            console.print(f"[yellow]Connection error, retrying in {backoff} seconds...[/yellow]")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            if e.response.status_code == 404:
                raise ValueError(f"Organization '{org_name}' not found or not accessible")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error fetching repos: {str(exc)}")
            raise

    logger.info(f"Fetched {len(repos)} repositories from organization {org_name}")
    return repos


def validate_repo_format(repo_str: str) -> bool:
    """
    Validate that a repository string matches the OWNER/REPO format.

    Args:
        repo_str: Repository string to validate

    Returns:
        True if valid format, False otherwise
    """
    if not repo_str:
        return False

    # GitHub username/org and repo name can contain alphanumeric, hyphens, underscores, and periods
    pattern = r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$'
    return bool(re.match(pattern, repo_str))


def parse_repo_string(repo_str: str) -> Tuple[str, str]:
    """
    Parse a repository string in OWNER/REPO format into owner and repo name.

    Args:
        repo_str: Repository string in OWNER/REPO format

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If format is invalid
    """
    if not validate_repo_format(repo_str):
        raise ValueError(
            f"Invalid repository format: {repo_str}\n"
            "Expected format: OWNER/REPO\n"
            "Example: myorg/myrepo"
        )

    owner, repo = repo_str.split('/', 1)
    return owner, repo


def fetch_single_repo(
    owner: str,
    repo: str,
    github_token: str
) -> Dict:
    """
    Fetch information for a single GitHub repository.

    Args:
        owner: Repository owner (user or organization)
        repo: Repository name
        github_token: GitHub personal access token

    Returns:
        Repository dictionary from GitHub API

    Raises:
        requests.HTTPError: If repository not found or not accessible
    """
    if not github_token:
        raise ValueError("GitHub token is required")

    headers = {"Authorization": f"token {github_token}"}
    url = f"https://api.github.com/repos/{owner}/{repo}"

    logger.debug(f"Fetching repository from: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Repository '{owner}/{repo}' not found or not accessible")
        raise
