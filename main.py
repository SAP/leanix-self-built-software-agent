from __future__ import annotations

import os

import requests

from src.db.models import init_db
from src.logging.logging import configure_structlog, get_logger
from src.converter.converters import coerce_state
from src.dto.state_dto import RootRepoState
from src.services.organizations import create_org_if_not_exists
from src.services.repositories import create_repository
from src.workflows.repo_type_workflow import generate_repo_type_workflow

SERVICE_NAME = os.getenv("LOGFIRE_SERVICE_NAME", "sbs-ai-discovery")
GITHUB_ORG = os.getenv('GITHUB_ORG')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

configure_structlog()
logger = get_logger(__name__)

def fetch_github_repos() -> list:
    """
    Fetch all repositories for the GitHub organization specified in the GITHUB_ORG environment variable.
    Handles rate limiting with exponential backoff and logs progress.
    Returns:
        List of repository dicts.
    """

    if not GITHUB_TOKEN:
        raise Exception("GITHUB_TOKEN environment variable is not set")
    if not GITHUB_ORG:
        raise Exception("GITHUB_ORG environment variable is not set")

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    repos = []
    page = 1
    backoff = 1

    while True:
        url = f"https://api.github.com/orgs/{GITHUB_ORG}/repos?per_page=100&page={page}"
        logger.info(f"Fetching repositories from: {url}")
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 403 and "rate limit" in response.text.lower():
                logger.warning("GitHub API rate limit reached, backing off...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            repos.extend([repo for repo in data if not repo.get("archived", False)])
            page += 1
            backoff = 1
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            break
        except Exception as exc:
            logger.error(f"Unexpected error: {str(exc)}")
            break

    logger.info(f"Fetched {len(repos)} repositories from organization {GITHUB_ORG}")
    return repos

def main() -> None:
    init_db()
    logger.info("Starting main workflow.")

    create_org_if_not_exists(GITHUB_ORG)
    logger.info(f"Fetching repositories for organization: {GITHUB_ORG}")
    repos = fetch_github_repos()
    logger.info(f"Processing {len(repos)} repositories.")
    for repo in repos:
        repo_root_url = repo.get("html_url")
        logger.info(f"Processing repository: {repo_root_url}")
        initial_state = RootRepoState(repo_root_url=repo_root_url)
        response = generate_repo_type_workflow().invoke(initial_state, config={})
        pred_state = coerce_state(response)
        logger.info(f"Predicted state for repo {repo_root_url}: {pred_state}")
        create_repository(pred_state)
    logger.info(f"Finished processing {len(repos)} repositories.")


if __name__ == "__main__":
    main()
