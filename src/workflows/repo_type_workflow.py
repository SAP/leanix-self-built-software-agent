from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.nodes.agents.individual_contributors_service_agent import individual_contributors_service_agent
from src.nodes.agents.languages_service_agent import languages_service_agent
from src.nodes.agents.extract_team_owners_agent import extract_team_owners_agent
from src.nodes.agents.mono_repo_services_inspector_agent import monorepo_inspector_agent
from src.nodes.agents.repo_type_agent import repo_type_inspector_agent
from src.dto.state_dto import RootRepoState
from src.nodes.router.routers import route_on_repo_type, route_on_deployable
from src.nodes.runnables.classify_repo_type_runnable import classify_repo_type_runnable
from src.nodes.runnables.clone_repo_runnable import clone_repo_tool_runnable
from src.nodes.runnables.delete_repo_runnable import delete_repo_runnable
from src.nodes.runnables.load_context_runnable import load_context_runnable
from src.nodes.runnables.detect_deployment_signals_runnable import deployment_signals_detection_runnable
from src.nodes.runnables.sbs_name_discovery_runnable import sbs_name_discovery_runnable
from src.nodes.runnables.single_purpose_repo_runnable import single_purpose_repo_inspector_runnable
from src.nodes.runnables.detect_tech_stack_runnable import detect_tech_stack_runnable


def generate_repo_type_workflow() -> CompiledStateGraph:
    # Create a new graph
    graph = StateGraph(RootRepoState)

    # Add your agent as a node
    graph.add_node("repo_type_inspector_agent", repo_type_inspector_agent)
    graph.add_node("monorepo_inspector_agent", monorepo_inspector_agent)
    graph.add_node("single_purpose_repo_inspector_runnable", single_purpose_repo_inspector_runnable)
    graph.add_node("clone_repo_tool_runnable", clone_repo_tool_runnable)
    graph.add_node("deployment_signals_detection_runnable", deployment_signals_detection_runnable)
    graph.add_node("classify_repo_type_runnable", classify_repo_type_runnable)
    graph.add_node("sbs_name_discovery_runnable", sbs_name_discovery_runnable)
    graph.add_node("languages_service_agent", languages_service_agent)
    graph.add_node("extract_team_owners_agent", extract_team_owners_agent)
    graph.add_node("delete_repo_runnable", delete_repo_runnable)
    graph.add_node("individual_contributors_service_agent", individual_contributors_service_agent)
    graph.add_node("detect_tech_stack_runnable", detect_tech_stack_runnable)
    graph.add_node("load_context_runnable", load_context_runnable)

    # Set the starting node
    graph.set_entry_point("clone_repo_tool_runnable")

    # After cloning, load user-provided discovery context
    graph.add_edge("clone_repo_tool_runnable", "load_context_runnable")

    # After loading context, detect deployment signals
    graph.add_edge("load_context_runnable", "deployment_signals_detection_runnable")

    # Route based on deployable status - if deployable continue to classify repo type, otherwise end
    graph.add_conditional_edges(
        "deployment_signals_detection_runnable",
        route_on_deployable,
        [
            "classify_repo_type_runnable",
            "delete_repo_runnable",
        ],
    )

    # After classifying repo type, route based on mono vs single purpose repo
    graph.add_conditional_edges(
        "classify_repo_type_runnable",
        route_on_repo_type,
        [
            "sbs_name_discovery_runnable",
            "single_purpose_repo_inspector_runnable",
        ],
    )

    # Both final nodes end the workflow

 # graph.add_edge("agent", END) Is this deployable? (look at the information you are provided and decide is this is a sbs
    # Given that this is a mono-repo, where will find all self-built software names and which dir we can surely ignore

    graph.add_edge("sbs_name_discovery_runnable", "languages_service_agent")
    graph.add_edge("single_purpose_repo_inspector_runnable", "languages_service_agent")
    graph.add_edge("languages_service_agent", "extract_team_owners_agent")
    graph.add_edge("extract_team_owners_agent", "individual_contributors_service_agent")
    graph.add_edge("individual_contributors_service_agent", "detect_tech_stack_runnable")
    graph.add_edge("detect_tech_stack_runnable", "delete_repo_runnable")
    graph.add_edge("delete_repo_runnable", END)

    # Compile the graph
    return graph.compile()
