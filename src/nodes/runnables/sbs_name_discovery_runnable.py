import json
import os
from pathlib import Path
from typing import List, Set, Dict

from src.dto.state_dto import RootRepoState, SelfBuiltComponent, Owner, ComponentType
from src.logging.logging import get_logger
from src.utils.file_filters import _should_skip_directory, _is_binary_file, _is_generated_or_derived_directory
from src.nodes.agents.ai_service_discovery_agent import ai_service_discovery_agent


logger = get_logger(__name__)

# Package manager files that indicate a self-built software
PACKAGE_MANAGER_FILES = {
    "package.json": "javascript",
    "project.json": "javascript",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "setup.py": "python",
    "composer.json": "php",
    "Gemfile": "ruby",
    "*.csproj": "csharp",
    "*.fsproj": "fsharp",
    "*.vbproj": "vb.net",
    "project.clj": "clojure",
    "deps.edn": "clojure",
    "mix.exs": "elixir",
    "pubspec.yaml": "dart"
}

def sbs_name_discovery_runnable(state: RootRepoState) -> RootRepoState:
    """
    Analyze the locally cloned repository to discover self-built software.
    Uses deployment signals to identify which directories with package managers are actually services.
    """
    if not state.local_path:
        logger.warning("No local path available for analysis")
        return state

    local_repo_path = Path(state.local_path)
    if not local_repo_path.exists():
        logger.error(f"Local repository path does not exist: {local_repo_path}")
        return state

    logger.info(f"Analyzing local repository at: {local_repo_path}")

    discovered_services = discover_services_by_deployment_signals(local_repo_path, state.repo_root_url, state.deployable_signal_files)

    # Add discovered services to state
    for service in discovered_services:
        state.self_built_software.append(service)

    logger.info(f"Discovered {len(discovered_services)} self-built software components")

    return state


def discover_services_by_deployment_signals(repo_path: Path, repo_root_url: str, deployment_signal_files: List[str]) -> List[SelfBuiltComponent]:
    """
    Discover self-built software by finding package manager directories and using an LLM to classify them.
    """
    services = []

    # Step 1: Find all directories with package manager files
    package_manager_dirs = _find_package_manager_directories(repo_path)
    logger.info(f"Found {len(package_manager_dirs)} directories with package managers")

    # Step 2: Analyze CI/CD files to find which directories they reference
    referenced_dirs = _analyze_cicd_references(repo_path, deployment_signal_files, package_manager_dirs)
    logger.info(f"CI/CD files reference {len(referenced_dirs)} package manager directories")

    # Step 3: Create services for referenced directories
    if len(referenced_dirs)>=4:
        for dir_info in package_manager_dirs:
            relative_path = dir_info['path']

            if str(relative_path) in referenced_dirs:
                service_name = _extract_service_name(repo_path / relative_path, dir_info['package_file'])
                language = dir_info['language']

                # Group deployment signals for this service
                service_signals = _group_deployment_signals_for_service(relative_path, deployment_signal_files)

                display_url = f"{repo_root_url}/tree/main/{relative_path}" if str(relative_path) != "." else repo_root_url

                component = SelfBuiltComponent(
                    name=service_name,
                    path=str(relative_path),
                    display_url=display_url,
                    owner=Owner(),
                    language=language,
                    component_type=ComponentType.UNKNOWN,
                    evidence=str(service_signals),
                    confidence="high",
                )

                services.append(component)
                logger.info(f"Found service: {service_name} at {relative_path} (language: {language})")
    else:
        # Read CI/CD/deployment file contents
        cicd_files = []
        for file in deployment_signal_files:
            fpath = repo_path / file
            if fpath.exists() and fpath.is_file():
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    cicd_files.append({"path": file, "content": content})
                except Exception as e:
                    logger.warning(f"Could not read {file}: {e}")

        # Call the LLM agent
        discovered = ai_service_discovery_agent(
            candidate_dirs=package_manager_dirs,
            cicd_files=cicd_files,
            repo_path=str(repo_path),
            readme_lines=20,  # set as appropriate
            context_signals=deployment_signal_files,  # or filter only strong ones if you prefer
        )

        # Build SelfBuiltComponent objects from LLM result
        for svc in discovered:
            path = svc.get("path")
            name = svc.get("name") or (Path(path).name if path and path != "." else "root")
            language = svc.get("language", "unknown")
            display_url = f"{repo_root_url}/tree/main/{path}" if path != "." else repo_root_url
            evidence = svc.get("evidence")
            confidence = svc.get("confidence")

            component = SelfBuiltComponent(
                name=name,
                path=path,
                display_url=display_url,
                owner=Owner(),
                language=language,
                component_type=ComponentType.UNKNOWN,
                evidence=evidence,
                confidence=confidence,
            )
            services.append(component)
            logger.info(f"(LLM) Detected service: {name} at {path} (language: {language})")

    return services

