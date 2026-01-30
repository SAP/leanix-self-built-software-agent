"""Pytest fixtures and configuration for the test suite."""
from __future__ import annotations

import pytest

from src.dto.context_dto import DiscoveryContext


@pytest.fixture
def empty_context() -> DiscoveryContext:
    """A DiscoveryContext with all fields as None."""
    return DiscoveryContext()


@pytest.fixture
def context_with_org_only() -> DiscoveryContext:
    """A DiscoveryContext with only org context set."""
    return DiscoveryContext(
        org_context="Organization context content",
        org_context_path="~/.sbs-discovery/myorg.md",
    )


@pytest.fixture
def context_with_repo_only() -> DiscoveryContext:
    """A DiscoveryContext with only repo context set."""
    return DiscoveryContext(
        repo_context="Repository context content",
        repo_context_path="/path/to/repo/.sbs-discovery.md",
    )


@pytest.fixture
def full_context() -> DiscoveryContext:
    """A DiscoveryContext with all fields populated."""
    return DiscoveryContext(
        org_context="Organization context content",
        repo_context="Repository context content",
        merged_context="Merged content for testing",
        org_context_path="~/.sbs-discovery/myorg.md",
        repo_context_path="/path/to/repo/.sbs-discovery.md",
    )
