import os
from typing import Any

from github import Github, GithubException

from src.logging.logging import get_logger
from src.utils.url_helper import parse_github_url_to_repo_full_name

logger = get_logger(__name__)

def discover_codeowners_runnable(repo_root_url: str) -> str:
    """
    Get the content of the CODEOWNERS file in a repository.
    """
    logger.info(f"Fetching CODEOWNERS content for repo: {repo_root_url}")

    repo_full_name = parse_repo_full_name(repo_root_url)
    repo_obj = get_gh_repo_object(repo_full_name)
    codeowners_paths = [
        "CODEOWNERS",
        ".github/CODEOWNERS",
        "docs/CODEOWNERS"
    ]
    for path in codeowners_paths:
        try:
            file_content = repo_obj.get_contents(path).decoded_content.decode()
            logger.info(f"Found CODEOWNERS at {path}")
            return file_content
        except Exception:
            continue
    logger.warning("CODEOWNERS file not found.")
    return "CODEOWNERS file not found."

def parse_repo_full_name(repo_root_url: str) -> str:
    try:
        owner, repo = parse_github_url_to_repo_full_name(repo_root_url)
        repo_full_name = f"{owner}/{repo}"
        logger.info(f"Parsed repo full name: {repo_full_name}")
        return repo_full_name
    except ValueError as err:
        logger.error(f"Error parsing repo URL: {err}")
        return f"Error: {err}"

def get_gh_repo_object(repo_full_name: str) -> Any:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        logger.error("GITHUB_TOKEN not set.")
        return "Error: GITHUB_TOKEN not set."

    gh = Github(token)
    try:
        repo_obj = gh.get_repo(repo_full_name)
        logger.info(f"Fetched repo object for: {repo_full_name}")
        return repo_obj
    except GithubException as exc:
        logger.error(f"Error opening {repo_full_name!r}: {exc}")
        return f"Error opening {repo_full_name!r}: {exc}"