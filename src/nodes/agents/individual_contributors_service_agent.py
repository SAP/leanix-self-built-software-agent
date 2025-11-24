from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.ai_provider.ai_provider import init_llm_by_provider
from src.dto.state_dto import RootRepoState, Individual
from src.logging.logging import get_logger
from src.nodes.runnables.discover_individual_contributors_runnable import discover_individual_contributors_runnable

logger = get_logger(__name__)


class IndividualResult(BaseModel):
    name: str = Field(description="User Name")
    emails: List[str] = Field(description="User Emails")
    commits: int = Field(description="Total number of commits")


class ListOfIndividuals(BaseModel):
    individuals: List[IndividualResult]


def individual_contributors_service_agent(state: RootRepoState) -> RootRepoState:
    """Takes repository data, and find the individual contributors for each service on the repository"""

    llm = init_llm_by_provider()
    parser = JsonOutputParser(pydantic_object=ListOfIndividuals)
    for service in state.self_built_software:
        individuals_list = discover_individual_contributors_runnable(state.local_path, service.name, service.path)
        prompt_text = """
        ## Role
        You are a repository individual contributors analyst. Your job is to analyze the contributors and merge the contributors.

        ## Inputs
        - **You must always work with the individual content {individuals_list}**. Do not use any other data.

        ## Hard rules
        - **No comments, explanations, or extra text.** Only return the required output.

        ## Method
        - Understand the content of the individual contributors and merge them based on the name or email.
        - Ignore any contributor with the name "renovate" or email containing "renovate".
        - Ignore noreply emails.

        ## IMPORTANT
        - Do **not** include any explanation, evidence, or extra text. No markdown, no blocks, no chain-of-thought.
        - **Only** the JSON array.
        
        ## Output
        {format_instructions}
        """
        prompt = PromptTemplate(
            template=prompt_text,
            input_variables=["individuals_list"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        chain = prompt | llm | parser
        response = chain.invoke({"individuals_list": individuals_list})
        individuals: list[Individual] = []
        for individual in response["individuals"]:
            if not individual:
                continue
            emails = individual.get("emails")
            individuals.append(Individual(
                name=individual["name"],
                emails=emails if emails else [],
            ))
        service.owner.individuals = individuals

    return state
