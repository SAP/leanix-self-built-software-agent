import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.dto.state_dto import RootRepoState
from src.logging.logging import get_logger
from src.nodes.agents.workflow_classifier_agent import workflow_classifier_agent

logger = get_logger(__name__)

@dataclass
class DeploymentSignal:
    """Represents a deployment indicator found in the repository."""
    category: str
    signal_type: str
    file_path: str
    description: str
    strength: str  # 'strong', 'medium', 'weak'

def deployment_signals_detection_runnable(state: RootRepoState) -> RootRepoState:
    """
    Analyze repository for deployment signals to determine if it contains deployable components.
    Uses a strength-based approach to reduce false positives.
    """
    if not state.local_path:
        logger.warning("No local path available for deployment signal analysis")
        return state

    local_repo_path = Path(state.local_path)
    if not local_repo_path.exists():
        logger.error(f"Local repository path does not exist: {local_repo_path}")
        return state

    logger.info(f"Analyzing deployment signals in: {local_repo_path}")

    deployment_signals = detect_deployment_signals(local_repo_path)

    strong_signals = [signal for signal in deployment_signals if signal.strength == 'strong']
    state.deployable_signal_files = [signal.file_path for signal in strong_signals]

    # Log findings
    if deployment_signals:
        logger.info(f"Found {len(deployment_signals)} deployment signals:")
        for signal in deployment_signals:
            logger.info(f"  {signal.strength.upper()}: {signal.category}:{signal.signal_type} at {signal.file_path}")
        logger.info(f"Strong signals added to deployable_signal_files: {len(strong_signals)}")
    else:
        logger.info("No deployment signals detected")

    is_deployable = _evaluate_deployment_signals(deployment_signals)
    if is_deployable:
        state.deployable = True
        return state

    ci_cd_signals = [
        signal for signal in deployment_signals
        if signal.category == 'ci_cd' and signal.strength in ['strong', 'medium']
    ]
    has_app_service_deploy = has_service_deployment_workflow_llm(local_repo_path, ci_cd_signals)
    if has_app_service_deploy:
        logger.info(f"Repository has deployable service detection. "
                    f"Also contains tool/automation workflows.")
        state.deployable = True
    else:
        logger.info(f"Repository does not have deployable service detection. "
                    f"Also does not contain tool/automation workflows.")
        state.deployable = False

    return state

