from typing import Optional

from src.db.conn import get_session
from src.db.models import Organization


def get_org(organization_name: str) -> Optional[Organization]:
    with get_session() as session:
        organization = session.query(Organization).filter(Organization.name == organization_name).first()
        return organization
def create_org_if_not_exists(organization_name: str) -> Organization:
    organization = get_org(organization_name)
    if organization is None:
        with get_session() as session:
            organization = Organization(
                name=organization_name,
                organization_id="organization_id",
                installed=True,
            )
            session.add(organization)
            session.commit()
    return organization