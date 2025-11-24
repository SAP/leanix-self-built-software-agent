from pathlib import Path
from typing import List

from src.dto.state_dto import RootRepoState, SelfBuiltComponent, TechStack
from src.nodes.agents.tech_stack_agent import tech_stack_agent
from src.logging.logging import get_logger

logger = get_logger(__name__)

PACKAGE_MANAGER_FILES = [
    "pom.xml", "build.gradle", "build.gradle.kts", "package.json", "requirements.txt",
    "pyproject.toml", "setup.py", "Pipfile", "poetry.lock", "composer.json", "Gemfile",
    "go.mod", "Cargo.toml"
]

def detect_tech_stack_runnable(state: RootRepoState) -> RootRepoState:
    """
    For each self-built component, find package manager files and extract tech stack using LLM agent.
    """
    if not state.local_path:
        logger.warning("No local path available for tech stack analysis")
        return state

    repo_path = Path(state.local_path)
    for component in state.self_built_software:
        comp_path = repo_path / component.path
        if not comp_path.exists():
            logger.warning(f"Component path does not exist: {comp_path}")
            continue

        tech_stacks: List[TechStack] = []
        for pm_file in PACKAGE_MANAGER_FILES:
            found_files = list(comp_path.glob(pm_file))
            for file_path in found_files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    result = tech_stack_agent(content)
                    logger.info(f"Tech stack agent result for {file_path}: {result}")
                    for stack_item in getattr(result, "tech_stacks", result.get("tech_stacks", [])):
                        tech_stacks.append(TechStack(
                            name=stack_item["name"] if isinstance(stack_item, dict) else stack_item.name,
                            version=stack_item["version"] if isinstance(stack_item, dict) else stack_item.version,
                            confidence=stack_item["confidence"] if isinstance(stack_item, dict) else stack_item.confidence,
                            evidence=stack_item["evidence"],
                        ))
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {e}")

        component.tech_stacks = tech_stacks
        logger.info(f"Extracted tech stack for {component.name}: {[f'{s.name} {s.version}' for s in component.tech_stacks]}")

    return state