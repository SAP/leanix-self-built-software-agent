import re
import subprocess
from typing import TypedDict, List

from src.logging.logging import get_logger

logger = get_logger(__name__)


class Individual(TypedDict):
    name: str
    email: str
    commits: int


def discover_individual_contributors_runnable(local_path: str, service_name: str, service_path: str) -> List[
    Individual]:
    """
    Get the contributors for a service
    """
    try:

        logger.info("Discovering individual contributors for service: %s", service_name)
        result = subprocess.run(
            ["git", "shortlog", "HEAD", "-sne", "--", service_path if service_path != "" else "."],
            stdout=subprocess.PIPE,
            cwd=local_path,
            text=True,
            timeout=60  # 1 minute timeout
        )
        contributors: list[Individual] = []
        for line in result.stdout.strip().splitlines():
            match = re.match(r"\s*(\d+)\s+(.*?)\s+<(.+)>", line)
            if match:
                commits, name, email = match.groups()
                if "renovate" in name.lower():
                    continue
                contributors.append(
                    Individual(
                        name=name.strip(),
                        email=email.strip(),
                        commits=int(commits)
                    ))
        return contributors

    except subprocess.TimeoutExpired:
        logger.error("Git short log operation timed out after 1 minutes")
        raise Exception("Git short log operation timed out")
    except Exception as exc:
        logger.error(f"Error during get short log: {str(exc)}")
        raise exc
