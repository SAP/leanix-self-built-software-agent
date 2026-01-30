from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger

logger = get_logger(__name__)

def route_on_repo_type(state: RootRepoState) -> str:
    """
    Route based on whether the repository is mono-repo or single-purpose-repo.
    If mono-repo, proceed to find all self-built software names, otherwise find single  name
    """
    nxt = ("sbs_name_discovery_runnable"
           if state.repo_type == "mono-repo"
           else "single_purpose_repo_inspector_runnable")
    logger.info("🔀 routing to %s based on repo_type=%s",
                nxt, state.repo_type)
    return nxt

def route_on_deployable(state: RootRepoState) -> str:
    """
    Route based on whether the repository is deployable.
    If deployable, proceed to classify repo type, otherwise end workflow.
    """
    if state.deployable:
        logger.info(f"Repository {state.repo_root_url} is deployable, proceeding to classify repo type")
        return "classify_repo_type_runnable"
    else:
        logger.info(f"Repository {state.repo_root_url} is not deployable, ending workflow")
        return "delete_repo_runnable"
