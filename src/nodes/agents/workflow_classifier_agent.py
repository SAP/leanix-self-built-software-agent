import os
from itertools import islice
from typing import Literal, List, Optional

from src.ai_provider.ai_provider import init_llm_by_provider
from src.logging.logging import get_logger

logger = get_logger(__name__)

def workflow_classifier_agent(
    workflow_content: str,
    workflow_path: str,
    repo_path: str = ".",
    readme_lines: int = 20,
    strong_signals: Optional[List[str]] = None
) -> Literal["deployment", "tooling", "unknown"]:
    """
    Use LLM to classify a workflow file as deployment or tooling, including the first part of the README for context,
    the workflow file name/path, and any strong deployment signals found in the repo.
    """
    logger.info("Initializing LLM for workflow classification.")
    readme_content = ""
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = "".join(list(islice(f, readme_lines)))
        except Exception as e:
            logger.warning(f"Could not read README.md: {e}")

    strong_signals_str = ""
    if strong_signals:
        strong_signals_str = (
            "\nStrong deployment signals detected in this repository (file names):\n"
            + "\n".join(strong_signals)
        )

    try:
        llm = init_llm_by_provider()
        prompt = (
            "You are an expert in DevOps and CI/CD. "
            "Given the following GitHub Actions workflow file content, its file name and path, "
            "the first part of the repository's README, and a list of strong deployment signals (if any), "
            "classify the workflow as either a 'deployment workflow' (a workflow that directly deploys or releases an application or service to a runtime environment, such as Kubernetes, cloud, or production/staging servers), "
            "a 'tooling workflow' (automation, migration, provisioning, code quality, reusable or template workflows, or similar tasks that do NOT directly deploy or release applications/services), "
            "or 'unknown' if unclear.\n"
            "If the workflow only calls other reusable workflows (using 'uses: ./.github/workflows/xyz.yml') and does not itself contain deployment or release steps, classify it as 'tooling'.\n"
            "If the workflow is designed to be called by other workflows (e.g., uses 'workflow_call'), classify it as 'tooling' unless it directly deploys something itself.\n"
            "If the workflow only builds and publishes documentation or static sites (e.g., to GitHub Pages), classify it as 'tooling'.\n"
            "Respond with only one word: deployment, tooling, or unknown.\n"
            f"Workflow file path: {workflow_path}\n"
            f"README (first {readme_lines} lines):\n{readme_content}\n"
            f"{strong_signals_str}\n"
            "Workflow content:\n"
            f"{workflow_content}"
        )
        logger.debug(f"Prompt for classification (truncated): {prompt[:500]}...")
        response = llm.invoke(prompt)
        classification = response.content.strip().lower()
        logger.info(f"Workflow classified as: {classification}")
        return classification
    except Exception as e:
        logger.error(f"Exception during workflow classification: {e}", exc_info=True)
        return "unknown"
