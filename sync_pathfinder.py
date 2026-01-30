"""
Service for syncing discovery data to LeanIX Pathfinder.

Can be used as:
1. Standalone script: python sync_pathfinder.py
2. Service module: from sync_pathfinder import initialize_leanix_client, sync_services, etc.
"""
import requests
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.db.conn import get_session
from src.db.models import AiDiscoveryData, FactSheet, Repository
from src.logging.logging import configure_structlog, get_logger

# Configure logging for standalone usage
if __name__ == "__main__":
    configure_structlog()

logger = get_logger(__name__)

# Global variables for LeanIX connection
_LEANIX_TOKEN: Optional[str] = None
_LEANIX_DOMAIN: Optional[str] = None
_GRAPHQL_ENDPOINT: Optional[str] = None
_OAUTH_TOKEN_URL: Optional[str] = None
_ACCESS_TOKEN: Optional[str] = None
_HEADERS: Optional[Dict[str, str]] = None

# GraphQL Queries and Mutations
GET_FACTSHEET_QUERY = """
query GetFactSheet($name: String!, $factSheetType: String!) {
  allFactSheets(filter: {
    displayName: $name
    facetFilters: [
      {
        facetKey: "FactSheetTypes",
        keys: [
          $factSheetType
        ]
      }
    ]
  }) {
    edges {
      node {
        id
        name
      }
    }
  }
}
"""

CREATE_FACTSHEET_MUTATION = """
mutation ($input: BaseFactSheetInput!, $patches: [Patch]!) {
  createFactSheet(input: $input, patches: $patches) {
    factSheet {
      id
      name
      description
      type
      ... on Application {
        externalId {
          externalId
        }
        alias
        category
      }
    }
  }
}
"""

UPDATE_SERVICE_MUTATION = """
mutation ($id: ID!, $patches: [Patch]!) {
  updateFactSheet(id: $id, patches: $patches) {
    factSheet {
      id
      name
      description
    }
  }
}
"""

LINK_TECHSTACK_MUTATION = """
mutation ($id: ID!, $patches: [Patch]!) {
  updateFactSheet(id: $id, patches: $patches) {
    factSheet {
      id
      name
      ... on Application {
        relApplicationToITComponent {
          edges { node { id } }
        }
      }
    }
  }
}
"""

CREATE_SUBSCRIPTION_MUTATION = """
mutation CreateSubscription($factSheetId: ID!, $user: UserInput!, $roles: [SubscriptionToSubscriptionRoleLinkInput]) {
  createSubscription(
    factSheetId: $factSheetId,
    user: $user,
    type: RESPONSIBLE,
    roles: $roles
  ) {
    id
  }
}
"""


