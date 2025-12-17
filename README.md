# SBS AI Discovery

**A CLI tool and library for automated discovery and analysis of self-built software in GitHub repositories using AI agents. Identifies services, dependencies, technology stacks, and runtime details without human intervention.**

<p align="center">
 &nbsp;<a href="https://www.python.org/downloads/" target="_blank"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13+-blue.svg"></a>&nbsp;
</p>

![](docs/capture.gif)
## Introduction

SBS AI Discovery is a powerful tool for automatically discovering and analyzing self-built software across your GitHub organization. Using AI agents powered by LangChain and LangGraph, it provides detailed visibility into your software portfolio, helping you manage technical debt, understand dependencies, and maintain an accurate software catalog.

Development is supported by SAP, and is released under the Apache-2.0 License.

## Features

- Generates comprehensive software catalogs from GitHub organizations and repositories
- Supports multiple LLM providers: OpenAI, Azure OpenAI, Anthropic Claude, and SAP AI Core
- Automatic repository classification and service discovery
- Works seamlessly with PostgreSQL or SQLite databases
- Built on LangGraph for sophisticated multi-agent workflows
- Production-ready with structured logging and error handling

## Installation

### Recommended

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/LeanIX/sbs-ai-discovery.git
cd sbs-ai-discovery
uv venv && uv sync
source .venv/bin/activate
```

### Homebrew

```bash
# Install uv
brew install uv

# Clone and setup
git clone https://github.com/LeanIX/sbs-ai-discovery.git
cd sbs-ai-discovery
uv venv && uv sync
source .venv/bin/activate
```

### Python Version

Python 3.13+ is required. Use [mise](https://mise.jdx.dev/) for easy version management:

```bash
brew install mise
mise install python 3.13.5
mise use -g python 3.13.5
```

## Getting Started

### Configuration

Configure your environment variables by copying the example file:

```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

#### Required Variables

Set **one** LLM provider:

**OpenAI:**
```bash
export OPENAI_API_KEY="sk-your-openai-api-key"
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

**Azure OpenAI:**
```bash
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export OPENAI_API_VERSION="2023-12-01-preview"
```

**SAP AI Core:**
```bash
export AICORE_CLIENT_ID="sb-your-client-id"
export AICORE_CLIENT_SECRET="your-client-secret"
export AICORE_AUTH_URL="https://your-auth-url.authentication.sap.hana.ondemand.com"
export AICORE_BASE_URL="https://api.ai.your-region.aws.ml.hana.ondemand.com"
export AICORE_RESOURCE_GROUP="your-resource-group"
```

**GitHub Integration:**
```bash
export GITHUB_TOKEN="ghp_your-github-token"
export GITHUB_ORG="your-organization"
```

**Database (optional - defaults to SQLite):**
```bash
export DATABASE_URL="sqlite:///./ai_discovery.db"
# Or for PostgreSQL:
# export DATABASE_URL="postgresql://user:password@localhost:5432/database"
```

### Discover Repositories

Analyze repositories in your GitHub organization:

```bash
# Discover all repositories in an organization
sbs-ai-discovery discover --org myorg

# Discover a single repository
sbs-ai-discovery discover --repo owner/repo

# Use a specific LLM model
sbs-ai-discovery discover --org myorg --llm gpt-4o
sbs-ai-discovery discover --org myorg --llm claude-sonnet

# Dry run without saving to database
sbs-ai-discovery discover --org myorg --dry-run

# Save results to JSON file
sbs-ai-discovery discover --org myorg --output results.json

# Limit number of repositories
sbs-ai-discovery discover --org myorg --limit 10
```

### Sync Command

Synchronize discovery results with external systems:

```bash
# Sync repositories
sbs-ai-discovery sync --org myorg

```

### Output Formats

The CLI supports various output options:

- **Console**: Human-readable output (default)
- **JSON**: Machine-readable structured data (`--output results.json`)
- **Database**: Persistent storage (automatic when `DATABASE_URL` is set)

### Supported LLM Models

**OpenAI:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`

**Anthropic:** `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`

