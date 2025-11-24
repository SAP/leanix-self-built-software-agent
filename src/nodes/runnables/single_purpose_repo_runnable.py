from src.dto.state_dto import RootRepoState, SelfBuiltComponent, Owner, ComponentType, RepoType
from src.logging.logging import get_logger
from src.utils.url_helper import parse_github_url_to_repo_full_name

logger = get_logger(__name__)


def single_purpose_repo_inspector_runnable(state: RootRepoState) -> RootRepoState:
    """Ensure exactly one component named after the repo root URL."""
    try:
        _, repo = parse_github_url_to_repo_full_name(state.repo_root_url)
    except Exception as e:
        logger.warning("Bad repo URL %r: %s", state.repo_root_url, e)
        return state

    if state.self_built_software:
        c = state.self_built_software[0]
        c.name = repo
        c.path = ""
        c.display_url = c.display_url or state.repo_root_url
        c.evidence = state.repo_type_evidence
        c.confidence = "high"
        state.self_built_software[:] = [c]   # collapse to exactly one
    else:
        state.self_built_software.append(
            SelfBuiltComponent(
                name=repo,
                path="",
                display_url=state.repo_root_url,
                owner=Owner(),
                language=None,
                component_type=ComponentType.UNKNOWN,
                evidence=state.repo_type_evidence,
                confidence="high",
            )
        )

    state.repo_type = RepoType.SINGLE_PURPOSE_REPO
    return state