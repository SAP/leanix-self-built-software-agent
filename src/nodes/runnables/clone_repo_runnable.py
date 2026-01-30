import os
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger

logger = get_logger(__name__)

def clone_repo_tool_runnable(state: RootRepoState) -> RootRepoState:
    """
    Clone a Git repository to repo temp directory using GITHUB_TOKEN for authentication.
    - Uses default branch if none specified.
    Returns:
    - Updated RootRepoState with local_path set to the cloned repo path.
    """
    repo_url = state.repo_root_url
    logger.info(f"Starting clone check for repo: {repo_url}")

    try:
        # Extract repo name from URL
        if repo_url.endswith('.git'):
            repo_name = repo_url.split('/')[-1][:-4]  # Remove .git suffix
        else:
            repo_name = repo_url.split('/')[-1]

        # Create repo temp directory at os temp directory
        temp_dir = os.path.join(tempfile.gettempdir(), repo_name)
        os.makedirs(temp_dir, exist_ok=True)
        local_path = temp_dir

        # Get GitHub token from environment
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            raise Exception("GITHUB_TOKEN environment variable is not set")

        # Convert GitHub URL to authenticated URL
        authenticated_url = _get_authenticated_url(repo_url, github_token)

        # Remove existing directory if it exists but is not a valid git repo
        if os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)

        logger.info(f"Cloning {repo_url} to {local_path}")

        # Execute git clone with authenticated URL
        result = subprocess.run(
            ["git", "clone", authenticated_url, local_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            # Cleanup on failure
            if os.path.exists(local_path):
                shutil.rmtree(local_path, ignore_errors=True)
            logger.error(f"Git clone failed: {result.stderr}")
            raise Exception(f"Git clone failed: {result.stderr}")

        # Verify the clone was successful
        if not os.path.exists(local_path) or not os.path.exists(os.path.join(local_path, ".git")):
            if os.path.exists(local_path):
                shutil.rmtree(local_path, ignore_errors=True)
            raise Exception("Repository was not cloned properly")

        logger.info(f"Successfully cloned {repo_url} to {local_path}")

        # Update state with local path
        state.local_path = local_path

        return state

    except subprocess.TimeoutExpired:
        logger.error("Git clone operation timed out after 5 minutes")
        raise Exception("Git clone operation timed out")
    except Exception as exc:
        logger.error(f"Error during clone: {str(exc)}")
        raise exc

def _get_authenticated_url(repo_url: str, token: str) -> str:
    """
    Convert a GitHub repository URL to an authenticated URL using the provided token.

    Args:
        repo_url: The original repository URL (https://github.com/user/repo)
        token: The GitHub personal access token

    Returns:
        Authenticated URL in format: https://token@github.com/user/repo
    """
    parsed = urlparse(repo_url)

    if parsed.hostname != 'github.com':
        # If it's not GitHub, return original URL
        return repo_url

    # Create authenticated URL: https://token@github.com/path
    authenticated_url = f"https://{token}@{parsed.hostname}{parsed.path}"

    return authenticated_url
