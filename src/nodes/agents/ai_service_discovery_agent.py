import os
from enum import Enum
from itertools import islice
from typing import List, Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.retry import ExponentialJitterParams
from pydantic import BaseModel, Field

from src.ai_provider.ai_provider import init_llm_by_provider
from src.logging.logging import get_logger

logger = get_logger(__name__)

class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class ServicesResult(BaseModel):
    path: str = Field(description="Directory path")
    name: str = Field(description="Service Name")
    language: int = Field(description="Main Programming Language")
    confidence: ConfidenceLevel = Field(
        description="Confidence level in service identification"
    )
    evidence: List[str] = Field(
        description="List of specific evidence found that supports the service identification (e.g., Dockerfile presence, main entry points, configuration files, dependency patterns)"
    )


class ListOfServices(BaseModel):
    services: List[ServicesResult]

def ai_service_discovery_agent(
    candidate_dirs: List[Dict],
    cicd_files: List[Dict],
    repo_path: str = ".",
    readme_lines: int = 20,
    context_signals: Optional[List[str]] = None
) -> List[Dict]:
    """
    Use LLM to choose which candidate directories in a repo are actual deployable services.
    - candidate_dirs: List of {"path": <str>, "package_file": <str>, "language": <str>}
    - cicd_files: List of {"path": <str>, "content": <str>}
    - context_signals: Strong deployment clues (optional)
    Returns: List of directories that are actual self-built services, augmented with LLM reasoning if desired.
    """
    logger.info("Initializing LLM for service discovery.")
    readme_content = ""
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = "".join(list(islice(f, readme_lines)))
        except Exception as e:
            logger.warning(f"Could not read README.md: {e}")

    # Gather candidate summary string
    dir_summary = "\n".join(
        [
            f"- Path: {entry['path']}, Package/Build file: {entry['package_file']}, Language: {entry.get('language', 'unknown')}"
            for entry in candidate_dirs
        ]
    )

    # Gather minimal summary of CI/CD/deploy files
    cicd_summary = "\n".join(
        [
            f"File: {cicd['path']}\n---\n{cicd['content'][:600]}\n---"
            for cicd in cicd_files
        ]
    )

    context_signals_str = ""
    if context_signals:
        context_signals_str = (
            "\nStrong deployment signals files present:\n" + "\n".join(context_signals)
        )

    prompt_text = """
    You are an expert DevOps engineer.
    Given candidate directories with package/build manager files, README content, and CI/CD/deployment workflows:
    Identify which directories are deployable services/applications built and managed by this repository.
    A 'deployable service' means a directory that:
      - Contains code intended to be built and deployed as a standalone application or microservice.
      - Has its own build/deploy configuration (e.g., Dockerfile, deployment YAML, or CI/CD workflow).
      - Is not a shared library, infrastructure-only folder, test/example, or documentation.
    For each deployable service, list:
      - Its directory path.
      - If the directory path is '.', 'app', or '', use the last part of the repository URL as the service name. For example, for 'https://github.com/leanix/secrets-provisioner', the service name MUST be 'secrets-provisioner'. Do not use placeholders or angle brackets; always use the actual name.
      - Main programming language.
    **IMPORTANT** The name should be the same as the path, unless you find definitive evidence that the name is different. (e.g. name of built docker image)
    If none, respond with a list containing one item, where the name of the service is the last part of the repository URL.
    Repository URL: <repo_url>
    Candidate directories:
        {dir_summary}
    README (first {readme_lines} lines):
        {readme_content}
        {context_signals_str}
    CI/CD and deployment file summaries:
        {cicd_summary}
        
    ### 3. Confidence Rubric (Must Follow Exactly)
    | Level    | Required Evidence                                                                              | What is **Insufficient**                                   |
    |----------|-----------------------------------------------------------------------------------------------|------------------------------------------------------------|
    | **High** | ≥1 *Deployment proof* artifact **and** it references the specific component (by path or name). | Any container or build file **alone**.                     |
    | **Medium** | Has *Potential Service Indicators* **and** is referenced by another service or compose stack **but lacks deployment proof**. | A single indicator with no cross-reference.                |
    | **Low**  | Exactly one potential indicator, and nothing else.                                             | —                                                          |
    | **None** | Does not meet the 'Low' threshold.                                                             | —                                                          |
    
    ## Output
        {format_instructions}
    """

    parser = JsonOutputParser(pydantic_object=ListOfServices)
    prompt = PromptTemplate(
        template=prompt_text,
        input_variables=["dir_summary", "readme_lines", "readme_content", "context_signals_str", "cicd_summary"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        llm = init_llm_by_provider()
        logger.debug(f"Prompt for LLM service discovery (truncated): {prompt_text[:700]}...")
        chain = prompt | llm.with_retry(
            exponential_jitter_params=ExponentialJitterParams(
                initial=2, max=30
            ),
            stop_after_attempt = 5

        ) | parser
        response = chain.invoke({"dir_summary": dir_summary, "readme_lines" : readme_lines, "readme_content": readme_content, "context_signals_str" : context_signals_str, "cicd_summary": cicd_summary})
        # Accepts: '[{"path": "integration-core", "name": "integration-core", "language": "java"}, ...]'
        logger.info(f"Service discovery LLM output: {response}")
        try:
            discovered_services = response["services"]
            assert isinstance(discovered_services, list)
        except Exception as e:
            logger.warning(f"Could not parse LLM response, defaulting to empty list. Error: {e}")
            discovered_services = []
        return discovered_services
    except Exception as e:
        logger.error(f"Exception during service discovery: {e}", exc_info=True)
        return []
