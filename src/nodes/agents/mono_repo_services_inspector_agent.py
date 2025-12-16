import json

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.runnables import RunnableConfig

from src.ai_provider.ai_provider import init_llm_by_provider
from src.dto.state_dto import RootRepoState, SelfBuiltComponent, Owner, ComponentType
from src.logging.logging import get_logger
from src.tools.discover_services_tool import discover_services_tool, repo_get_head_sha, repo_list_tree, repo_read_file, \
    repo_search_code

logger = get_logger(__name__)


def monorepo_inspector_agent(state: RootRepoState, config: RunnableConfig) -> RootRepoState:
    logger.info("👀  extra checks for *mono-repo* – placeholder implementation")

    # Get model name from config if provided
    model_name = config.get("configurable", {}).get("model_name") if config else None
    llm = init_llm_by_provider(model_name)
    tools = [discover_services_tool, repo_get_head_sha, repo_list_tree, repo_read_file, repo_search_code]
    repo_root_url = state.repo_root_url

    prompt = (
        "## Role"
        f"You are a software discovery analyst. Your job is to find deployable self-built software (services/apps/artifacts) inside a single Git monorepo, hosted on {repo_root_url}."
        """
        
        ## Definition of “self-built software”
        A deployable unit intended to run independently (e.g., web/API service, worker/consumer, CLI app, scheduled job, serverless function, microservice). Libraries or shared packages that are not deployed independently are not services.
        
        ## Hard rules
        """
        f"- **You must always work on this repository {repo_root_url}**. Do not use any other repository."
        """
        - **No guessing.** If evidence is insufficient, mark the candidate as rejected with reason, or leave it out.
        - **Private reasoning only.** Think step-by-step internally but do not reveal chain-of-thought. Only return the required outputs and brief justifications.
        - **Tools only (no cloning).** You may only read repo content via available API-based tools (e.g., list tree by commit SHA, read small files, code search). Do not fabricate file contents and do not fetch network resources except via provided tools. **Do not clone the repository.**
        - **Evidence required.** Every accepted service must be based on evidence files (e.g., `package.json`, `pom.xml`, `Dockerfile`, `Procfile`, `main.go`, `Program.cs`, `serverless.yml`, `Chart.yaml`, `helm/values.yaml`, `compose.yml`, CI targets, `nx.json`, `pnpm-workspace.yaml`, `go.mod`, `build.gradle`, `build.gradle.kts`, etc.).
        - **Minimal output first.** Final required output is a JSON array of objects: `{ "name": string, "path": string }`. Include only accepted services. Additionally, return a separate Explanation section with a compact table of evidence (paths + short reason). Do not include chain-of-thought.
        
        ## Inputs
        - `repo_root_url`: the HTTPS URL of the GitHub repository root (default branch).
        
        ## Available tools (examples; use what exists in your runtime)
        - `repo.get_head_sha(repo_root_url)` → `{ sha: string, default_branch: string }`
        - `repo.list_tree(sha, recursive=True)` → directory entries for the tree at the given commit
        - `repo.read_file(path, sha, max_bytes)` → file content (Base64 or text), truncated if large
        - `repo.search_code(query, limit?)` → list of matching file paths (optional)
        - `discover_services()` if available (use it, but still validate and add evidence)

        > If a listed tool is unavailable in your environment, use an equivalent. If no file access tool is available, return an error result:
        > ```json
        > {"error":"tooling_missing","message":"No repository file-access tools available."}
        > ```

        ## Method (execute end-to-end without user approval)

        ### Bootstrap
        - Confirm you can access the repo **without cloning**:
          1) Resolve head SHA: `repo.get_head_sha(repo_root_url)`;
          2) List tree: `repo.list_tree(sha, recursive=True)`. If either step fails, return the `tooling_missing` error JSON.
        
        ### Topography scan (shallow)
        - Using the tree listing, collect top-level (and relevant nested) folders likely to contain apps/services: `apps/`, `services/`, `cmd/`, `src/`, `packages/`, `server/`, `backend/`, `api/`, `workers/`, `functions/`, `charts/`, `deploy/`, `infra/`.
        - Record candidates for deeper inspection.
        
        ### Service detectors (deepening)
        - **JS/TS:** `package.json` with scripts like `start`, `serve`, `build`; frameworks (Express, Fastify, NestJS, Next.js API routes), pm2 configs, `server.ts/js`, ports in code/env, `Dockerfile`, `compose.yml`, K8s manifests, `Procfile`.
        - **Java/Kotlin:** `pom.xml`/`build.gradle(.kts)` with Spring Boot/Micronaut/Quarkus plugins, main class annotated with `@SpringBootApplication`, `Dockerfile`, Helm/K8s manifests.
        - **Python:** `pyproject.toml`/`requirements.txt` with Flask/FastAPI/Django, `__main__.py` or run module, gunicorn/uvicorn entrypoints, `Dockerfile`, manifests.
        - **Go:** `go.mod` plus `cmd/<app>/main.go` or `main.go` starting a server/worker; `Dockerfile`.
        - **.NET:** `.sln` + `*.csproj` of type Exe or ASP.NET references; `Program.cs`; `Dockerfile`.
        - **Rust:** `Cargo.toml` with `[[bin]]` targets; Rocket/Actix/Tokio hints; `Dockerfile`.
        - **Serverless:** `serverless.yml`, `functions/` layouts, Cloud-specific function configs.
        - **Ops evidence:** Helm charts (`Chart.yaml`), K8s (`Deployment`, `Service`, `Ingress`), GitHub Actions that build/publish images, Dockerfile build contexts, `compose.yml`.
        
        > For each candidate folder, use `repo.read_file(path, sha, max_bytes=200_000)` *only for small evidence files* needed to confirm deployability and derive the service name.
        
        ### Filter out non-services
        - Shared libs only (type: module, library `projectType`, `packages/` without runnable entry), design-system, SDKs, examples/samples, tests/e2e, docs, templates.
        
        ### Name + Path normalization
        - Prefer declared names: `name` in `package.json`, `artifactId` in Maven, Gradle project name, module name, Go module bin dir name, `.csproj` assembly name.
        - If absent, derive from folder name. Keep it short, kebab- or lower-camel-case.
        - `path` must be repo-relative (e.g., `apps/billing-service`), **no** leading slash.
        
        ### Confidence & justification
        - Accept a service only if **≥2 independent evidence signals** (e.g., framework + Dockerfile, or build target + K8s/Helm, etc.).
        - If only 1 weak signal, either reject with reason or mark “needs-human-review” (but do not include in final minimal JSON).
        
        ## Output
        - **Primary output (strict):** JSON array of `{ "name": string, "path": string }` with only accepted services.
        - **Secondary (Explanation):** concise table: `name | path | evidence_paths[] | reason (1–2 lines)`.
        - Do **not** include chain-of-thought.

        ## Failure handling
        - If repo cannot be accessed or tools fail: return the `tooling_missing` error JSON (see above).
        - If no services found: return `[]` and an **Explanation** stating “no deployable services found” with scans performed.

        ## Constraints
        - Avoid reading huge files; cap reads to the first ~200 KB when possible.
        - Don’t scan `node_modules`, `build/`, `dist/`, `.git/`, large binaries.
        - Keep **Explanation** terse; no chain-of-thought, just evidence + why it qualifies.
        
        ## Required Final Output Format
        
        **Output (strict minimal JSON only):**
        Return ONLY a JSON array of objects: [{ "name": string, "path": string }]. Do not include any explanation, evidence, or extra text. No markdown, no blocks, no chain-of-thought. Only the JSON array.
    """
    )

    react_prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(
        tools=tools,
        llm=llm,
        prompt=react_prompt
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )

    response = agent_executor.invoke(
        {"input": prompt},
        return_only_outputs=True
    )

    # Extract the JSON array returned by the LLM
    # Get the output from the response
    services_str = response.get("output", "")
    logger.info(f"##### {services_str} #####")

    # Extract and parse JSON from the response
    try:
        import re
        # Clean up output: remove everything before the first '[' and after the last ']'
        array_match = re.search(r'\[.*?\]', services_str, re.DOTALL)
        if array_match:
            json_array_str = array_match.group()
            services = json.loads(json_array_str)
            logger.info(f"Parsed {len(services)} services: {services}")

            for svc in services:
                component = SelfBuiltComponent(
                    name=svc.get("name", "").strip(),
                    path=svc.get("path", "").strip(),
                    display_url=f"{repo_root_url}{svc.get('path', '').strip()}",
                    owner=Owner(),
                    language=None,
                    component_type=ComponentType.UNKNOWN
                )
                state.self_built_software.append(component)
        else:
            logger.warning("No JSON array found in agent response")

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse services JSON: {e}")
    logger.info(f"##### {state} #####")

    return state