def _find_package_manager_directories(repo_path: Path) -> List[Dict]:
    """Find all directories containing package manager files."""
    package_dirs = []
    processed_dirs = set()  # Track already processed directories

    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)

        # Skip directories that should be filtered out
        dirs[:] = [
            d for d in dirs
            if not _should_skip_directory(d)
            and not _is_generated_or_derived_directory(root_path / d)
        ]

        # Filter out binary files
        filtered_files = [
            f for f in files
            if not _is_binary_file(f)
        ]

        # Check for package manager files in this directory
        package_files_found = []
        for file in filtered_files:
            if _is_package_manager_file(file):
                package_files_found.append(file)

        # If we found package manager files and haven't processed this directory yet
        relative_path = root_path.relative_to(repo_path)
        if package_files_found and str(relative_path) not in processed_dirs:
            # Prioritize certain package manager files over others
            priority_order = ['package.json', 'project.json', 'pom.xml', 'build.gradle', 'go.mod', 'Cargo.toml']

            selected_file = package_files_found[0]  # Default to first found
            for priority_file in priority_order:
                if priority_file in package_files_found:
                    selected_file = priority_file
                    break

            package_dirs.append({
                'path': relative_path,
                'package_file': selected_file,
                'language': PACKAGE_MANAGER_FILES.get(selected_file, "unknown")
            })

            processed_dirs.add(str(relative_path))

    return package_dirs

def _analyze_cicd_references(repo_path: Path, deployment_signal_files: List[str], package_manager_dirs: List[Dict]) -> Set[str]:
    """
    Analyze CI/CD files to find which package manager directories they reference.
    Handles both source directories and their corresponding build/dist directories.
    """
    referenced_dirs = set()

    # Filter to only CI/CD files
    cicd_files = [
        f for f in deployment_signal_files
        if _is_cicd_file(f)
    ]

    logger.info(f"Analyzing {len(cicd_files)} CI/CD files for service references: {cicd_files}")

    for cicd_file in cicd_files:
        try:
            cicd_path = repo_path / cicd_file
            logger.debug(f"Processing CI/CD file: {cicd_path}")
            if not cicd_path.exists():
                logger.warning(f"CI/CD file does not exist: {cicd_path}")
                continue

            content = cicd_path.read_text(encoding='utf-8', errors='ignore').lower()

            # Check which package manager directories are referenced in this CI/CD file
            for dir_info in package_manager_dirs:
                dir_path = str(dir_info['path'])
                logger.debug(f"Checking if directory '{dir_path}' is referenced in CI/CD file '{cicd_file}'")
                if _is_directory_referenced_in_cicd(content, dir_path, dir_info):
                    logger.info(f"Directory '{dir_path}' referenced in CI/CD file '{cicd_file}'")
                    referenced_dirs.add(dir_path)

        except Exception as e:
            logger.debug(f"Could not analyze CI/CD file {cicd_file}: {e}")

    logger.info(f"Referenced directories found: {referenced_dirs}")
    return referenced_dirs

def _is_directory_referenced_in_cicd(content: str, dir_path: str, dir_info: Dict) -> bool:
    """
    Check if a directory is referenced in CI/CD content.
    Generic pattern matching for various monorepo tools and CI/CD systems.
    """
    package_file = dir_info['package_file']

    # First check if this looks like an infrastructure directory
    if _is_infrastructure_directory(dir_path):
        return False

    # Extract service/project name from directory path
    service_name = Path(dir_path).name if dir_path != "." else "root"

    # Get all path segments for partial matching
    path_segments = dir_path.split('/') if dir_path != "." else []

    # 1. Direct path references
    direct_patterns = _generate_direct_path_patterns(dir_path, package_file)

    # 2. Service/project name patterns (generic for all monorepo tools)
    service_patterns = _generate_service_name_patterns(service_name, path_segments)

    # 3. Build/dist directory mappings
    build_patterns = _generate_build_patterns(dir_path)

    # 4. Tool-specific patterns
    tool_patterns = _generate_tool_specific_patterns(service_name, dir_path, path_segments)

    # Combine all patterns and convert to lowercase for case-insensitive matching
    all_patterns = direct_patterns + service_patterns + build_patterns + tool_patterns
    all_patterns_lower = [pattern.lower() for pattern in all_patterns]

    # Check if any pattern matches
    for pattern in all_patterns_lower:
        if pattern in content:
            return True

    return False

