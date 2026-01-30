import os
from collections import Counter
from typing import Literal

from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger

logger = get_logger(__name__)

BUILD_MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "pom.xml",
    "go.mod", "Cargo.toml", "build.gradle", "build.gradle.kts",
    "requirements.txt",
}
DOCKERFILE_NAMES = {"Dockerfile", "dockerfile"}

RepoType = Literal["mono-repo", "single-purpose-repo"]


def classify_repo_type_runnable(state: RootRepoState) -> RootRepoState:
    """
    Decide whether a locally cloned repo is a *mono-repo* or *single-purpose-repo*
    by looking for build manifests / Dockerfiles in the root and one-level-deep
    sub-directories.
    """

    if not state.local_path:
        raise ValueError("local_path is required but not set in state")

    if not os.path.exists(state.local_path):
        raise ValueError(f"Local repository path does not exist: {state.local_path}")

    logger.info(f"↪️ classify_repo_type_runnable({state.local_path})")

    def get_depth(path: str, base_path: str) -> int:
        """Calculate the depth of a file relative to the base path"""
        rel_path = os.path.relpath(path, base_path)
        if rel_path == ".":
            return 0
        return len(rel_path.split(os.sep))

    manifest_hits, docker_hits = 0, 0
    per_dir_hits = Counter()

    # Walk through the repository directory
    for root, dirs, files in os.walk(state.local_path):
        # Skip .git directories and other hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        depth = get_depth(root, state.local_path)

        # Only look at root level (depth 0) and up to 3 levels deep to match original tool behavior
        # Skip deeper directories to avoid scanning too much
        if depth > 3:
            dirs.clear()  # Don't recurse further
            continue

        for filename in files:
            # Skip hidden files
            if filename.startswith('.'):
                continue

            file_path = os.path.join(root, filename)

            # Determine the top-level directory for this file
            if depth == 0:
                top_dir = ""  # Root level
            else:
                # Get the immediate subdirectory under root
                rel_path = os.path.relpath(root, state.local_path)
                top_dir = rel_path.split(os.sep)[0]

            if filename in BUILD_MANIFESTS:
                manifest_hits += 1
                per_dir_hits[top_dir] += 1
                logger.debug(f"Found build manifest: {file_path}")
            elif filename in DOCKERFILE_NAMES:
                docker_hits += 1
                per_dir_hits[top_dir] += 1
                logger.debug(f"Found Dockerfile: {file_path}")

    logger.info(f"📦 manifests={manifest_hits} dockerfiles={docker_hits} dirs_with_hits={len(per_dir_hits)}")
    logger.debug(f"Directories with hits: {dict(per_dir_hits)}")

    # Decide repo type based on weighted scoring system
    # Score calculation (more conservative approach):
    # - Multiple manifests: Only score if significantly more than typical single-purpose
    # - Multiple dockerfiles: Strong indicator of multiple services
    # - Multiple directories: Only score if substantial separation
    score = 0

    # Add points for multiple build manifests
    # Single-purpose repos can have 2 manifests (e.g., main + tool/plugin)
    # Require 3+ manifests OR 2+ manifests in different directories
    if manifest_hits >= 3:
        score += 2  # Strong indicator
    elif manifest_hits == 2 and len(per_dir_hits) > 1:
        score += 1  # Moderate indicator

    # Add points for multiple dockerfiles (strong indicator of multiple services)
    if docker_hits > 1:
        score += 2

    # Add points for build artifacts spread across multiple directories
    # But require substantial distribution (3+ directories for strong signal)
    if len(per_dir_hits) >= 3:
        score += 2
    elif len(per_dir_hits) == 2:
        score += 1

    logger.info(f"🏆 Calculated score: {score} (manifests: {manifest_hits}, dockerfiles: {docker_hits}, directories: {len(per_dir_hits)})")

    repo_type: RepoType
    # Raise the threshold to be more conservative
    if score >= 3:
        repo_type = "mono-repo"
    else:
        repo_type = "single-purpose-repo"

    logger.info(f"Classified repository as: {repo_type}")

    # Update state with the classification result
    state.repo_type = repo_type
    state.repo_type_evidence = f"manifests={manifest_hits} dockerfiles={docker_hits} dirs_with_hits={len(per_dir_hits)}"

    return state
