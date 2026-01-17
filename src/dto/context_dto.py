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
