from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.ai_provider.ai_provider import init_llm_by_provider
from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.nodes.runnables.get_languages_and_package_manager_runnable import get_languages_and_package_manager_runnable

logger = get_logger(__name__)

class LanguageResult(BaseModel):
    name: str = Field(description="Language Name")
    version: str = Field(description="Language Version")
    reason: str = Field(description="Reason for the decision, base on the files found on the service")

def languages_service_agent(state: RootRepoState, config: RunnableConfig) -> RootRepoState:
    """Takes repository data, and find languages for each service on the repository"""

    # Get model name from config if provided
    model_name = config.get("configurable", {}).get("model_name") if config else None
    llm = init_llm_by_provider(model_name)
    parser = JsonOutputParser(pydantic_object=LanguageResult)
    prompt_text = """
        ## Role
        You are an expert in identifying the primary programming language and its version for services inside a GitHub repository.

        ## Inputs
        - You will receive a language_content : a JSON structure containing, for each candidate language:
        - the number of source files detected
        - the contents of relevant package/build files.
        - Use **only** the data from language_content .
        - Do not infer from filenames outside this data.

        ## Critical Rule
        - If `language_content` is empty or has no valid files, return exactly:
          {{"name": "NA", "version": "", "reason": "No language files found"}}
          
        ## Hard rules
        - Decide the language based on the **highest total of source files** in `language_content`, excluding any under `test`, `integration`, or `template` folders.
        - Detect the version from the package/build file content related to the chosen language.
        - If no language is found, return `"name": "NA"`.
        - If no version is present, return an empty string `""`.
        - If the detected version contains characters like ~, ^, >=, <=, etc., remove them and return only the numeric value (e.g., 5.8.0).
        - Do not add comments, explanations, or markdown.
        - Output must be a single, valid JSON object.

        ## Method
        1. From `language_content`, choose the language with the greatest number of valid source files.
        2. Parse its package/build manifests to extract the version (if present).
        3. Return the result, including a brief `"reason"` describing what led to the choice (e.g., which manifest or count).
        ## Output
        {format_instructions}
        
        USER: Here is the  language content:
        {language_content}
        """

    for service in state.self_built_software:
        prompt = PromptTemplate(
            template=prompt_text,
            input_variables=["language_content"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        service_content = get_languages_and_package_manager_runnable(state.local_path, service.name, service.path)
        if "language_content" in service_content:
            chain = prompt | llm | parser
            response = chain.invoke({"language_content": service_content["languages"]})
            service.language = response
        else:
            service.language = [LanguageResult(name="NA", version="", reason="No language files found").dict()]

    return state