def detect_deployment_signals(repo_path: Path) -> List[DeploymentSignal]:
    """
    Detect various deployment signals in the repository.
    """
    signals = []

    # Define deployment signal patterns
    signal_patterns = {
        "package_manager": {
            "java": [
                ("**/pom.xml", "Maven Project"),
                ("**/build.gradle", "Gradle Project"),
                ("**/build.gradle.kts", "Gradle Kotlin Project"),
            ],
            "javascript": [
                ("**/package.json", "NPM/Node.js Project"),
                ("**/project.json", "NX/Build Tool Project"),
                ("**/yarn.lock", "Yarn Project"),
                ("**/pnpm-lock.yaml", "PNPM Project"),
            ],
            "python": [
                ("**/requirements.txt", "Python Requirements"),
                ("**/pyproject.toml", "Python Project"),
                ("**/setup.py", "Python Setup"),
                ("**/Pipfile", "Pipenv Project"),
                ("**/poetry.lock", "Poetry Project"),
            ],
            "dotnet": [
                ("**/*.csproj", ".NET Project"),
                ("**/*.sln", ".NET Solution"),
                ("**/packages.config", ".NET Packages"),
            ],
            "go": [
                ("**/go.mod", "Go Module"),
            ],
            "rust": [
                ("**/Cargo.toml", "Rust Cargo Project"),
            ],
            "php": [
                ("**/composer.json", "PHP Composer Project"),
            ],
            "ruby": [
                ("**/Gemfile", "Ruby Gem Project"),
            ],
        },
        "kubernetes": {
            "deployment_manifests": [
                ("**/deployment.yaml", "Kubernetes Deployment"),
                ("**/deployment.yml", "Kubernetes Deployment"),
                ("**/statefulset.yaml", "Kubernetes StatefulSet"),
                ("**/statefulset.yml", "Kubernetes StatefulSet"),
                ("**/job.yaml", "Kubernetes Job"),
                ("**/job.yml", "Kubernetes Job"),
                ("**/cronjob.yaml", "Kubernetes CronJob"),
                ("**/cronjob.yml", "Kubernetes CronJob"),
                ("**/*-deployment.yaml", "Kubernetes Deployment"),
                ("**/*-deployment.yml", "Kubernetes Deployment"),
                ("**/k8s/**/*.yaml", "Kubernetes Manifest"),
                ("**/k8s/**/*.yml", "Kubernetes Manifest"),
                ("**/kubernetes/**/*.yaml", "Kubernetes Manifest"),
                ("**/kubernetes/**/*.yml", "Kubernetes Manifest"),
                ("**/manifests/**/*.yaml", "Kubernetes Manifest"),
                ("**/manifests/**/*.yml", "Kubernetes Manifest"),
            ],
            "helm": [
                ("**/Chart.yaml", "Helm Chart"),
                ("**/Chart.yml", "Helm Chart"),
                ("**/values.yaml", "Helm Values"),
                ("**/values.yml", "Helm Values"),
                ("**/charts/**", "Helm Chart Directory"),
                ("**/templates/**/*.yaml", "Helm Template"),
                ("**/templates/**/*.yml", "Helm Template"),
            ],
            "kustomize": [
                ("**/kustomization.yaml", "Kustomize"),
                ("**/kustomization.yml", "Kustomize"),
                ("**/Kustomization", "Kustomize"),
            ]
        },
        "containerization": {
            "docker": [
                ("**/Dockerfile", "Docker Build"),
                ("**/Dockerfile.*", "Docker Build Variant"),
                ("**/docker-compose.yml", "Docker Compose"),
                ("**/docker-compose.yaml", "Docker Compose"),
                ("**/docker-compose.*.yml", "Docker Compose Variant"),
                ("**/docker-compose.*.yaml", "Docker Compose Variant"),
                ("**/.dockerignore", "Docker Configuration"),
            ],
            "buildpacks": [
                ("**/project.toml", "Cloud Native Buildpacks"),
                ("**/Procfile", "Buildpack Process File"),
            ]
        },
        "serverless": {
            "framework_agnostic": [
                ("**/serverless.yml", "Serverless Framework"),
                ("**/serverless.yaml", "Serverless Framework"),
            ],
            "aws": [
                ("**/template.yaml", "AWS SAM Template"),
                ("**/template.yml", "AWS SAM Template"),
                ("**/sam-template.yaml", "AWS SAM Template"),
                ("**/cloudformation.yaml", "AWS CloudFormation"),
                ("**/cloudformation.yml", "AWS CloudFormation"),
                ("**/*.sam.yaml", "AWS SAM"),
                ("**/*.sam.yml", "AWS SAM"),
            ],
            "azure": [
                ("**/host.json", "Azure Functions"),
                ("**/function.json", "Azure Function"),
                ("**/proxies.json", "Azure Functions Proxies"),
            ],
            "gcp": [
                ("**/app.yaml", "Google App Engine"),
                ("**/app.yml", "Google App Engine"),
                ("**/cron.yaml", "Google App Engine Cron"),
                ("**/queue.yaml", "Google App Engine Queue"),
                ("**/cloudbuild.yaml", "Google Cloud Build"),
                ("**/cloudbuild.yml", "Google Cloud Build"),
            ],
            "vercel": [
                ("**/vercel.json", "Vercel Deployment"),
                ("**/now.json", "Vercel (Now) Deployment"),
            ],
            "netlify": [
                ("**/netlify.toml", "Netlify Deployment"),
            ],
            "cloudflare": [
                ("**/wrangler.toml", "Cloudflare Workers"),
            ]
        },
        "platform_specific": {
            "heroku": [
                ("**/Procfile", "Heroku Process File"),
                ("**/app.json", "Heroku App Configuration"),
                ("**/runtime.txt", "Heroku Runtime"),
            ],
            "fly_io": [
                ("**/fly.toml", "Fly.io Deployment"),
            ],
            "render": [
                ("**/render.yaml", "Render Deployment"),
            ],
            "railway": [
                ("**/railway.json", "Railway Deployment"),
                ("**/railway.toml", "Railway Deployment"),
            ]
        },
        "ci_cd": {
            "github_actions": [
                ("**/.github/workflows/*.yml", "GitHub Actions Workflow"),
                ("**/.github/workflows/*.yaml", "GitHub Actions Workflow"),
            ],
            "gitlab": [
                ("**/.gitlab-ci.yml", "GitLab CI"),
            ],
            "jenkins": [
                ("**/Jenkinsfile", "Jenkins Pipeline"),
            ],
            "azure_pipelines": [
                ("**/azure-pipelines.yml", "Azure Pipelines"),
                ("**/azure-pipelines.yaml", "Azure Pipelines"),
            ],
            "circle_ci": [
                ("**/.circleci/config.yml", "CircleCI"),
            ],
            "travis": [
                ("**/.travis.yml", "Travis CI"),
            ]
        },
        "infrastructure_as_code": {
            "terraform": [
                ("**/*.tf", "Terraform"),
                ("**/main.tf", "Terraform Main"),
                ("**/variables.tf", "Terraform Variables"),
                ("**/outputs.tf", "Terraform Outputs"),
            ],
            "pulumi": [
                ("**/Pulumi.yaml", "Pulumi"),
                ("**/Pulumi.yml", "Pulumi"),
                ("**/__main__.py", "Pulumi Python"),
                ("**/index.ts", "Pulumi TypeScript"),
            ],
            "cdk": [
                ("**/cdk.json", "AWS CDK"),
                ("**/cdk.yaml", "AWS CDK"),
            ]
        },
        "gitops": {
            "argocd": [
                ("**/application.yaml", "Argo CD Application"),
                ("**/application.yml", "Argo CD Application"),
                ("**/argocd/**/*.yaml", "Argo CD Configuration"),
            ],
            "flux": [
                ("**/kustomization.yaml", "Flux Kustomization"),
                ("**/helmrelease.yaml", "Flux Helm Release"),
                ("**/gitrepository.yaml", "Flux Git Repository"),
            ]
        }
    }

    # Search for deployment signals
    for category, subcategories in signal_patterns.items():
        for signal_type, patterns in subcategories.items():
            for pattern, description in patterns:
                found_files = list(repo_path.glob(pattern))
                for file_path in found_files:
                    if _is_valid_deployment_file(file_path):
                        relative_path = file_path.relative_to(repo_path)
                        signals.append(DeploymentSignal(
                            category=category,
                            signal_type=signal_type,
                            file_path=str(relative_path),
                            description=description,
                            strength='weak'  # Default strength, will be updated later
                        ))

    # Content-based detection for CI/CD deployment steps
    signals.extend(_detect_cicd_deployment_content(repo_path))

    # Container reference detection
    signals.extend(_detect_container_references(repo_path))

    # Classify signal strength based on combination requirements
    signals = _classify_signal_strength_by_combination(signals)

    return signals

