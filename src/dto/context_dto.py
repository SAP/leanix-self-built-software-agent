"""Data structures for user-provided discovery context.

This module defines the context model for user-provided hints that improve
AI discovery accuracy. Context can be provided at two levels:
- Organization level: ~/.sbs-discovery/{org}.md (local config)
- Repository level: .sbs-discovery.md in repo root

Repository context extends/overrides organization context.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class DiscoveryContext:
    """Container for user-provided discovery context.

    Attributes:
        org_context: Raw markdown from organization-level config file.
        repo_context: Raw markdown from repository's .sbs-discovery.md file.
        merged_context: Combined context ready for LLM consumption.
        org_context_path: Source path for debugging/logging.
        repo_context_path: Source path for debugging/logging.
    """

    org_context: Optional[str] = None
    repo_context: Optional[str] = None
    merged_context: Optional[str] = None
    org_context_path: Optional[str] = None
    repo_context_path: Optional[str] = None


def merge_contexts(org_context: Optional[str], repo_context: Optional[str]) -> str:
    """Merge organization and repository context into a single string.

    The merge follows an inheritance model where repository context extends
    and can override organization context. When both are present, they are
    concatenated with clear headers so the LLM can understand the hierarchy.

    Since repository context appears after organization context, the LLM will
    naturally weight repository-specific information more heavily (recency bias).

    Args:
        org_context: Raw markdown from organization-level config, or None.
        repo_context: Raw markdown from repository's .sbs-discovery.md, or None.

    Returns:
        Merged context string ready for LLM consumption.
        Empty string if both inputs are None or empty.
    """
    org = (org_context or "").strip()
    repo = (repo_context or "").strip()

    if not org and not repo:
        return ""

    if org and not repo:
        return org

    if repo and not org:
        return repo

    # Both present: concatenate with headers
    return f"""## Organization Context
{org}

## Repository Context
{repo}"""