def _generate_direct_path_patterns(dir_path: str, package_file: str) -> List[str]:
    """Generate direct path reference patterns."""
    return [
        dir_path,
        f"./{dir_path}",
        f"cd {dir_path}",
        f"working-directory: {dir_path}",
        f"dir: {dir_path}",
        f"path: {dir_path}",
        f"context: {dir_path}",
        f"dockerfile: {dir_path}/dockerfile",
        f"{dir_path}/{package_file}",
        f"./{dir_path}/{package_file}",
    ]

def _generate_service_name_patterns(service_name: str, path_segments: List[str]) -> List[str]:
    """Generate service/project name patterns for various monorepo tools."""
    patterns = []

    # Basic service name patterns
    patterns.extend([
        f"project: {service_name}",
        f"name: {service_name}",
        f"app: {service_name}",
        f"service: {service_name}",
        f"package: {service_name}",
        f"module: {service_name}",
    ])

    # Command-line tool patterns
    patterns.extend([
        # NX (JavaScript/TypeScript)
        f"nx run {service_name}:",
        f"nx build {service_name}",
        f"nx test {service_name}",
        f"nx lint {service_name}",
        f"nx e2e {service_name}",
        f"nx run-many --projects={service_name}",
        f"--projects={service_name}",

        # Lerna (JavaScript)
        f"lerna run --scope {service_name}",
        f"--scope {service_name}",

        # Rush (JavaScript)
        f"rush build --to {service_name}",
        f"rush test --to {service_name}",

        # Bazel (multi-language)
        f"bazel build //{service_name}",
        f"bazel test //{service_name}",
        f"//{service_name}:",

        # Gradle (Java/Kotlin)
        f"gradle :{service_name}:",
        f"./gradlew :{service_name}:",
        f":{service_name}:build",
        f":{service_name}:test",

        # Maven (Java)
        f"mvn -pl {service_name}",
        f"-pl {service_name}",
        f"--projects {service_name}",

        # Cargo (Rust)
        f"cargo build -p {service_name}",
        f"cargo test -p {service_name}",
        f"-p {service_name}",

        # Go modules
        f"go build ./{service_name}",
        f"go test ./{service_name}",

        # .NET
        f"dotnet build {service_name}",
        f"dotnet test {service_name}",

        # Generic make/task patterns
        f"make {service_name}",
        f"task {service_name}",
        f"invoke {service_name}",
    ])

    # Environment variable patterns (common in CI/CD)
    patterns.extend([
        f"app_name={service_name}",
        f"service_name={service_name}",
        f"project_name={service_name}",
        f"package_name={service_name}",
        f"component={service_name}",
        f"APP_NAME={service_name.upper()}",
        f"SERVICE_NAME={service_name.upper()}",
        f"PROJECT_NAME={service_name.upper()}",
    ])

    # Container/deployment patterns
    patterns.extend([
        f"image: {service_name}",
        f"container: {service_name}",
        f"deployment: {service_name}",
        f"app-name: {service_name}",
        f"release: {service_name}",
        f"version: {service_name}",
    ])

    # Path segment patterns (for nested services)
    if len(path_segments) > 1:
        for segment in path_segments:
            patterns.extend([
                f"project: {segment}",
                f"nx run {segment}:",
                f"--scope {segment}",
                f":{segment}:build",
                f"-p {segment}",
            ])

    return patterns

