import os
from collections import Counter
from typing import Literal, TypedDict

from github import Github, GithubException
from langchain_core.tools import tool

from src.logging.logging import get_logger
from src.utils.url_helper import parse_github_url_to_repo_full_name

logger = get_logger(__name__)

BUILD_MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "pom.xml",
    "go.mod", "Cargo.toml", "build.gradle", "build.gradle.kts",
    "requirements.txt",
}
DOCKERFILE_NAMES = {"Dockerfile", "dockerfile"}

RepoType = Literal["mono-repo", "single-purpose-repo"]

class RepoClassification(TypedDict):
    repo_root: str         # canonical GitHub repo URL
    repo_type: RepoType    # the classification result


@tool("classify_repo_type", return_direct=True)
def classify_repo_type_tool(repo_root_url: str) -> RepoClassification:
    """
    Decide whether a GitHub repo is a *mono-repo* or *single-purpose-repo*
    by looking for build manifests / Dockerfiles in the root and one-level-deep
    sub-directories.
    """

    try:
        owner, repo = parse_github_url_to_repo_full_name(repo_root_url)
        repo_full_name = f"{owner}/{repo}"
    except ValueError as err:
        return f"Error: {err}"

    logger.info("↪️  classify_repo_type_tool(%s)", repo_full_name)

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        return "Error: GITHUB_TOKEN not set."

    gh = Github(token)
    try:
        repo = gh.get_repo(repo_full_name)
    except GithubException as exc:
        return f"Error opening {repo_full_name!r}: {exc}"

    try:
        tree = repo.get_git_tree(repo.default_branch, recursive=True).tree
    except GithubException as exc:
        return f"Error fetching git tree: {exc}"

    def depth(path: str) -> int:
        return len(path.split("/"))

    manifest_hits, docker_hits = 0, 0
    per_dir_hits = Counter()

    for entry in tree:
        if entry.type != "blob" or depth(entry.path) > 3:
            continue

        filename = entry.path.rsplit("/", 1)[-1]
        top_dir = entry.path.split("/", 1)[0] if depth(entry.path) == 2 else ""

        if filename in BUILD_MANIFESTS:
            manifest_hits += 1
            per_dir_hits[top_dir] += 1
        elif filename in DOCKERFILE_NAMES:
            docker_hits += 1
            per_dir_hits[top_dir] += 1

    logger.info("📦 manifests=%s dockerfiles=%s dirs_with_hits=%s",
                manifest_hits, docker_hits, len(per_dir_hits))

    # ── decide ────────────────────────────────────────────────
    repo_type: RepoType
    if manifest_hits > 1 or docker_hits > 1 or len(per_dir_hits) > 1:
        repo_type = "mono-repo"
    else:
        repo_type = "single-purpose-repo"

    # ── return structured result ───────────────────────────────
    return RepoClassification(repo_root=repo_root_url, repo_type=repo_type)