def _is_valid_deployment_file(file_path: Path) -> bool:
    """Check if file is a valid deployment configuration file."""

    # Skip if in excluded directories
    excluded_dirs = {
        'node_modules', '.git', '__pycache__', 'target', 'build',
        'dist', '.venv', 'venv', 'vendor', 'deps'
    }

    if any(part in excluded_dirs for part in file_path.parts):
        return False

    # Skip if file is too large (likely not a config file)
    try:
        if file_path.stat().st_size > 1024 * 1024:  # 1MB
            return False
    except OSError:
        return False

    return True

def _detect_cicd_deployment_content(repo_path: Path) -> List[DeploymentSignal]:
    """Detect deployment-related content in CI/CD files."""
    signals = []

    ci_files = [
        *repo_path.glob("**/.github/workflows/*.yml"),
        *repo_path.glob("**/.github/workflows/*.yaml"),
        *repo_path.glob("**/.gitlab-ci.yml"),
        *repo_path.glob("**/Jenkinsfile"),
        *repo_path.glob("**/azure-pipelines.yml"),
        *repo_path.glob("**/azure-pipelines.yaml"),
    ]

    deployment_keywords = [
        'docker build', 'docker push', 'kubectl apply', 'helm upgrade',
        'helm install', 'serverless deploy', 'aws ecs', 'gcloud deploy',
        'terraform apply', 'pulumi up', 'deploy:', 'deployment:',
        'aws lambda', 'azure functions', 'vercel --prod', 'netlify deploy'
    ]

    for ci_file in ci_files:
        if not _is_valid_deployment_file(ci_file):
            continue

        try:
            content = ci_file.read_text(encoding='utf-8').lower()
            for keyword in deployment_keywords:
                if keyword in content:
                    relative_path = ci_file.relative_to(repo_path)
                    signals.append(DeploymentSignal(
                        category="ci_cd",
                        signal_type="deployment_step",
                        file_path=str(relative_path),
                        description=f"CI/CD with deployment step: {keyword}",
                        strength='medium'  # Content-based signals are medium strength
                    ))
                    break  # Only add one signal per file
        except Exception as e:
            logger.debug(f"Could not read CI file {ci_file}: {e}")

    return signals

