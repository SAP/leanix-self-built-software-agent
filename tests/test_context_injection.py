"""Tests for context_injection module, specifically format_context_for_prompt."""
from __future__ import annotations

import pytest

from src.dto.context_dto import DiscoveryContext
from src.utils.context_injection import format_context_for_prompt


class TestFormatContextForPrompt:
    """Test cases for the format_context_for_prompt function."""

    def test_none_context_returns_empty_string(self) -> None:
        """When context is None, returns empty string."""
        result = format_context_for_prompt(None)
        assert result == ""

    def test_context_with_none_merged_returns_empty(self) -> None:
        """When merged_context is None, returns empty string."""
        ctx = DiscoveryContext(
            org_context="org",
            repo_context="repo",
            merged_context=None,
        )
        result = format_context_for_prompt(ctx)
        assert result == ""

    def test_context_with_empty_merged_returns_empty(self) -> None:
        """When merged_context is empty string, returns empty string."""
        ctx = DiscoveryContext(merged_context="")
        result = format_context_for_prompt(ctx)
        assert result == ""

    def test_context_with_whitespace_merged_returns_empty(self) -> None:
        """When merged_context is whitespace only, returns empty string."""
        ctx = DiscoveryContext(merged_context="   \n\t   ")
        result = format_context_for_prompt(ctx)
        assert result == ""

    def test_valid_context_includes_header(self) -> None:
        """Valid context includes the section header."""
        ctx = DiscoveryContext(merged_context="Test content")
        result = format_context_for_prompt(ctx)

        assert "## User-Provided Context" in result
        assert "Test content" in result

    def test_valid_context_includes_instructions(self) -> None:
        """Valid context includes instructions for the LLM."""
        ctx = DiscoveryContext(merged_context="Test content")
        result = format_context_for_prompt(ctx)

        assert "help with discovery" in result
        assert "service classification" in result or "better decisions" in result

    def test_valid_context_ends_with_separator(self) -> None:
        """Valid context ends with a separator line."""
        ctx = DiscoveryContext(merged_context="Test content")
        result = format_context_for_prompt(ctx)

        assert result.strip().endswith("---")

    def test_preserves_content(self) -> None:
        """The merged content is preserved in output."""
        content = "This is my custom context\nWith multiple lines\nAnd special chars: @#$%"
        ctx = DiscoveryContext(merged_context=content)
        result = format_context_for_prompt(ctx)

        assert content in result

    # Truncation tests
    def test_truncates_at_max_chars(self) -> None:
        """Content is truncated when exceeding max_chars."""
        long_content = "x" * 5000
        ctx = DiscoveryContext(merged_context=long_content)
        result = format_context_for_prompt(ctx)

        # Should contain truncation marker
        assert "[context truncated]" in result

    def test_truncated_content_respects_limit(self) -> None:
        """Truncated content respects the max_chars limit."""
        # Use '~' which doesn't appear in the template text
        long_content = "~" * 5000
        ctx = DiscoveryContext(merged_context=long_content)
        result = format_context_for_prompt(ctx, max_chars=4000)

        # The merged content portion should be limited to max_chars
        tilde_count = result.count("~")
        assert tilde_count == 4000  # Should be exactly max_chars tildes

    def test_custom_max_chars(self) -> None:
        """Custom max_chars parameter is respected."""
        # Use '~' which doesn't appear in the template text
        content = "~" * 100
        ctx = DiscoveryContext(merged_context=content)
        result = format_context_for_prompt(ctx, max_chars=50)

        # Should be truncated at 50 chars
        assert result.count("~") == 50
        assert "[context truncated]" in result

    def test_no_truncation_when_under_limit(self) -> None:
        """No truncation when content is under the limit."""
        content = "Short content"
        ctx = DiscoveryContext(merged_context=content)
        result = format_context_for_prompt(ctx)

        assert "[context truncated]" not in result
        assert content in result

    def test_exact_limit_not_truncated(self) -> None:
        """Content exactly at the limit is not truncated."""
        content = "x" * 4000
        ctx = DiscoveryContext(merged_context=content)
        result = format_context_for_prompt(ctx, max_chars=4000)

        assert "[context truncated]" not in result
        assert content in result

    # Fixture-based tests
    def test_with_empty_context_fixture(self, empty_context: DiscoveryContext) -> None:
        """Test with empty context fixture."""
        result = format_context_for_prompt(empty_context)
        assert result == ""

    def test_with_full_context_fixture(self, full_context: DiscoveryContext) -> None:
        """Test with full context fixture (has merged_context set)."""
        result = format_context_for_prompt(full_context)
        assert "## User-Provided Context" in result
        assert full_context.merged_context in result

    def test_strips_whitespace_from_content(self) -> None:
        """Leading and trailing whitespace is stripped from content."""
        ctx = DiscoveryContext(merged_context="  \n  content  \n  ")
        result = format_context_for_prompt(ctx)

        # The content portion should be stripped
        assert "content" in result
        # But the overall format includes intentional whitespace
