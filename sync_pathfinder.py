import os
import sys
import requests
from src.db.conn import get_session
from src.db.models import AiDiscoveryData, FactSheet, Repository
from src.logging.logging import configure_structlog, get_logger
from dotenv import load_dotenv
import json
import uuid

load_dotenv()
configure_structlog()
logger = get_logger(__name__)

REQUIRED_ENV_VARS = ["LEANIX_TOKEN", "LEANIX_DOMAIN"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

LEANIX_TOKEN = os.getenv("LEANIX_TOKEN")
LEANIX_DOMAIN = os.getenv("LEANIX_DOMAIN")
GRAPHQL_ENDPOINT = f"https://{LEANIX_DOMAIN}/services/pathfinder/v1/graphql"
OAUTH_TOKEN_URL = f"https://{LEANIX_DOMAIN}/services/mtm/v1/oauth2/token"

def get_access_token():
    response = requests.post(
        OAUTH_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=requests.auth.HTTPBasicAuth("apitoken", LEANIX_TOKEN)
    )
    if response.status_code != 200:
        logger.error(f"Failed to get access token: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

ACCESS_TOKEN = get_access_token()

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

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

def graphql_request(query, variables):
    response = requests.post(
        GRAPHQL_ENDPOINT,
        json={"query": query, "variables": variables},
        headers=headers
    )
    if response.status_code != 200 or "errors" in response.json():
        logger.error(f"GraphQL request failed: {response.text}")
        return None
    return response.json()["data"]

def get_discovery_data():
    services = []
    with get_session() as session:
        results = session.query(AiDiscoveryData, FactSheet, Repository).join(
            FactSheet, AiDiscoveryData.fact_sheet_id == FactSheet.fact_sheet_id
        ).join(
            Repository, FactSheet.repository_id == Repository.id
        ).all()
        for ai_data, fact_sheet, repository in results:
            repo_data = repository.data if repository.data else {}
            service = {
                "name": fact_sheet.fact_sheet_name,
                "tech_stacks": ai_data.tech_stacks or [],
                "contributors": ai_data.contributors or [],
                "repository_url": repo_data.get("url")
            }
            services.append(service)
    return services

def sync_services(services):
    logger.info("Starting service synchronization...")
    summary = {"created": 0, "updated": 0, "failed": 0}
    updated_services = []
    for service in services:
        service_name = service["name"]
        repository_url = service.get("repository_url")
        logger.debug(f"Processing service: {service_name}, repository_url: {repository_url}")
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
                logger.error(f"Failed to create FactSheet for service '{service_name}'.")
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
                    logger.error(f"Failed to update repository URL for service '{service_name}'.")
            else:
                logger.info(f"Missing repository_url, skipping update for service: {service_name}")
        updated_services.append(service)
    logger.info(f"Service sync summary: {summary}")
    return updated_services

def sync_tech_stacks(services):
    techstack_cache = {}  # {techstack_name: factsheet_id}
    summary = {"linked": 0, "created": 0, "failed": 0}

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
                        logger.error(f"Failed to create ITComponent FactSheet for techstack '{techstack_name}'")
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
                logger.error(f"Failed to link service '{service_name}' to techstack '{techstack_name}'")

    logger.info(f"Techstack sync summary: {summary}")
    return summary

def sync_contributors(services):
    summary = {"created": 0, "already_exists": 0, "failed": 0}

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
                logger.warning(f"Contributor entry missing name or emails, skipping. Data: {contributor}")
                continue
            email = emails[0]
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
                GRAPHQL_ENDPOINT,
                json={"query": CREATE_SUBSCRIPTION_MUTATION, "variables": variables},
                headers=headers
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
                    logger.error(f"Failed to create subscription for '{name}' ({email}) on service '{service_name}': {error_messages}")
            else:
                summary["failed"] += 1
                logger.error(f"Unexpected error for '{name}' ({email}) on service '{service_name}': {result}")

    logger.info(f"Contributor sync summary: {summary}")
    return summary

def main():
    services = get_discovery_data()
    logger.info(f"Fetched {len(services)} services:")

    tech_stacks = [s["tech_stacks"] for s in services]
    contributors = [s["contributors"] for s in services]

    updated_services = sync_services(services)
    tech_stack_summary = sync_tech_stacks(updated_services)
    contributor_summary = sync_contributors(updated_services)
    logger.info(f"TechStacks: {tech_stack_summary}")
    logger.info(f"Contributors: {contributor_summary}")

if __name__ == "__main__":
    main()