def _detect_container_references(repo_path: Path) -> List[DeploymentSignal]:
    """Detect references to container builds in compose/manifest files."""
    signals = []

    compose_files = [
        *repo_path.glob("**/docker-compose*.yml"),
        *repo_path.glob("**/docker-compose*.yaml"),
    ]

    for compose_file in compose_files:
        if not _is_valid_deployment_file(compose_file):
            continue

        try:
            content = compose_file.read_text(encoding='utf-8')
            # Look for build context references
            if re.search(r'build:\s*\.', content) or re.search(r'build:\s*\w+', content):
                relative_path = compose_file.relative_to(repo_path)
                signals.append(DeploymentSignal(
                    category="containerization",
                    signal_type="local_build",
                    file_path=str(relative_path),
                    description="Docker Compose with local build context",
                    strength='medium'  # Detected build context is medium strength
                ))
        except Exception as e:
            logger.debug(f"Could not read compose file {compose_file}: {e}")

    return signals

def _classify_signal_strength_by_combination(signals: List[DeploymentSignal]) -> List[DeploymentSignal]:
    """
    Classify the strength of deployment signals based on combination requirements.

    Strong signal requires ALL THREE components:
    1. Package manager file (pom.xml, package.json, etc.)
    2. CI/CD file (.github/workflows/*.yml, .gitlab-ci.yml, etc.)
    3. Way to run (Dockerfile, docker-compose.yml, etc.)

    Medium signal requires at least 2 of the 3 components.
    Weak signal is everything else.
    """

    # Group signals by category to check combinations
    categories_found = set(signal.category for signal in signals)

    # Check if we have all three required categories
    has_package_manager = "package_manager" in categories_found
    has_ci_cd = "ci_cd" in categories_found or any(s.category == "ci_cd" and s.signal_type == "deployment_step" for s in signals)
    has_way_to_run = ("containerization" in categories_found or
                     "serverless" in categories_found or
                     "platform_specific" in categories_found or
                     "kubernetes" in categories_found)

    # Count how many of the three components we have
    component_count = sum([has_package_manager, has_ci_cd, has_way_to_run])

    logger.info(f"Deployment components found - Package Manager: {has_package_manager}, CI/CD: {has_ci_cd}, Way to Run: {has_way_to_run}")

    # Classify all signals based on the overall combination
    for signal in signals:
        if component_count >= 3:
            # All three components present - strong signals for relevant categories
            if (signal.category in ["package_manager", "ci_cd", "containerization", "serverless", "platform_specific", "kubernetes"] or
                (signal.category == "ci_cd" and signal.signal_type == "deployment_step")):
                signal.strength = 'strong'
            else:
                signal.strength = 'medium'
        elif component_count >= 2:
            # Two components present - medium strength
            if (signal.category in ["package_manager", "ci_cd", "containerization", "serverless", "platform_specific", "kubernetes"] or
                (signal.category == "ci_cd" and signal.signal_type == "deployment_step")):
                signal.strength = 'medium'
            else:
                signal.strength = 'weak'
        else:
            # Only one or no components - weak
            signal.strength = 'weak'

    return signals

