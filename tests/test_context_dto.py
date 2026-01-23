"""Tests for context_dto module, specifically merge_contexts function."""
from __future__ import annotations

import pytest

from src.dto.context_dto import DiscoveryContext, merge_contexts


class TestMergeContexts:
    """Test cases for the merge_contexts function."""

    def test_both_none_returns_empty_string(self) -> None:
        """When both inputs are None, returns empty string."""
        result = merge_contexts(None, None)
        assert result == ""

    def test_org_only_returns_org(self) -> None:
        """When only org context is provided, returns just org content."""
        org_content = "This is org context"
        result = merge_contexts(org_content, None)
        assert result == org_content

    def test_repo_only_returns_repo(self) -> None:
        """When only repo context is provided, returns just repo content."""
        repo_content = "This is repo context"
        result = merge_contexts(None, repo_content)
        assert result == repo_content

    def test_both_present_concatenates_with_headers(self) -> None:
        """When both are present, concatenates with clear headers."""
        org_content = "org"
        repo_content = "repo"
        result = merge_contexts(org_content, repo_content)

        expected = """## Organization Context
org

## Repository Context
repo"""
        assert result == expected

    def test_whitespace_only_org_treated_as_empty(self) -> None:
        """Whitespace-only org context is treated as empty."""
        result = merge_contexts("   ", None)
        assert result == ""

    def test_whitespace_only_repo_treated_as_empty(self) -> None:
        """Whitespace-only repo context is treated as empty."""
        result = merge_contexts(None, "   \n\t  ")
        assert result == ""

    def test_both_whitespace_only_returns_empty(self) -> None:
        """When both inputs are whitespace-only, returns empty string."""
        result = merge_contexts("  ", "  ")
        assert result == ""

    def test_empty_string_org_treated_as_none(self) -> None:
        """Empty string org context behaves same as None."""
        result = merge_contexts("", "repo content")
        assert result == "repo content"

    def test_empty_string_repo_treated_as_none(self) -> None:
        """Empty string repo context behaves same as None."""
        result = merge_contexts("org content", "")
        assert result == "org content"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Content is stripped before processing."""
        result = merge_contexts("  org  ", "  repo  ")
        expected = """## Organization Context
org

## Repository Context
repo"""
        assert result == expected

    def test_preserves_internal_whitespace(self) -> None:
        """Internal whitespace in content is preserved."""
        org = "line 1\n\nline 3"
        repo = "para 1\n\npara 2"
        result = merge_contexts(org, repo)

        assert "line 1\n\nline 3" in result
        assert "para 1\n\npara 2" in result


class TestDiscoveryContextDataclass:
    """Test cases for the DiscoveryContext dataclass."""

    def test_default_values_are_none(self) -> None:
        """All fields default to None."""
        ctx = DiscoveryContext()
        assert ctx.org_context is None
        assert ctx.repo_context is None
        assert ctx.merged_context is None
        assert ctx.org_context_path is None
        assert ctx.repo_context_path is None

    def test_can_set_all_fields(self) -> None:
        """All fields can be set via constructor."""
        ctx = DiscoveryContext(
            org_context="org",
            repo_context="repo",
            merged_context="merged",
            org_context_path="/org/path",
            repo_context_path="/repo/path",
        )
        assert ctx.org_context == "org"
        assert ctx.repo_context == "repo"
        assert ctx.merged_context == "merged"
        assert ctx.org_context_path == "/org/path"
        assert ctx.repo_context_path == "/repo/path"

    def test_uses_slots(self) -> None:
        """DiscoveryContext uses slots for memory efficiency."""
        ctx = DiscoveryContext()
        assert hasattr(ctx, "__slots__")
        # Should not be able to add arbitrary attributes
        with pytest.raises(AttributeError):
            ctx.arbitrary_attr = "should fail"  # type: ignore[attr-defined]
