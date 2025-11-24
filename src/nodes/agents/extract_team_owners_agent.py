import os
from typing import Final

from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain import init_llm
from langchain_core.prompts import PromptTemplate

from src.ai_provider.ai_provider import init_llm_by_provider
from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.nodes.runnables.discover_codeowners_runnable import discover_codeowners_runnable
import json
import re

load_dotenv()
logger = get_logger(__name__)

MODEL_NAME: Final[str] = os.getenv("LLM_DEPLOYMENT", "gpt-4.1")


def extract_team_owners_agent(state: RootRepoState) -> RootRepoState:
    """Extracts team names from list of codeowners"""
    logger.info(f"Repo URL: {state.repo_root_url}, deployable: {state.deployable}")
    if state.deployable:
        logger.info("Starting to extract team names from codeowners")
        try:
            llm = init_llm_by_provider()

            codeowners_content = discover_codeowners_runnable(state.repo_root_url)
            logger.info(f"codeowners_file_content: \n{codeowners_content}")

            prompt_text = """
                ## Role
                You are a repository ownership analyst. Your job is to analyze the codeowners file content and extract the owner team name for each service or directory listed in the CODEOWNERS file of a GitHub repository.
                ## Inputs
               
                - **You must always work with the file content {codeowners_content}**. Do not use any other data.
    
                ## Hard rules
                - **No comments, explanations, or extra text.** Only return the required output.
                - **Only team names.** If a service does not have a team owner, use null as the value.
                - **No usernames.** Only include team names (e.g., "team-atlantis").
                - **Strict output format.** Return ONLY a JSON array of objects: `{{ "service": string, "owner_team": array of strings|null }}`.
                - **You should not extract team names from user usernames.** Only extract team names from team names.
                ## Method
                - Understand the content of the CODEOWNERS file and extract the list of service names and their owner team names.
                - If a service/directory does not have a team owner, set `"owner_team": null`.
                ## Output
                - **Primary output (strict):** JSON array of `{{ "service": string, "owner_team": array of strings|null }}`.
    
                ## IMPORTANT
                - Do **not** include any explanation, evidence, or extra text. No markdown, no blocks, no chain-of-thought.
                - Do **NOT** include any comments, explanations, markdown, or extra text.
                - **Only** the JSON array.
                - For each owner_team team name, return only the team name, not the full team name with any prefix or suffix.
    
                ## Before returning the output, extract only the raw team names from each owner team name.
                For example, from 'team-aura' return 'aura', from 'component-library-working-group' return 'component-library-working'.
                For example, from '@leanix/team-potato', return 'potato'.
                
                ## Example output
                [
                    {{"service": "recon", "owner_team": ["team-nova", "team-nova-2"]"]}},
                    {{"service": "*", "owner_team": "team-elevate"}},
                    {{"service": "DEVX", "owner_team": "team-butterfly"}}
                ]
                """

            try:
                prompt = PromptTemplate(
                    template=prompt_text,
                    input_variables=["codeowners_content"],
                )
                chain = prompt | llm
                llm_output = chain.invoke({"codeowners_content": codeowners_content})
            except Exception as e:
                logger.error(f"Error extracting team names: {e}")
                match = re.search(r"Could not parse LLM output: `(.*)`", str(e), re.DOTALL)
                if match:
                    llm_output = match.group(1)
                else:
                    llm_output = "[]"

            # Parse the LLM response
            try:
                service_owners = json.loads(llm_output.content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Raw output: {llm_output.content}")
                service_owners = extract_valid_json(llm_output.content)
            logger.info(f"service_owners: {service_owners}")

            # Build a mapping: service name -> owner_team
            owner_map = {entry["service"]: entry["owner_team"] for entry in service_owners}
            logger.info(f"owner_map: {owner_map}")

            # Get the default owner_team from "*"
            default_owner_team = owner_map.get("*")
            logger.info(f"default_owner_team: {default_owner_team}")

            # Update each SelfBuiltComponent's owner.team
            for comp in state.self_built_software:
                matched_owner_team = None
                for service, team in owner_map.items():
                    if service != "*" and comp.name in service:
                        matched_owner_team = team
                        break
                if matched_owner_team is None:
                    matched_owner_team = default_owner_team
                comp.owner.team = matched_owner_team
                logger.info(f"Updated owner team for {comp.name}: {matched_owner_team}")

            for comp in state.self_built_software:
                logger.info(f"Service2: {comp.name}, owner team: {comp.owner.team}")

            return state

        except Exception as e:
            logger.error(f"Error assigning team ownership: {e}")
            return state
    else:
        logger.info("Skipping team ownership assignment because the repo is not deployable.")
        return state


def extract_valid_json(raw_output):
    logger.info("Attempting to extract valid JSON from LLM output.")
    # Find the start of the array
    start = raw_output.find('[')
    end = raw_output.rfind('}')
    if start != -1 and end != -1 and end > start:
        array_str = raw_output[start:end + 1]
        logger.info(f"Found partial JSON array: {array_str[:200]}...")
        obj_matches = re.findall(r'\{[^{}]*\}', array_str)
        valid_objs = []
        for i, obj_str in enumerate(obj_matches):
            try:
                valid_obj = json.loads(obj_str)
                valid_objs.append(valid_obj)
                logger.info(f"Parsed object {i}: {valid_obj}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error at object {i}: {e}. Object: {obj_str}")
                break
        logger.info(f"Extracted {len(valid_objs)} valid objects.")
        return valid_objs
    logger.warning("No JSON array found in raw output.")
    return []