def initialize_leanix_client(token: str, domain: str) -> None:
    """
    Initialize the LeanIX client with credentials.

    Args:
        token: LeanIX API token
        domain: LeanIX domain (e.g., company.leanix.net)

    Raises:
        Exception: If authentication fails
    """
    global _LEANIX_TOKEN, _LEANIX_DOMAIN, _GRAPHQL_ENDPOINT, _OAUTH_TOKEN_URL, _ACCESS_TOKEN, _HEADERS

    _LEANIX_TOKEN = token
    _LEANIX_DOMAIN = domain
    _GRAPHQL_ENDPOINT = f"https://{domain}/services/pathfinder/v1/graphql"
    _OAUTH_TOKEN_URL = f"https://{domain}/services/mtm/v1/oauth2/token"

    # Get access token
    _ACCESS_TOKEN = _get_access_token()

    # Set headers
    _HEADERS = {
        "Authorization": f"Bearer {_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    logger.info(f"Initialized LeanIX client for domain: {domain}")


def _get_access_token() -> str:
    """Get OAuth access token from LeanIX."""
    response = requests.post(
        _OAUTH_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=requests.auth.HTTPBasicAuth("apitoken", _LEANIX_TOKEN),
        timeout=30
    )
    if response.status_code != 200:
        logger.error(f"Failed to get access token: {response.text}")
        raise Exception(f"Failed to authenticate with LeanIX: {response.text}")
    return response.json()["access_token"]


def graphql_request(query: str, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Execute a GraphQL request to LeanIX."""
    response = requests.post(
        _GRAPHQL_ENDPOINT,
        json={"query": query, "variables": variables},
        headers=_HEADERS,
        timeout=30
    )
    if response.status_code != 200 or "errors" in response.json():
        return None
    return response.json()["data"]


def get_discovery_data(repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch discovery data from the database.

    Args:
        repo_filter: Optional repository filter in format OWNER/REPO

    Returns:
        List of service dictionaries
    """
    services = []
    with get_session() as session:
        query = session.query(AiDiscoveryData, FactSheet, Repository).join(
            FactSheet, AiDiscoveryData.fact_sheet_id == FactSheet.fact_sheet_id
        ).join(
            Repository, FactSheet.repository_id == Repository.id
        )

        # Apply filter if specified
        if repo_filter:
            query = query.filter(Repository.full_name == repo_filter)

        results = query.all()

        for ai_data, fact_sheet, repository in results:
            repo_data = repository.data if repository.data else {}
            service = {
                "name": fact_sheet.fact_sheet_name,
                "tech_stacks": ai_data.tech_stacks or [],
                "contributors": ai_data.contributors or [],
                "repository_url": repo_data.get("url"),
                "repository_name": repository.full_name,
            }
            services.append(service)

    logger.info(f"Fetched {len(services)} service(s) from database")
    return services


def sync_services(services: List[Dict[str, Any]], dry_run: bool = False, progress_callback: Optional[Callable] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Sync services to LeanIX Pathfinder.

    Args:
        services: List of service dictionaries
        dry_run: If True, don't make actual changes
        progress_callback: Optional callback function to report progress

    Returns:
        Tuple of (updated services with factsSheetId, summary dict with errors)
    """
    logger.info("Starting service synchronization...")
    summary = {"created": 0, "updated": 0, "failed": 0, "errors": []}
    updated_services = []

    for idx, service in enumerate(services):
        service_name = service["name"]
        repository_url = service.get("repository_url")
        logger.debug(f"Processing service: {service_name}, repository_url: {repository_url}")

        if dry_run:
            logger.info(f"[DRY RUN] Would sync service: {service_name}")
            service["factsSheetId"] = f"dry-run-{uuid.uuid4().hex}"
            summary["created"] += 1
            updated_services.append(service)
            continue

        result = graphql_request(GET_FACTSHEET_QUERY, {"name": service_name, "factSheetType": "Application"})
        edges = result.get("allFactSheets", {}).get("edges", []) if result else []

        if not edges:
            logger.info(f"FactSheet not found for service '{service_name}', creating new FactSheet.")
            variables = {
                "input": {
                    "name": service_name,
                    "type": "Application"
                },
                "patches": [
                    {
                        "op": "add",
                        "path": "/category",
                        "value": "microservice"
                    }
                ]
            }
            create_result = graphql_request(CREATE_FACTSHEET_MUTATION, variables)
            if create_result and create_result.get("createFactSheet"):
                fact_sheet_id = create_result["createFactSheet"]["factSheet"]["id"]
                service["factsSheetId"] = fact_sheet_id
                summary["created"] += 1
                logger.info(f"Created FactSheet for service '{service_name}' with id '{fact_sheet_id}'.")
            else:
                service["factsSheetId"] = None
                summary["failed"] += 1
                error_msg = f"Failed to create FactSheet for service '{service_name}'"
                summary["errors"].append({"service": service_name, "error": error_msg})
        else:
            fact_sheet_id = edges[0]["node"]["id"]
            service["factsSheetId"] = fact_sheet_id
            logger.info(f"Found existing FactSheet for service '{service_name}' with id '{fact_sheet_id}'.")
            if repository_url:
                patches = [{
                    "op": "replace",
                    "path": "/lxRepositoryUrl",
                    "value": repository_url
                }]
                update_result = graphql_request(
                    UPDATE_SERVICE_MUTATION,
                    {"id": fact_sheet_id, "patches": patches}
                )
                if update_result and update_result.get("updateFactSheet"):
                    summary["updated"] += 1
                    logger.info(f"Updated repository URL for service '{service_name}'.")
                else:
                    summary["failed"] += 1
                    error_msg = f"Failed to update repository URL for service '{service_name}'"
                    summary["errors"].append({"service": service_name, "error": error_msg})
            else:
                logger.info(f"Missing repository_url, skipping update for service: {service_name}")

        updated_services.append(service)

        # Report progress
        if progress_callback:
            progress_callback(idx + 1, len(services), service_name)

    logger.info(f"Service sync summary: {summary}")
    return updated_services, summary


def sync_tech_stacks(services: List[Dict[str, Any]], dry_run: bool = False, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Sync tech stacks to LeanIX and link them to services.

    Args:
        services: List of service dictionaries with factsSheetId
        dry_run: If True, don't make actual changes
        progress_callback: Optional callback function to report progress

    Returns:
        Summary dictionary with counts and errors
    """
    techstack_cache = {}  # {techstack_name: factsheet_id}
    summary = {"linked": 0, "created": 0, "failed": 0, "errors": []}

    # Calculate total tech stacks for progress
    total_stacks = sum(len(s.get("tech_stacks", [])) for s in services)
    current = 0

    for service in services:
        app_id = service.get("factsSheetId")
        service_name = service.get("name")
        if not app_id:
            logger.warning(f"Service '{service_name}' missing factsSheetId, skipping techstack sync.")
            continue

        for techstack in service.get("tech_stacks", []):
            techstack_name = techstack.get("name") if isinstance(techstack, dict) else str(techstack)
            if not techstack_name:
                logger.warning("Techstack entry missing name, skipping.")
                continue

            logger.debug(f"Processing techstack '{techstack_name}' for service '{service_name}'")

            if dry_run:
                logger.info(f"[DRY RUN] Would link techstack '{techstack_name}' to service '{service_name}'")
                summary["linked"] += 1
                continue

            # Use techstack_name as the cache key
            if techstack_name in techstack_cache:
                itcomp_id = techstack_cache[techstack_name]
                logger.debug(f"Found techstack '{techstack_name}' in cache with id '{itcomp_id}'")
            else:
                logger.debug(f"Techstack '{techstack_name}' not in cache, querying LeanIX...")
                result = graphql_request(GET_FACTSHEET_QUERY, {"name": techstack_name, "factSheetType": "ITComponent"})
                edges = result.get("allFactSheets", {}).get("edges", []) if result else []
                if edges:
                    itcomp_id = edges[0]["node"]["id"]
                    logger.info(f"Found ITComponent FactSheet for techstack '{techstack_name}' with id '{itcomp_id}'")
                else:
                    logger.info(f"ITComponent FactSheet for techstack '{techstack_name}' not found, creating...")
                    variables = {
                        "input": {
                            "name": techstack_name,
                            "type": "ITComponent"
                        },
                        "patches": [
                            {
                                "op": "add",
                                "path": "/category",
                                "value": "software"
                            }
                        ]
                    }
                    create_result = graphql_request(CREATE_FACTSHEET_MUTATION, variables)
                    if create_result and create_result.get("createFactSheet"):
                        itcomp_id = create_result["createFactSheet"]["factSheet"]["id"]
                        summary["created"] += 1
                        logger.info(f"Created ITComponent FactSheet for techstack '{techstack_name}' with id '{itcomp_id}'")
                    else:
                        summary["failed"] += 1
                        error_msg = f"Failed to create ITComponent FactSheet for techstack '{techstack_name}'"
                        summary["errors"].append({"techstack": techstack_name, "service": service_name, "error": error_msg})
                        continue
                techstack_cache[techstack_name] = itcomp_id

            # Create relation
            logger.debug(f"Linking service '{service_name}' (id: {app_id}) to techstack '{techstack_name}' (id: {itcomp_id})")
            patches = [{
                "op": "add",
                "path": f"/relApplicationToITComponent/new_{uuid.uuid4().hex}",
                "value": json.dumps({"factSheetId": itcomp_id})
            }]
            relation_result = graphql_request(
                LINK_TECHSTACK_MUTATION,
                {"id": app_id, "patches": patches}
            )
            if relation_result and relation_result.get("updateFactSheet"):
                summary["linked"] += 1
                logger.info(f"Linked service '{service_name}' to techstack '{techstack_name}'")
            else:
                summary["failed"] += 1
                error_msg = f"Failed to link service '{service_name}' to techstack '{techstack_name}'"
                summary["errors"].append({"techstack": techstack_name, "service": service_name, "error": error_msg})

            # Report progress
            current += 1
            if progress_callback:
                progress_callback(current, total_stacks, f"{techstack_name} → {service_name}")

    logger.info(f"Techstack sync summary: {summary}")
    return summary


def sync_contributors(services: List[Dict[str, Any]], dry_run: bool = False, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Sync contributors to LeanIX as subscriptions.

    Args:
        services: List of service dictionaries with factsSheetId
        dry_run: If True, don't make actual changes
        progress_callback: Optional callback function to report progress

    Returns:
        Summary dictionary with counts and errors
    """
    summary = {"created": 0, "already_exists": 0, "failed": 0, "errors": []}

    # Calculate total contributors for progress
    total_contributors = sum(len(s.get("contributors", [])) for s in services)
    current = 0

    for service in services:
        fact_sheet_id = service.get("factsSheetId")
        service_name = service.get("name")
        contributors = service.get("contributors", [])
        if not fact_sheet_id:
            logger.warning(f"Service '{service_name}' missing factsSheetId, skipping contributor sync.")
            continue

        for contributor in contributors:
            name = contributor.get("name", "")
            emails = contributor.get("emails", [])
            if not name or not emails:
                summary["failed"] += 1
                error_msg = f"Contributor entry missing name or emails"
                summary["errors"].append({"contributor": contributor, "service": service_name, "error": error_msg})
                continue

            email = emails[0]

            if dry_run:
                logger.info(f"[DRY RUN] Would add contributor '{name}' ({email}) to service '{service_name}'")
                summary["created"] += 1
                continue

            user_input = {
                "email": email,
                "firstName": name,
                "lastName": ""
            }
            variables = {
                "factSheetId": fact_sheet_id,
                "user": user_input,
                "roles": [{}]
            }
            logger.debug(f"Creating subscription for contributor '{name}' ({email}) on service '{service_name}' (FactSheetId: {fact_sheet_id})")
            response = requests.post(
                _GRAPHQL_ENDPOINT,
                json={"query": CREATE_SUBSCRIPTION_MUTATION, "variables": variables},
                headers=_HEADERS,
                timeout=30
            )
            result = response.json()
            if response.status_code == 200 and result.get("data", {}).get("createSubscription"):
                summary["created"] += 1
                logger.info(f"Created subscription for '{name}' ({email}) on service '{service_name}'.")
            elif "errors" in result:
                error_messages = [e.get("message", "") for e in result["errors"]]
                if any("Subscription already exists" in msg for msg in error_messages):
                    summary["already_exists"] += 1
                    logger.info(f"Subscription already exists for '{name}' ({email}) on service '{service_name}'.")
                else:
                    summary["failed"] += 1
                    error_msg = f"Failed to create subscription for '{name}' ({email}): {', '.join(error_messages)}"
                    summary["errors"].append({"contributor": name, "service": service_name, "error": error_msg})
            else:
                summary["failed"] += 1
                error_msg = f"Unexpected error for '{name}' ({email})"
                summary["errors"].append({"contributor": name, "service": service_name, "error": error_msg})

            # Report progress
            current += 1
            if progress_callback:
                progress_callback(current, total_contributors, f"{name} → {service_name}")

    logger.info(f"Contributor sync summary: {summary}")
    return summary
