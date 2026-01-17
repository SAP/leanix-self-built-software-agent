"""Tests for context_loader service module.

Tests the filesystem-based context discovery and loading functionality.
Uses tmp_path fixtures and monkeypatch to simulate filesystem conditions.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.context_loader import (
    ORG_CONTEXT_DIR,
    REPO_CONTEXT_FILENAME,
    load_org_context,
    load_repo_context,
    build_discovery_context,
)


# Sample context content for testing
SAMPLE_ORG_CONTEXT = """# Organization Context
This organization uses Python 3.13+ and follows strict typing guidelines.
All services should use structured logging.
"""

SAMPLE_REPO_CONTEXT = """# Repository Context
This is a discovery service that analyzes GitHub repositories.
Uses LangChain for AI orchestration.
"""


class TestLoadOrgContext:
    """Tests for load_org_context function."""

    def test_returns_content_and_path_when_file_exists(self, tmp_path: Path) -> None:
        """When org context file exists, returns (content, path) tuple."""
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            content, path = load_org_context("myorg")

        assert content == SAMPLE_ORG_CONTEXT
        assert path == str(org_file)

    def test_returns_none_none_when_file_missing(self, tmp_path: Path) -> None:
        """When org context file doesn't exist, returns (None, None)."""
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()  # Directory exists but file doesn't

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            content, path = load_org_context("nonexistent")

        assert content is None
        assert path is None

    def test_returns_none_none_when_org_name_empty(self) -> None:
        """When org_name is empty string, returns (None, None) without file access."""
        content, path = load_org_context("")
        assert content is None
        assert path is None

    def test_returns_none_none_when_directory_missing(self, tmp_path: Path) -> None:
        """When the .sbs-discovery directory doesn't exist, returns (None, None)."""
        nonexistent_dir = tmp_path / "nonexistent"

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", nonexistent_dir):
            content, path = load_org_context("someorg")

        assert content is None
        assert path is None

    def test_handles_permission_error_gracefully(self, tmp_path: Path) -> None:
        """When file exists but can't be read, returns (None, None)."""
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
                content, path = load_org_context("myorg")

        assert content is None
        assert path is None

    def test_handles_oserror_gracefully(self, tmp_path: Path) -> None:
        """When an OSError occurs reading file, returns (None, None)."""
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            with patch.object(Path, "read_text", side_effect=OSError("Disk error")):
                content, path = load_org_context("myorg")

        assert content is None
        assert path is None


class TestLoadRepoContext:
    """Tests for load_repo_context function."""

    def test_returns_content_and_path_when_file_exists(self, tmp_path: Path) -> None:
        """When repo context file exists, returns (content, path) tuple."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        context_file = repo_dir / REPO_CONTEXT_FILENAME
        context_file.write_text(SAMPLE_REPO_CONTEXT)

        content, path = load_repo_context(str(repo_dir))

        assert content == SAMPLE_REPO_CONTEXT
        assert path == str(context_file)

    def test_returns_none_none_when_file_missing(self, tmp_path: Path) -> None:
        """When .sbs-discovery.md doesn't exist in repo, returns (None, None)."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()  # Directory exists but no context file

        content, path = load_repo_context(str(repo_dir))

        assert content is None
        assert path is None

    def test_returns_none_none_when_local_path_empty(self) -> None:
        """When local_path is empty string, returns (None, None) without file access."""
        content, path = load_repo_context("")
        assert content is None
        assert path is None

    def test_returns_none_none_when_repo_directory_missing(self, tmp_path: Path) -> None:
        """When the repo directory doesn't exist, returns (None, None)."""
        nonexistent_repo = tmp_path / "nonexistent-repo"

        content, path = load_repo_context(str(nonexistent_repo))

        assert content is None
        assert path is None

    def test_handles_permission_error_gracefully(self, tmp_path: Path) -> None:
        """When file exists but can't be read, returns (None, None)."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        context_file = repo_dir / REPO_CONTEXT_FILENAME
        context_file.write_text(SAMPLE_REPO_CONTEXT)

        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            content, path = load_repo_context(str(repo_dir))

        assert content is None
        assert path is None

    def test_handles_oserror_gracefully(self, tmp_path: Path) -> None:
        """When an OSError occurs reading file, returns (None, None)."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        context_file = repo_dir / REPO_CONTEXT_FILENAME
        context_file.write_text(SAMPLE_REPO_CONTEXT)

        with patch.object(Path, "read_text", side_effect=OSError("Disk error")):
            content, path = load_repo_context(str(repo_dir))

        assert content is None
        assert path is None


