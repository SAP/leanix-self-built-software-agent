"""Tests for load_context_runnable module, specifically _extract_org_from_url."""
from __future__ import annotations

import pytest

from src.nodes.runnables.load_context_runnable import _extract_org_from_url


class TestExtractOrgFromUrl:
    """Test cases for the _extract_org_from_url function."""

    # HTTPS URL formats
    def test_https_basic_url(self) -> None:
        """Extract org from basic HTTPS GitHub URL."""
        result = _extract_org_from_url("https://github.com/myorg/myrepo")
        assert result == "myorg"

    def test_https_with_git_extension(self) -> None:
        """Extract org from HTTPS URL with .git extension."""
        result = _extract_org_from_url("https://github.com/myorg/myrepo.git")
        assert result == "myorg"

    def test_https_with_www(self) -> None:
        """Extract org from HTTPS URL with www prefix."""
        result = _extract_org_from_url("https://www.github.com/myorg/myrepo")
        assert result == "myorg"

    def test_https_with_trailing_slash(self) -> None:
        """Extract org from HTTPS URL with trailing slash."""
        result = _extract_org_from_url("https://github.com/myorg/myrepo/")
        assert result == "myorg"

    # SSH URL formats
    def test_ssh_basic_url(self) -> None:
        """Extract org from basic SSH GitHub URL."""
        result = _extract_org_from_url("git@github.com:myorg/myrepo.git")
        assert result == "myorg"

    def test_ssh_without_git_extension(self) -> None:
        """Extract org from SSH URL without .git extension."""
        result = _extract_org_from_url("git@github.com:myorg/myrepo")
        assert result == "myorg"

    # Edge cases - should return None
    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        result = _extract_org_from_url("")
        assert result is None

    def test_none_returns_none(self) -> None:
        """None input returns None (if function accepts it)."""
        # Note: The function signature says str, but implementation handles None
        result = _extract_org_from_url(None)  # type: ignore[arg-type]
        assert result is None

    def test_gitlab_url_returns_none(self) -> None:
        """Non-GitHub URL (GitLab) returns None."""
        result = _extract_org_from_url("https://gitlab.com/org/repo")
        assert result is None

    def test_bitbucket_url_returns_none(self) -> None:
        """Non-GitHub URL (Bitbucket) returns None."""
        result = _extract_org_from_url("https://bitbucket.org/org/repo")
        assert result is None

    def test_invalid_url_returns_none(self) -> None:
        """Invalid URL returns None."""
        result = _extract_org_from_url("invalid-url")
        assert result is None

    def test_just_domain_returns_none(self) -> None:
        """GitHub domain without path returns None."""
        result = _extract_org_from_url("https://github.com")
        assert result is None

    def test_github_with_only_slash_returns_none(self) -> None:
        """GitHub domain with only slash returns None."""
        result = _extract_org_from_url("https://github.com/")
        assert result is None

    # Various org/repo name formats
    def test_org_with_hyphen(self) -> None:
        """Extract org containing hyphen."""
        result = _extract_org_from_url("https://github.com/my-org/my-repo")
        assert result == "my-org"

    def test_org_with_numbers(self) -> None:
        """Extract org containing numbers."""
        result = _extract_org_from_url("https://github.com/org123/repo456")
        assert result == "org123"

    def test_single_char_org(self) -> None:
        """Extract single character org name."""
        result = _extract_org_from_url("https://github.com/x/repo")
        assert result == "x"

    def test_long_org_name(self) -> None:
        """Extract long organization name."""
        long_org = "very-long-organization-name-that-is-valid"
        result = _extract_org_from_url(f"https://github.com/{long_org}/repo")
        assert result == long_org

    # URL with additional path segments
    def test_url_with_additional_path_segments(self) -> None:
        """Extract org even when URL has additional path segments."""
        result = _extract_org_from_url("https://github.com/myorg/myrepo/tree/main")
        assert result == "myorg"

    def test_url_with_blob_path(self) -> None:
        """Extract org from URL pointing to a file."""
        result = _extract_org_from_url(
            "https://github.com/myorg/myrepo/blob/main/README.md"
        )
        assert result == "myorg"