**Azure OpenAI:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-35-turbo`

**SAP AI Core:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`

**Model Aliases:**
- `claude-sonnet` → `claude-3-5-sonnet-20241022`
- `claude-opus` → `claude-3-opus-20240229`
- `claude-haiku` → `claude-3-haiku-20240307`

## Project Structure

```
sbs-ai-discovery/
├─ main.py                   # Legacy entrypoint
├─ src/
│  ├─ ai_provider/           # LLM provider initialization
│  ├─ nodes/                 # LangGraph nodes for workflow steps
│  ├─ tools/                 # LangChain tools (GitHub API, classification)
│  ├─ workflows/             # Business workflows with multiple agents
│  ├─ db/                    # Database models and initialization
│  ├─ services/              # Business logic services
│  ├─ dto/                   # Data transfer objects and state definitions
│  ├─ logging/               # Structured logging configuration
│  └─ utils/                 # Utility functions
├─ db-scripts/               # Database initialization scripts
├─ docker-compose.yaml       # PostgreSQL setup for local development
└─ pyproject.toml            # Project dependencies and configuration
```

## Key Technologies

| Library        | Purpose                                           |
| -------------- | ------------------------------------------------- |
| **LangChain**  | Chain-of-thought prompts and LLM integrations     |
| **LangGraph**  | State-based orchestration for AI agent workflows  |
| **SQLAlchemy** | Database ORM for PostgreSQL and SQLite            |
| **PyGithub**   | GitHub API client for repository analysis         |
| **structlog**  | Structured logging for better observability       |
| **uv**         | Fast Python package and project manager           |

## Database Setup

### SQLite (Quick Start)

SQLite is used by default with no additional configuration:

```bash
export DATABASE_URL="sqlite:///./ai_discovery.db"
```

### PostgreSQL (Production)

For production deployments, use PostgreSQL:

```bash
# Using Docker Compose
docker-compose up -d database
export DATABASE_URL="postgresql://sbs-ai-discovery-user:sbs-ai-discovery-password@localhost:5433/sbs-ai-discovery-db"

# Run migrations
uv run alembic upgrade head
```

## Development

### Code Quality Tools

| Tool     | Purpose            | Command                   |
| -------- | ------------------ | ------------------------- |
| **Ruff** | Linter / formatter | `uv run ruff check --fix` |
| **mypy** | Static typing      | `uv run mypy`             |

### Adding Dependencies

```bash
uv add <package>            # Runtime dependency
uv add --dev <package>      # Development dependency
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## How It Works

### Discovery Pipeline

1. **Repository Fetching**: Connects to GitHub API and retrieves repositories from the specified organization
2. **AI Analysis**: Each repository is analyzed using LLM-powered agents that:
   - Examine repository structure and files
   - Classify the repository type (service, library, infrastructure, etc.)
   - Identify technology stack and frameworks
   - Discover services and their metadata
3. **Data Storage**: Results are persisted to the database for querying and reporting
4. **Workflow Orchestration**: LangGraph manages the state and flow between different analysis steps

### Architecture

- **Workflows**: High-level orchestration of analysis tasks (`src/workflows/`)
- **Nodes**: Individual processing steps in the workflow (`src/nodes/`)
- **Tools**: External integrations like GitHub API (`src/tools/`)
- **AI Provider**: Abstraction layer supporting multiple LLM providers (`src/ai_provider/`)

## Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository and create a new branch
2. Make your changes following PEP 8 style guidelines
3. Run linters and type checkers: `uv run ruff check --fix && uv run mypy`
4. Test your changes thoroughly
5. Submit a pull request with a clear description

Please ensure your code:
- Follows PEP 8 style guidelines
- Includes type hints for better code quality
- Has appropriate error handling
- Is well-documented with docstrings

## License

Apache License 2.0

## Support

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/LeanIX/sbs-ai-discovery/issues)
- **Discussions**: Join conversations in [GitHub Discussions](https://github.com/LeanIX/sbs-ai-discovery/discussions)

---

Built with [LangChain](https://www.langchain.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), and [PyGithub](https://github.com/PyGithub/PyGithub).
