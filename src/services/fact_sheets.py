from typing import Optional
from uuid import UUID

from src.logging.logging import get_logger
from src.db.conn import get_session
from src.db.models import FactSheet
from src.dto.state_dto import SelfBuiltComponent
from src.services.ai_discovery_data import create_ai_discovery_data_if_not_exists, delete_ai_discovery_data

logger = get_logger(__name__)

def get_fact_sheet(fact_sheet_name: str) -> Optional[FactSheet]:
    with get_session() as session:
        fact_sheet = session.query(FactSheet).filter(FactSheet.fact_sheet_name == fact_sheet_name).first()
    return fact_sheet

def delete_fact_sheet_by_repository(repository_id: UUID) -> None:
    with get_session() as session:
        session.query(FactSheet).filter(FactSheet.repository_id == repository_id).delete()
        session.commit()

def create_fact_sheet_from_sbs(self_built_component: SelfBuiltComponent, repository_id: UUID) -> Optional[FactSheet]:
    fact_sheet = get_fact_sheet(
        fact_sheet_name=self_built_component.name,
    )
    if fact_sheet is None:
        with get_session() as session:
            fact_sheet = FactSheet(
                fact_sheet_name=self_built_component.name,
                repository_id=repository_id,
                manifest_file_url=self_built_component.display_url
            )
            session.add(fact_sheet)
            session.commit()
            session.refresh(fact_sheet)
    # Manage AI discovery data
    try:
        delete_ai_discovery_data(fact_sheet.fact_sheet_id)
        create_ai_discovery_data_if_not_exists(
            fact_sheet.fact_sheet_id, self_built_component
        )
        logger.debug(f"Updated AI discovery data for fact sheet: {fact_sheet.fact_sheet_id}")
    except Exception as e:
        logger.error(f"Error managing AI discovery data for fact sheet {fact_sheet.fact_sheet_id}: {e}")

    return fact_sheet
