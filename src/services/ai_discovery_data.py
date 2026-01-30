import dataclasses

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from src.db.conn import get_session
from src.db.models import AiDiscoveryData
from src.dto.state_dto import SelfBuiltComponent


def _build_filter_conditions(session: Session, fact_sheet_id: UUID):
    """Build common filter conditions for AI discovery data queries."""
    return session.query(AiDiscoveryData).filter(
        AiDiscoveryData.fact_sheet_id == fact_sheet_id
    )


def get_ai_discovery_data(fact_sheet_id: UUID) -> Optional[AiDiscoveryData]:
    with get_session() as session:
        return _build_filter_conditions(
            session,
            fact_sheet_id
        ).first()


def delete_ai_discovery_data(fact_sheet_id: UUID) -> None:
    with get_session() as session:
        _build_filter_conditions(
            session,
            fact_sheet_id
        ).delete()
        session.commit()


def create_ai_discovery_data_if_not_exists(fact_sheet_id: UUID,
                                           self_built_component: SelfBuiltComponent) -> AiDiscoveryData:
    data = get_ai_discovery_data(fact_sheet_id)
    if data is None:
        with get_session() as session:
            contributors_dict = None
            if self_built_component.owner.individuals:
                contributors_dict = [{"name": individual.name, "emails": individual.emails} for individual in
                                     self_built_component.owner.individuals]
            tech_stacks_dict = None
            if self_built_component.tech_stacks:
                tech_stacks_dict = [dataclasses.asdict(stack) for stack in self_built_component.tech_stacks]
            data = AiDiscoveryData(
                fact_sheet_id=fact_sheet_id,
                languages=self_built_component.language,
                teams=self_built_component.owner.team if self_built_component.owner.team else None,
                contributors=contributors_dict,
                tech_stacks=tech_stacks_dict
            )
            session.add(data)
            session.commit()
            session.refresh(data)
    return data
