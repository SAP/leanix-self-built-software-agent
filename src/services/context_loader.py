"""Context discovery and loading service for user-provided context files.

This module handles the discovery and loading of user-provided context files that
improve AI discovery accuracy. Context can be loaded from:
- Organization level: ~/.sbs-discovery/{org}.md (local config)
- Repository level: .sbs-discovery.md in repo root

Repository context extends/overrides organization context.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from src.dto.context_dto import DiscoveryContext, merge_contexts
from src.logging.logging import get_logger

logger = get_logger(__name__)

# Base directory for organization-level context files
ORG_CONTEXT_DIR = Path.home() / ".sbs-discovery"

# Filename to look for in repository roots
REPO_CONTEXT_FILENAME = ".sbs-discovery.md"


def load_org_context(org_name: str) -> tuple[Optional[str], Optional[str]]:
    """Load organization-level context from local config file.

    Args:
        org_name: The organization/owner name to look up.

    Returns:
        A tuple of (content, path) if the file exists and is readable,
        or (None, None) if not found or an error occurs.
    """
    if not org_name:
        return None, None

    context_path = ORG_CONTEXT_DIR / f"{org_name}.md"

    try:
        if context_path.exists() and context_path.is_file():
            content = context_path.read_text(encoding="utf-8")
            logger.debug(
                "Loaded organization context",
                org_name=org_name,
                path=str(context_path),
                size=len(content),
            )
            return content, str(context_path)
        else:
            logger.debug(
                "No organization context file found",
                org_name=org_name,
                expected_path=str(context_path),
            )
            return None, None
    except PermissionError:
        logger.warning(
            "Permission denied reading organization context",
            org_name=org_name,
            path=str(context_path),
        )
        return None, None
    except OSError as exc:
        logger.warning(
            "Error reading organization context file",
            org_name=org_name,
            path=str(context_path),
            error=str(exc),
        )
        return None, None


def load_repo_context(local_path: str) -> tuple[Optional[str], Optional[str]]:
    """Load repository-level context from the cloned repo.

    Args:
        local_path: The local filesystem path to the cloned repository.

    Returns:
        A tuple of (content, path) if the file exists and is readable,
        or (None, None) if not found or an error occurs.
    """
    if not local_path:
        return None, None

    context_path = Path(local_path) / REPO_CONTEXT_FILENAME

    try:
        if context_path.exists() and context_path.is_file():
            content = context_path.read_text(encoding="utf-8")
            logger.debug(
                "Loaded repository context",
                path=str(context_path),
                size=len(content),
            )
            return content, str(context_path)
        else:
            # Not finding repo context is expected/normal - most repos won't have it
            logger.debug(
                "No repository context file found",
                expected_path=str(context_path),
            )
            return None, None
    except PermissionError:
        logger.warning(
            "Permission denied reading repository context",
            path=str(context_path),
        )
        return None, None
    except OSError as exc:
        logger.warning(
            "Error reading repository context file",
            path=str(context_path),
            error=str(exc),
        )
        return None, None


def build_discovery_context(
    org_name: Optional[str],
    local_path: Optional[str],
    org_context_override: Optional[str] = None,
    repo_context_override: Optional[str] = None,
) -> DiscoveryContext:
    """Build a complete DiscoveryContext by loading and merging context files.

    This function handles context discovery with CLI override support:
    - If org_context_override is provided, it's used instead of loading from disk
    - If repo_context_override is provided, it's used instead of loading from disk
    - Otherwise, attempts to load from standard file locations

    Args:
        org_name: The organization/owner name for org-level context lookup.
        local_path: The local filesystem path to the cloned repository.
        org_context_override: Optional CLI-provided org context (bypasses file load).
        repo_context_override: Optional CLI-provided repo context (bypasses file load).

    Returns:
        A fully populated DiscoveryContext with all available context merged.
    """
    # Load or use override for org context
    if org_context_override is not None:
        org_content = org_context_override
        org_path = "<cli-override>"
        logger.info("Using CLI-provided organization context override")
    elif org_name:
        org_content, org_path = load_org_context(org_name)
    else:
        org_content, org_path = None, None

    # Load or use override for repo context
    if repo_context_override is not None:
        repo_content = repo_context_override
        repo_path = "<cli-override>"
        logger.info("Using CLI-provided repository context override")
    elif local_path:
        repo_content, repo_path = load_repo_context(local_path)
    else:
        repo_content, repo_path = None, None

    # Merge contexts
    merged = merge_contexts(org_content, repo_content)

    # Log summary of what was loaded
    logger.info(
        "Discovery context built",
        org_context_loaded=org_content is not None,
        repo_context_loaded=repo_content is not None,
        merged_context_length=len(merged) if merged else 0,
    )

    return DiscoveryContext(
        org_context=org_content,
        repo_context=repo_content,
        merged_context=merged if merged else None,
        org_context_path=org_path,
        repo_context_path=repo_path,
    )