def _evaluate_deployment_signals(signals: List[DeploymentSignal]) -> bool:
    """
    Evaluate if the repository is deployable based on the new combination-based signal strength.

    Rules for determining deployability:
    1. Any strong signal = deployable (requires all 3 components: package manager + CI/CD + way to run)
    2. Otherwise = not deployable
    """
    if not signals:
        return False

    # Categorize signals by strength
    strong_signals = [s for s in signals if s.strength == 'strong']
    medium_signals = [s for s in signals if s.strength == 'medium']
    weak_signals = [s for s in signals if s.strength == 'weak']

    # Rule 1: Only strong signals mean deployable (all 3 components present)
    if strong_signals:
        logger.info(f"Found {len(strong_signals)} strong deployment signals (all 3 components present) - repository is deployable")
        return True

    # All other cases are not deployable
    logger.info(f"Insufficient deployment evidence: {len(strong_signals)} strong, {len(medium_signals)} medium, {len(weak_signals)} weak signals")
    logger.info("Repository requires all 3 components (package manager + CI/CD + way to run) for deployability")
    return False

IGNORED_DEPLOY_PATHS = [
    "test/", "tests/", "template/", "templates/",
    "example/", "examples/", "spec/", "sample/"
]
def _is_ignored_deploy_file(file_path: str) -> bool:
    """True if the path is under a test/template/example/spec/sample folder"""
    path_lc = file_path.lower()
    return any(p in path_lc for p in IGNORED_DEPLOY_PATHS)

def has_service_deployment_workflow_llm(repo_path: Path, filtered_strong_signals: List[DeploymentSignal]) -> bool:
    """
    Analyze all workflow files listed in filtered_strong_signals using the LLM classifier agent.
    Returns True if any workflow is classified as 'deployment'.
    Passes strong deployment signals as context to the LLM.
    """
    logger.info(f"Classifying {len(filtered_strong_signals)} workflow files using LLM agent.")

    # Gather all strong deployment signals (file names) for context
    all_signals = detect_deployment_signals(repo_path)
    strong_signal_files = [
        signal.file_path for signal in all_signals if signal.strength == 'strong'
    ]

    for signal in filtered_strong_signals:
        wf = repo_path / signal.file_path
        try:
            content = wf.read_text(encoding="utf-8")
            logger.info(f"Classifying workflow '{wf.name}' using LLM agent. (path: {signal.file_path})")
            classification = workflow_classifier_agent(
                workflow_content=content,
                workflow_path=signal.file_path,
                repo_path=str(repo_path),
                strong_signals=strong_signal_files
            )
            logger.info(f"AI agent classified workflow '{wf.name}' as: {classification}")
            if classification == "deployment":
                return True
        except Exception as e:
            logger.warning(f"Failed to read or classify workflow '{wf.name}': {e}")

    logger.info("No service deployment workflows detected by LLM in this repo.")
    return False