def _generate_build_patterns(dir_path: str) -> List[str]:
    """Generate build/dist directory patterns."""
    patterns = []

    # Build directory mappings
    build_mappings = _generate_build_directory_mappings(dir_path)

    for build_pattern in build_mappings:
        patterns.extend([
            build_pattern,
            f"./{build_pattern}",
            f"source-directory: ./{build_pattern}",
            f"source-directory: {build_pattern}",
            f"path: ./{build_pattern}",
            f"path: {build_pattern}",
            f"dist: {build_pattern}",
            f"output: {build_pattern}",
            f"build: {build_pattern}",
            f"target: {build_pattern}",
            f"artifact-path: {build_pattern}",
            f"dist-dir: {build_pattern}",
            f"output-dir: {build_pattern}",
            f"build-dir: {build_pattern}",
        ])

    return patterns

def _generate_tool_specific_patterns(service_name: str, dir_path: str, path_segments: List[str]) -> List[str]:
    """Generate tool-specific patterns based on file content analysis."""
    patterns = []

    # Turborepo patterns
    patterns.extend([
        f'"name": "{service_name}"',  # turbo.json or package.json reference
        f'"{service_name}#build"',    # Turborepo task syntax
        f'"{service_name}#test"',
        f'"{service_name}#lint"',
    ])

    # Kubernetes/Helm patterns
    patterns.extend([
        f"app.kubernetes.io/name: {service_name}",
        f"app: {service_name}",
        f"release: {service_name}",
        f"chart: {service_name}",
    ])

    # Docker Compose patterns
    patterns.extend([
        f"services:",  # Look for service definitions (more complex matching needed)
        f"{service_name}:",  # Service name in docker-compose
    ])

    # Cloud provider specific patterns
    patterns.extend([
        # AWS
        f"function-name: {service_name}",
        f"stack-name: {service_name}",

        # Azure
        f"app-name: {service_name}",
        f"resource-group: {service_name}",

        # GCP
        f"service: {service_name}",
        f"function: {service_name}",
    ])

    # CI/CD platform specific patterns
    patterns.extend([
        # GitHub Actions
        f"uses: ./.github/actions/{service_name}",
        f"uses: ./.github/workflows/{service_name}",

        # GitLab CI
        f"extends: {service_name}",
        f"needs: {service_name}",

        # Jenkins
        f"stage('{service_name}')",
        f'stage("{service_name}")',

        # Azure DevOps
        f"job: {service_name}",
        f"task: {service_name}",
    ])

    return patterns

def _is_infrastructure_directory(dir_path: str) -> bool:
    """
    Check if directory appears to be infrastructure/configuration rather than a deployable service.
    Uses more specific matching to avoid false positives.
    """
    dir_name = Path(dir_path).name.lower()
    dir_path_lower = dir_path.lower()

    # Exact matches for common infrastructure directories
    exact_infrastructure_names = {
        'k8s', 'kubernetes', 'kube',
        'infrastructure', 'infra', 'deploy', 'deployment', 'deployments',
        'config', 'configuration', 'configs', 'conf',
        'manifests', 'helm', 'charts', 'chart',
        'terraform', 'tf', 'ansible', 'playbooks',
        'scripts', 'tools', 'utilities', 'utils',
        'docs', 'documentation', 'doc',
        'test', 'tests', 'testing', 'e2e', 'integration',
        'ci', 'cd', 'pipeline', 'pipelines',
        'security', 'secrets', 'vault',
        'storybook', 'styleguide', 'design-system',
        'libs', 'lib', 'libraries',
        'monitoring', 'logs', 'logging',
    }

    # Check for exact matches first
    if dir_name in exact_infrastructure_names:
        return True

    # Check if directory starts with excluded patterns (for full path matching)
    excluded_prefixes = ['libs/', 'scripts/', 'tools/', 'utilities/']
    if any(dir_path_lower.startswith(prefix) for prefix in excluded_prefixes):
        return True

    # More specific config patterns that are clearly infrastructure
    specific_config_patterns = [
        'k8s-config', 'kubernetes-config', 'helm-config',
        'terraform-config', 'ansible-config',
        'nginx-config', 'apache-config',
        'docker-config', 'compose-config',
        'ci-config', 'cd-config', 'pipeline-config',
        'deployment-config', 'infrastructure-config'
    ]

    # Check specific config patterns
    if any(pattern in dir_name for pattern in specific_config_patterns):
        return True

    # Metrics exclusion patterns (more specific)
    metrics_exclusion_patterns = [
        'metrics-config', 'metrics-dashboard', 'metrics-setup',
        'prometheus-config', 'grafana-config', 'observability-config'
    ]

    if any(pattern in dir_name for pattern in metrics_exclusion_patterns):
        return True

    return False

