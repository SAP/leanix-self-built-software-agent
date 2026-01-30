from typing import Optional
from uuid import UUID

from src.db.conn import get_session
from src.db.models import Repository
from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.services.fact_sheets import create_fact_sheet_from_sbs, delete_fact_sheet_by_repository
from src.utils.url_helper import parse_github_url_to_repo_full_name

logger = get_logger(__name__)

def get_repository(full_name: str) -> Optional[Repository]:
    with get_session() as session:
        repository = session.query(Repository).filter(Repository.full_name == full_name).first()
        return repository

def create_repository(repos_state: RootRepoState):
    owner, repo = parse_github_url_to_repo_full_name(repos_state.repo_root_url)
    full_name = f"{owner}/{repo}"
    repository = get_repository(
        full_name=full_name,
    )
    with get_session() as session:
        if repository is None:
            repository = Repository(
                full_name=full_name,
                data={"id": "repo_id",
                    "url": repos_state.repo_root_url,
                    "name": repo,
                    "topics": [],
                    "archived": False,
                    "languages": [],
                    "codeOwners": None,
                    "visibility": "Private",
                    "description": None,
                    "prApprovers": None,
                    "defaultBranch": "main",
                    "organizationName": owner,
                    "updatedAt": "2024-12-17T10:20:27Z"
                    },
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)

    try:
        # Manage FactSheets
        delete_fact_sheet_by_repository(repository.id)

        if repos_state.self_built_software:
            for sbs_component in repos_state.self_built_software:
                create_fact_sheet_from_sbs(
                    self_built_component=sbs_component,
                    repository_id=repository.id
                )
            logger.info(f"Created {len(repos_state.self_built_software)} fact sheets for repository {repository.id}")
        else:
            logger.info(f"No self-built software components found for repository {repository.id}")

    except Exception as e:
        logger.error(f"Error processing fact sheets for repository {repository.id}: {e}")
