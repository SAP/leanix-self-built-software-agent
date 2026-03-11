# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAP LeanIX Self Built Software Agent (`ai-based-discovery`) — a Python CLI tool that uses LangGraph multi-agent workflows to automatically discover and analyze self-built software in GitHub repositories. It identifies services, tech stacks, team ownership, and deployment patterns.

## Tech Stack

- **Language:** Python 3.13+
- **Package manager:** uv (with Hatchling build backend)
- **LLM framework:** LangChain, LangGraph
- **LLM providers:** OpenAI, Anthropic, SAP AI Core, Azure OpenAI (via `langchain-openai`, `langchain-anthropic`, `sap-ai-sdk-gen`)
- **Database:** SQLAlchemy ORM (SQLite default, PostgreSQL production)
- **CLI:** Click + Rich
- **GitHub integration:** PyGitHub
- **Logging:** structlog
- **Testing:** pytest, pytest-cov
- **Linting/formatting:** Ruff
- **Type checking:** mypy

## Development Setup

```bash
# Requires Python 3.13+ and uv package manager
uv venv && uv sync
source .venv/bin/activate
cp .env.example .env  # Configure API keys
```

## Common Commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_context_dto.py

# Run a single test by name
uv run pytest -k "test_name"

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy .

# Run the CLI
sbs-ai-discovery discover --org <org>
sbs-ai-discovery discover --repo <owner/repo>

# PostgreSQL via Docker (port 5433)
docker-compose up -d database
```

## Architecture

### LangGraph Workflow Pipeline

The core is a `StateGraph` in `src/workflows/repo_type_workflow.py` that processes repositories through a series of nodes:

```
clone_repo → load_context → detect_deployment_signals
  → (not deployable) → delete_repo → END
  → (deployable) → classify_repo_type
      → (mono-repo) → sbs_name_discovery → languages_agent → team_owners_agent → contributors_agent → tech_stack_detection → delete_repo → END
      → (single-purpose) → single_purpose_repo_inspector → languages_agent → ... same pipeline ... → END
```

### Central State Object

`RootRepoState` (`src/dto/state_dto.py`) is the single state object flowing through the entire workflow. It accumulates results from each node: repo metadata, deployability signals, repo type classification, discovered components (`SelfBuiltComponent`), languages, team owners, and tech stacks.

### Source Layout

- `src/cli/` — Click CLI commands (`discover`, `sync`, `context`) and utilities
- `src/nodes/agents/` — LLM-powered agents (repo type, monorepo inspector, languages, team owners, contributors, tech stack)
- `src/nodes/runnables/` — Non-LLM pipeline steps (clone, delete, deployment signals, context loading, tech stack detection)
- `src/nodes/router/` — Conditional routing functions (`route_on_repo_type`, `route_on_deployable`)
- `src/dto/` — Dataclasses (`slots=True`) and Pydantic models for state and structured LLM output
- `src/ai_provider/` — LLM provider initialization (OpenAI, Anthropic, Azure, SAP AI Core)
- `src/services/` — Database CRUD (SQLAlchemy ORM with SQLite or PostgreSQL)
- `src/db/` — SQLAlchemy models and connection setup
- `src/converter/` — State coercion from raw LLM responses
- `src/evals/` — Evaluation/scoring functions for agent output quality
- `src/tools/` — LangChain tools used by ReAct agents
- `tests/` — pytest tests with class-based organization and shared fixtures in `conftest.py`

### Database

SQLAlchemy ORM with `DeclarativeBase`. Default: SQLite (`sqlite:///sbs-ai-discovery.db`). Production: PostgreSQL on port 5433 via Docker Compose.

- Connection configured via `DATABASE_URL` env var (`src/config/config.py`)
- Engine and `SessionLocal` created in `src/db/conn.py`
- Models in `src/db/models.py`: `Organization`, `Repository`, `FactSheet`, `AiDiscoveryData`
- Tables auto-created via `Base.metadata.create_all()` — no migration framework
- CRUD operations go through service layer in `src/services/`

### LLM Provider Selection

Providers are auto-detected from environment variables in priority order: OpenAI → Anthropic Custom Hosting → Anthropic → SAP AI Core → Azure OpenAI. Only one provider needs to be configured.

### Licensing and REUSE Compliance

Licensed under Apache-2.0. REUSE compliance is handled via a blanket annotation in `REUSE.toml` covering all files (`path = "**"`). No per-file license headers are needed.