from langchain.agents import initialize_agent

from src.ai_provider.ai_provider import init_llm_by_provider
from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.tools.classify_repo_type_tool import classify_repo_type_tool

logger = get_logger(__name__)

def repo_type_inspector_agent(state: RootRepoState) -> RootRepoState:
    """Takes repository data, and determines if a repository is a mono-repo or single-purpose-repo"""

    llm = init_llm_by_provider()
    tools = [classify_repo_type_tool]
    repo_root_url = state.repo_root_url

    prompt = (
        "You have access to a tool `classify_repo_type (repo_root_url)`\n"
        f"Decide whether the GitHub repo with the url `{repo_root_url}` is\n"
        "`monorepo` or `single-purpose-service`.\n"
        "Use the classify_repo_type_tool tool then answer succinctly.\n"
    )
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        verbose=True
    )

    response = agent.invoke(
        prompt,
        return_only_outputs=True
    )

    logger.info(response)
    state.repo_type = response["output"].get("repo_type", "").strip().lower()
    state.repo_root_url = response["output"].get("repo_root",  state.repo_root_url)
    logger.info("Returning " + state.repo_type)
    return state




