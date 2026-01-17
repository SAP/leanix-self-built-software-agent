"""Runnable for loading user-provided discovery context into workflow state.

This runnable is called AFTER clone_repo_runnable, when state.local_path
is populated. It discovers and loads context from:
- Organization level: ~/.sbs-discovery/{org}.md
- Repository level: .sbs-discovery.md in the cloned repo

The loaded context is attached to state.discovery_context for use
by downstream LLM agents.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.services.context_loader import build_discovery_context

logger = get_logger(__name__)


def load_context_runnable(state: RootRepoState) -> RootRepoState:
    """Load user-provided discovery context from files into workflow state.

    This runnable discovers and loads context files that help LLM agents
    make better discovery decisions. It should be called after the repository
    is cloned (state.local_path must be populated).

    Args:
        state: The current workflow state with repo_root_url and local_path set.

    Returns:
        Updated state with discovery_context populated.
    """
    logger.info(
        "Loading discovery context",
        repo_url=state.repo_root_url,
        local_path=state.local_path,
    )

    # Extract org name from repository URL
    org_name = _extract_org_from_url(state.repo_root_url)
    if org_name:
        logger.debug("Extracted organization name", org_name=org_name)
    else:
        logger.debug(
            "Could not extract organization name from URL",
            repo_url=state.repo_root_url,
        )

    # Build discovery context (handles file loading and merging)
    context = build_discovery_context(
        org_name=org_name,
        local_path=state.local_path,
    )

    # Attach to state
    state.discovery_context = context

    # Log summary
    logger.info(
        "Discovery context loaded",
        org_context_found=context.org_context is not None,
        repo_context_found=context.repo_context is not None,
        has_merged_context=context.merged_context is not None,
    )

    return state


def _extract_org_from_url(repo_url: str) -> Optional[str]:
    """Extract the organization/owner name from a GitHub repository URL.

    Handles both HTTPS and SSH URL formats:
    - https://github.com/org/repo
    - https://github.com/org/repo.git
    - git@github.com:org/repo.git

    Args:
        repo_url: The repository URL to parse.

    Returns:
        The organization/owner name, or None if the URL doesn't match
        expected patterns.
    """
    if not repo_url:
        return None

    # Try HTTPS format: https://github.com/org/repo[.git]
    try:
        parsed = urlparse(repo_url)
        if parsed.hostname in ("github.com", "www.github.com"):
            # path is like "/org/repo" or "/org/repo.git"
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 1 and path_parts[0]:
                return path_parts[0]
    except (ValueError, AttributeError):
        pass

    # Try SSH format: git@github.com:org/repo.git
    ssh_pattern = r"^git@github\.com:([^/]+)/.*$"
    match = re.match(ssh_pattern, repo_url)
    if match:
        return match.group(1)

    return None
