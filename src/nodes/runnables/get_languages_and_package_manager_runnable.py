import glob
from pathlib import Path
from typing import Optional, List

from typing_extensions import TypedDict

from src.logging.logging import get_logger

logger = get_logger(__name__)

LANGUAGES = {
    "Kotlin": {
        "build_manifests": {"build.gradle", "build.gradle.kts", "pom.xml", "gradle.properties", "libs.versions.toml"},
        "file_indicators": {"*.kt", "*.kts"},
    },
    "Java": {
        "build_manifests": {"build.gradle", "build.gradle.kts", "pom.xml", "gradle.properties", "libs.versions.toml"},
        "file_indicators": {"*.java"},
    },
    "TypeScript": {
        "build_manifests": {"package.json", "yarn.lock", "pnpm-lock.yaml", "project.json"},
        "file_indicators": {"*.ts"},
    },
    "Javascript": {
        "build_manifests": {".node-version"},
        "file_indicators": {"*.js"},
    },
    "Python": {
        "build_manifests": {"requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock", "Dockerfile"},
        "file_indicators": {"*.py"},
    },
    "C#": {
        "build_manifests": {"*.csproj", "*.sln", "packages.config"},
        "file_indicators": {"*.cs"},
    },
    "Go": {
        "build_manifests": {"go.mod"},
        "file_indicators": {"*.go"},
    },
    "Rust": {
        "build_manifests": {"Cargo.toml"},
        "file_indicators": {"*.rs"},
    },
    "Ruby": {
        "build_manifests": {"Gemfile"},
        "file_indicators": {"*.rb"},
    },
    "HCL": {
        "build_manifests": {".terraform.lock.hcl", "versions.tf"},
        "file_indicators": {"*.tf"},
    },
    "PHP": {
        "build_manifests": {},
        "file_indicators": {"*.php"},
    },
    "LUA": {
        "build_manifests": {"Dockerfile"},
        "file_indicators": {"*.lua"},
    }
}


class FilesContent(TypedDict):
    file_name: Optional[str]
    content: Optional[str]

class Language(TypedDict):
    name: str
    total_files: int
    packages_content: List[FilesContent]

class ServiceManifests(TypedDict):
    local_path: str  # canonical GitHub repo URL
    service_name: str
    languages: List[Language]

def get_languages_and_package_manager_runnable(local_path: str, service_name: str, service_path: str) -> ServiceManifests:
    """
    Get the content from the package manager for a service
    """
    if not local_path:
        logger.warning("No local path available for deployment signal analysis")
        return f"Error: no local path"

    local_repo_path = Path(local_path + "/" + service_path)
    if not local_repo_path.exists():
        logger.error(f"Local repository path does not exist: {local_repo_path}")
        return f"Error: no local path"

    files_content: List[FilesContent] = []
    languages: List[Language] = []
    total_files_content_found = 0
    for expected_language in LANGUAGES:
        total_files = 0
        for file_extension in LANGUAGES[expected_language]["file_indicators"]:
            total_files += len(list(glob.glob(local_path + "/" + service_path + "/**/" + file_extension, recursive=True)))
        if total_files > 0:
            for expected_manifest_name in LANGUAGES[expected_language]["build_manifests"]:
                found_files = list(local_repo_path.glob(expected_manifest_name))
                for file_path in found_files:
                    files_content.append(FilesContent(file_name=file_path.name, content=file_path.read_text(encoding="utf-8")))
                total_files_content_found += len(found_files)

            languages.append(Language(name=expected_language, total_files=total_files, packages_content=files_content))

    logger.info(f"Languages found {len(languages)} and manifest found {total_files_content_found} files for {service_name}")

    # ── return structured result ───────────────────────────────
    return ServiceManifests(local_path=local_path, service_name=service_name, languages=languages)