class TestBuildDiscoveryContext:
    """Tests for build_discovery_context function."""

    def test_builds_context_with_both_files_present(self, tmp_path: Path) -> None:
        """When both org and repo context files exist, merges them."""
        # Set up org context
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        # Set up repo context
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        repo_file = repo_dir / REPO_CONTEXT_FILENAME
        repo_file.write_text(SAMPLE_REPO_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context("myorg", str(repo_dir))

        assert ctx.org_context == SAMPLE_ORG_CONTEXT
        assert ctx.repo_context == SAMPLE_REPO_CONTEXT
        assert ctx.merged_context is not None
        assert "Organization Context" in ctx.merged_context
        assert "Repository Context" in ctx.merged_context
        assert ctx.org_context_path == str(org_file)
        assert ctx.repo_context_path == str(repo_file)

    def test_builds_context_with_only_org_file(self, tmp_path: Path) -> None:
        """When only org context file exists, context has org only."""
        # Set up org context
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        # Empty repo (no context file)
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context("myorg", str(repo_dir))

        assert ctx.org_context == SAMPLE_ORG_CONTEXT
        assert ctx.repo_context is None
        assert ctx.merged_context == SAMPLE_ORG_CONTEXT.strip()
        assert ctx.org_context_path == str(org_file)
        assert ctx.repo_context_path is None

    def test_builds_context_with_only_repo_file(self, tmp_path: Path) -> None:
        """When only repo context file exists, context has repo only."""
        # No org context (empty dir)
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()

        # Set up repo context
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        repo_file = repo_dir / REPO_CONTEXT_FILENAME
        repo_file.write_text(SAMPLE_REPO_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context("myorg", str(repo_dir))

        assert ctx.org_context is None
        assert ctx.repo_context == SAMPLE_REPO_CONTEXT
        assert ctx.merged_context == SAMPLE_REPO_CONTEXT.strip()
        assert ctx.org_context_path is None
        assert ctx.repo_context_path == str(repo_file)

    def test_builds_empty_context_when_no_files_exist(self, tmp_path: Path) -> None:
        """When no context files exist, context has all None values."""
        # No org context
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()

        # No repo context
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context("myorg", str(repo_dir))

        assert ctx.org_context is None
        assert ctx.repo_context is None
        assert ctx.merged_context is None
        assert ctx.org_context_path is None
        assert ctx.repo_context_path is None

    def test_org_context_override_bypasses_file_loading(self, tmp_path: Path) -> None:
        """CLI org_context_override is used instead of loading from file."""
        # Set up org context file (should be ignored)
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        override_content = "Override org context"

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context(
                "myorg",
                str(tmp_path / "repo"),
                org_context_override=override_content,
            )

        assert ctx.org_context == override_content
        assert ctx.org_context_path == "<cli-override>"

    def test_repo_context_override_bypasses_file_loading(self, tmp_path: Path) -> None:
        """CLI repo_context_override is used instead of loading from file."""
        # Set up repo context file (should be ignored)
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        repo_file = repo_dir / REPO_CONTEXT_FILENAME
        repo_file.write_text(SAMPLE_REPO_CONTEXT)

        override_content = "Override repo context"

        ctx = build_discovery_context(
            None,
            str(repo_dir),
            repo_context_override=override_content,
        )

        assert ctx.repo_context == override_content
        assert ctx.repo_context_path == "<cli-override>"

    def test_both_overrides_bypass_all_file_loading(self, tmp_path: Path) -> None:
        """When both overrides are provided, no file loading occurs."""
        org_override = "CLI org"
        repo_override = "CLI repo"

        ctx = build_discovery_context(
            "someorg",
            str(tmp_path / "somerepo"),
            org_context_override=org_override,
            repo_context_override=repo_override,
        )

        assert ctx.org_context == org_override
        assert ctx.repo_context == repo_override
        assert ctx.org_context_path == "<cli-override>"
        assert ctx.repo_context_path == "<cli-override>"
        assert ctx.merged_context is not None
        assert "Organization Context" in ctx.merged_context
        assert "Repository Context" in ctx.merged_context

    def test_handles_none_org_name(self, tmp_path: Path) -> None:
        """When org_name is None, org context loading is skipped."""
        repo_dir = tmp_path / "my-repo"
        repo_dir.mkdir()
        repo_file = repo_dir / REPO_CONTEXT_FILENAME
        repo_file.write_text(SAMPLE_REPO_CONTEXT)

        ctx = build_discovery_context(None, str(repo_dir))

        assert ctx.org_context is None
        assert ctx.repo_context == SAMPLE_REPO_CONTEXT
        assert ctx.org_context_path is None

    def test_handles_none_local_path(self, tmp_path: Path) -> None:
        """When local_path is None, repo context loading is skipped."""
        org_dir = tmp_path / ".sbs-discovery"
        org_dir.mkdir()
        org_file = org_dir / "myorg.md"
        org_file.write_text(SAMPLE_ORG_CONTEXT)

        with patch("src.services.context_loader.ORG_CONTEXT_DIR", org_dir):
            ctx = build_discovery_context("myorg", None)

        assert ctx.org_context == SAMPLE_ORG_CONTEXT
        assert ctx.repo_context is None
        assert ctx.repo_context_path is None