def _generate_build_directory_mappings(source_dir: str) -> List[str]:
    """
    Generate possible build/dist directory paths for a source directory.
    Examples:
    - apps/my-app -> dist/apps/my-app, build/apps/my-app, out/apps/my-app
    - src/service -> dist/src/service, build/service, target/service
    """
    mappings = []

    # Common build output prefixes
    build_prefixes = ['dist', 'build', 'out', 'target', 'compiled']

    for prefix in build_prefixes:
        # Full path mapping: apps/my-app -> dist/apps/my-app
        mappings.append(f"{prefix}/{source_dir}")

        # Simplified mapping: apps/my-app -> dist/my-app (skip intermediate dirs)
        if '/' in source_dir:
            parts = source_dir.split('/')
            if len(parts) >= 2:
                # Take the last part: apps/my-app -> dist/my-app
                mappings.append(f"{prefix}/{parts[-1]}")
                # Take last two parts if more than 2: some/apps/my-app -> dist/apps/my-app
                if len(parts) >= 3:
                    mappings.append(f"{prefix}/{'/'.join(parts[-2:])}")

    return mappings

def _generate_source_directory_mappings(build_dir: str) -> List[str]:
    """
    Generate possible source directory paths from a build directory.
    Examples:
    - dist/apps/my-app -> apps/my-app, src/apps/my-app
    - build/my-service -> my-service, src/my-service
    """
    mappings = []

    # Remove build prefix
    build_prefixes = ['dist/', 'build/', 'out/', 'target/', 'compiled/']

    for prefix in build_prefixes:
        if build_dir.startswith(prefix):
            remainder = build_dir[len(prefix):]

            # Direct mapping: dist/apps/my-app -> apps/my-app
            mappings.append(remainder)

            # Common source prefixes
            source_prefixes = ['src', 'lib', 'packages']
            for src_prefix in source_prefixes:
                # src/apps/my-app pattern
                mappings.append(f"{src_prefix}/{remainder}")

                # If remainder has path, try src/last-part
                if '/' in remainder:
                    parts = remainder.split('/')
                    mappings.append(f"{src_prefix}/{parts[-1]}")

    return mappings

def _is_cicd_file(file_path: str) -> bool:
    """Check if file is a CI/CD file."""
    cicd_patterns = [
        '.github/workflows/',
        '.gitlab-ci.yml',
        'Jenkinsfile',
        'azure-pipelines.yml',
        'azure-pipelines.yaml',
        '.circleci/config.yml',
        '.travis.yml'
    ]

    return any(pattern in file_path for pattern in cicd_patterns)

def _group_deployment_signals_for_service(service_path: Path, deployment_signal_files: List[str]) -> List[str]:
    """Group deployment signals that belong to a specific service."""
    service_signals = []
    service_path_str = str(service_path)

    for signal_file in deployment_signal_files:
        # Check if signal file is in the service directory or references it
        if (signal_file.startswith(service_path_str) or
            service_path_str == "." or  # Root directory
            _is_cicd_file(signal_file)):  # CI/CD files can reference any service
            service_signals.append(signal_file)

    return service_signals

def _is_package_manager_file(filename: str) -> bool:
    """Check if file is a package manager file."""
    return filename in PACKAGE_MANAGER_FILES

def _extract_service_name(path: Path, package_file: str) -> str:
    """Extract service name from directory path or package file, with logging."""
    service_name = path.name
    logger.debug(f"Attempting to extract service name from path: {path}, package_file: {package_file}")

    # If it's the root directory, try to extract from package.json or similar
    if service_name == "." or not service_name:
        logger.debug("Path is root directory or has no name, attempting to extract from package file.")
        if package_file == "package.json":
            try:
                package_json_path = path / package_file
                logger.debug(f"Reading package.json at: {package_json_path}")
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    extracted_name = package_data.get('name', path.parent.name)
                    logger.info(f"Extracted service name from package.json: {extracted_name}")
                    return extracted_name
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(f"Failed to extract name from package.json: {e}")

        # Fallback to parent directory name
        fallback_name = path.parent.name if path.parent.name else "root"
        logger.info(f"Falling back to parent directory name: {fallback_name}")
        service_name = fallback_name
    else:
        logger.info(f"Using directory name as service name: {service_name}")

    return service_name
