import shutil

from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger

logger = get_logger(__name__)


def delete_repo_runnable(state: RootRepoState) -> RootRepoState:
    """
    Delete the temp directory from  a Git repository
    Returns:
    - RootRepoState
    """
    logger.info(f"Deleting clone repo: {state.local_path}")

    try:

        shutil.rmtree(state.local_path)

        return state
    except Exception as exc:
        logger.error(f"Error deleting clone repository: {str(exc)}")
        raise exc
