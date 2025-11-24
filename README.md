# AI-Based Self-Built Software Discovery

> **Automated discovery and analysis of self-built software in GitHub repositories using AI agents and code analysis.**

Discover self‑built software running in production – and identify its owners, dependencies, technology stacks, and runtime details – **without human intervention**, by leveraging AI agents powered by LangChain and LangGraph.

## ✨ Features

- 🤖 **Multi-Provider LLM Support**: Works with OpenAI, Azure OpenAI, Anthropic Claude, and SAP AI Core
- 🔍 **Intelligent Repository Analysis**: Automatically classifies repository types and discovers services
- 📊 **Flexible Database Backend**: Supports both PostgreSQL and SQLite
- 🔗 **GitHub Integration**: Direct integration with GitHub API for repository analysis
- 🎯 **AI Agent Workflows**: Built on LangGraph for sophisticated multi-step reasoning
- 📈 **Production Ready**: Structured logging, error handling, and observability

---

## 🚀 Quick Start

Get started in 5 minutes:

```bash
# 1. Install uv (if not already installed)
brew install uv  # macOS - see docs for other platforms

# 2. Clone and setup
git clone <repository-url>
cd sbs-ai-discovery
uv venv && uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys and GitHub credentials

# 4. Start local database (optional - uses SQLite by default)
docker-compose up -d database

# 5. Run the application
source .venv/bin/activate
python main.py
```

For detailed setup instructions, see the sections below.

---

## 1. Prerequisites

### 1.1  Python ≥ 3.13

We develop and test on Python 3.13.x.  Any newer patch release (e.g. 3.13.5, 3.13.6) works the same.

> **Tip (Mac & Linux)**  Use [**mise**](https://mise.jdx.dev/) for painless multi‑version management.
>
> ```bash
> brew install mise            # once
>
> mise ls‑remote python        # list all available 3.x versions
> mise install python 3.13.5   # download & compile once
> mise use ‑g python 3.13.5    # use it globally for this repo
> ```

### 1.2  A modern package / venv manager – **uv**

We use [**uv**](https://docs.astral.sh/uv/) for dependency management. It's blazingly fast, deterministic, and works great with lock files.

```bash
brew install uv               # macOS
# Or see https://docs.astral.sh/uv/getting-started/installation/ for other platforms
```

### 1.3  Linters & static analysis

| Tool                                     | Purpose            | Run with                  |
| ---------------------------------------- | ------------------ | ------------------------- |
| [**Ruff**](https://docs.astral.sh/ruff/) | Linter / formatter | `uv run ruff check --fix` |
| [**mypy**](https://mypy-lang.org/)       | Static typing      | `uv run mypy`             |

We follow [PEP 8](https://peps.python.org/pep-0008/) – *Ruff* is configured to apply it automatically.

---

## 2. First‑time setup

### 2.1  Clone & create an isolated environment

```bash
# in the repo root
uv venv       # creates .venv and activates it (fish/zsh/bash compatible)
uv sync       # installs everything from pyproject.toml/uv.lock
```

### 2.2  Adding or upgrading packages

```bash
uv add <package>            # runtime dependency
uv add --dev <package>      # dev‑only dependency
```

(Lock file and `pyproject.toml` are updated automatically.)

---

## 3. Environment variables

Create a `.env` file in the project root with the required variables for your setup. You can copy `.env.example` as a starting point:

```bash
cp .env.example .env
# Then edit .env with your actual credentials
```

### Required Variables

| Variable                                                                                                    | Description                                                                                                                                                         | Required For                                       |
| ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `OPENAI_API_KEY`                                                                                            | Your OpenAI API key → [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)                                                                | OpenAI provider                                    |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION`                                     | Your Azure OpenAI credentials → [https://portal.azure.com/](https://portal.azure.com/)                                                                            | Azure OpenAI provider                              |
| `ANTHROPIC_API_KEY`                                                                                         | Your Anthropic API key → [https://console.anthropic.com/](https://console.anthropic.com/)                                                                         | Anthropic Claude provider                          |
| `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, `AICORE_AUTH_URL`, `AICORE_BASE_URL`, `AICORE_RESOURCE_GROUP` | SAP AI Core credentials (optional, for SAP BTP users)                                                                                                              | SAP AI Core provider                               |
| `LLM_DEPLOYMENT`                                                                                            | Model name to use (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")                                                                                                  | Optional (has provider-specific defaults)          |
| `DATABASE_URL`                                                                                              | Database connection string (PostgreSQL or SQLite)                                                                                                                  | All configurations                                 |
| `GITHUB_TOKEN`                                                                                              | GitHub Personal Access Token → [Creating a token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) | GitHub integration                                 |
| `GITHUB_ORG`                                                                                                | GitHub organization name to analyze                                                                                                                                | GitHub integration                                 |

> ⚠️  **Secrets** should never be committed.  `dotenv` loads them locally; CI/CD injects them via the secret store.

---

## 4. Project layout

```
sbs-ai-discovery/
├─ main.py                   # 🏁 entrypoint – CLI for batch processing repositories
├─ src/
│  ├─ ai_provider/           # LLM provider initialization (OpenAI, Azure, Anthropic, SAP AI Core)
│  ├─ nodes/                 # reusable LangGraph nodes for workflow steps
│  ├─ tools/                 # LangChain tools (GitHub API, repository classification, service discovery)
│  ├─ workflows/             # business workflows composed of multiple agents
│  ├─ db/                    # database models and initialization
│  ├─ services/              # business logic services (organizations, repositories)
│  ├─ dto/                   # data transfer objects and state definitions
│  ├─ logging/               # structured logging configuration
│  └─ utils/                 # utility functions and helpers
├─ db-scripts/               # database initialization scripts
├─ docker-compose.yaml       # PostgreSQL database setup for local development
└─ pyproject.toml            # project dependencies and configuration
```

---
## 5. LLM Provider Configuration

The application supports multiple LLM providers through environment variables. Configure **one** of the following:

### 5.1  OpenAI

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-your-openai-api-key"
export LLM_DEPLOYMENT="gpt-4o"  # Optional, defaults to "gpt-4o"
```

### 5.2  Azure OpenAI

Set your Azure OpenAI credentials:

```bash
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource-name.openai.azure.com/"
export OPENAI_API_VERSION="2023-12-01-preview"  # Optional, defaults to latest
export LLM_DEPLOYMENT="gpt-4o"  # Optional, defaults to "gpt-4o"
```

### 5.3  Anthropic (Claude)

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export LLM_DEPLOYMENT="claude-3-5-sonnet-20241022"  # Optional, defaults to "claude-3-5-sonnet-20241022"
```

### 5.4  SAP AI Core

Set your AI Core credentials and configuration:

```bash
export AICORE_CLIENT_ID="sb-your-aicore-client-id"
export AICORE_CLIENT_SECRET="your-aicore-client-secret"
export AICORE_AUTH_URL="https://your-auth-url.authentication.sap.hana.ondemand.com"
export AICORE_BASE_URL="https://api.ai.your-region.aws.ml.hana.ondemand.com"
export AICORE_RESOURCE_GROUP="your-resource-group"
export LLM_DEPLOYMENT="gpt-4o"  # Optional, defaults to "gpt-4o"
```

### 5.5  Usage in Code

Initialize the LLM provider in your application:

```python
from ai_provider.aI_provider import init_llm_by_provider

# Automatically detects configured provider and initializes appropriate LLM
llm = init_llm_by_provider()
```

The `init_llm_by_provider()` function will:
- Check for available provider credentials in order: OpenAI → Azure OpenAI → Anthropic → SAP AI Core
- Initialize the appropriate LangChain LLM client
- Raise a `ValueError` if no provider is configured
- Raise an `ImportError` if required dependencies are missing

> **Note:** The function uses the first available provider it finds. Configure only one provider at a time for predictable behavior.

---

## 6. Database Configuration

The application supports multiple database backends for storing discovery results, analysis data, and workflow state. Configure **one** of the following:

### 6.1  PostgreSQL (Recommended for Production)

Set your PostgreSQL connection:

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/database_name"
```

For development with Docker Compose:
```bash
# Use the provided docker-compose.yaml
docker-compose up -d postgres
export DATABASE_URL="postgresql://postgres:password@localhost:5432/ai_discovery"
```

### 6.2  SQLite (Quick Setup & Development)

For local development and testing:

```bash
export DATABASE_URL="sqlite:///./ai_discovery.db"
```

### 6.3  Database Migrations

Initialize or update your database schema:

```bash
# Run database migrations
uv run alembic upgrade head

# Or using the provided scripts
./db-scripts/init.sql  # For initial setup
```

### 6.4  Database Features

The database stores:
- **Discovery Results**: Repository analysis, dependency graphs, technology stacks

> **💡 Tip:** Use PostgreSQL for production deployments to take advantage of advanced features like JSON operations, full-text search, and better concurrent access handling.

---

## 7. Key libraries

| Library                   | Why we use it                                                 | Docs                                                                                 |
| ------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **LangChain**             | Chain‑of‑thought prompts, tool‑calling, and LLM integrations | [https://python.langchain.com/docs/](https://python.langchain.com/docs/)             |
| **LangGraph**             | State‑based orchestration for building AI agent workflows     | [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/) |
| **SQLAlchemy**            | Database ORM for PostgreSQL and SQLite                        | [https://www.sqlalchemy.org/](https://www.sqlalchemy.org/)                          |
| **PyGithub**              | GitHub API client for repository analysis                    | [https://pygithub.readthedocs.io/](https://pygithub.readthedocs.io/)                |
| **structlog**             | Structured logging for better observability                   | [https://www.structlog.org/](https://www.structlog.org/)                            |
| **gen_ai_hub** (optional) | SAP AI Core integration for enterprise AI deployments        | SAP AI Core users only                                                               |

---

## 8. Running the application

### 8.1  Quick start

After setting up your environment variables and database:

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Run the main discovery workflow
python main.py
```

The application will:
1. Connect to the GitHub organization specified in `GITHUB_ORG`
2. Fetch all non-archived repositories
3. Analyze each repository using AI agents to:
   - Classify the repository type (e.g., service, library, infrastructure)
   - Discover services and their metadata
   - Extract technology stack information
4. Store results in the configured database

### 8.2  Using Docker Compose for database

Start the PostgreSQL database locally:

```bash
docker-compose up -d database
export DATABASE_URL="postgresql://sbs-ai-discovery-user:sbs-ai-discovery-password@localhost:5433/sbs-ai-discovery-db"
```

### 8.3  Sample usage with custom repository

You can also analyze specific repositories by modifying the workflow in your code:

```python
from src.dto.state_dto import RootRepoState
from src.workflows.repo_type_workflow import generate_repo_type_workflow

# Analyze a specific repository
initial_state = RootRepoState(repo_root_url="https://github.com/your-org/your-repo")
workflow = generate_repo_type_workflow()
result = workflow.invoke(initial_state, config={})
print(result)
```

---

## 9. LangGraph glossary

| Term                 | What it means in practice                                                                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **State**            | A (typed) `dict`/`TypedDict` that holds all data flowing through the graph. Each node receives it, mutates or extends it, then passes it on.                              |
| **Node**             | A `@langgraph.node`‑decorated function (or any LangChain **Runnable**) that takes the current state and returns an updated state – a single processing step.              |
| **Graph**            | The orchestration object built with `langgraph.Graph()`. You register nodes and connect them with edges, then `graph.compile()` it into an executable workflow.           |
| **Edge**             | A directed connection between two nodes that dictates execution order.                                                                                                    |
| **Conditional edge** | An edge whose *target* is chosen at runtime based on a predicate over the state – created with `graph.add_conditional_edges(...)`.                                        |
| **Tool**             | A side‑effectful helper (API call, DB query, …) wrapped in LangChain’s `@tool` decorator so it can be invoked by an LLM.                                                  |
| **Tools node**       | A ready‑made node (`langgraph.nodes.tools`) that exposes one or more **tools** to the LLM and writes the result back into the state.                                      |
| **State graph**      | The compiled graph object – the “blueprint” that owns every node & edge and knows the shape of the state. It can be invoked many times with different inputs.             |
| **Runnable**         | LangChain’s generic interface for *something executable*. Every node **and** the compiled graph itself are `Runnable`s; a bare Runnable need not manage state on its own. |

---

## 10. Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository** and create a new branch for your feature or bug fix
2. **Make your changes** following the code style guidelines (use `uv run ruff check --fix` and `uv run mypy`)
3. **Test your changes** thoroughly
4. **Submit a pull request** with a clear description of your changes

Please ensure your code:
- Follows PEP 8 style guidelines
- Includes type hints for better code quality
- Has appropriate error handling
- Is well-documented with docstrings

---

## 11. License

[Add your license information here - e.g., MIT, Apache 2.0, etc.]

---

## 12. Support and Community

- **Issues**: Report bugs or request features via [GitHub Issues](../../issues)
- **Discussions**: Join conversations in [GitHub Discussions](../../discussions)
- **Documentation**: Check the docs in the `docs/` folder for more detailed information

---

## 13. Acknowledgments

Built with:
- [LangChain](https://www.langchain.com/) - Framework for developing applications with LLMs
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Library for building stateful AI agents
- [PyGithub](https://github.com/PyGithub/PyGithub) - Python library for GitHub API

---

## 14. How It Works

The AI-based discovery system uses a multi-agent workflow built on LangGraph to analyze GitHub repositories:

### Discovery Pipeline

1. **Repository Fetching**: Connects to GitHub API and retrieves repositories from the specified organization
2. **AI Analysis**: Each repository is analyzed using LLM-powered agents that:
   - Examine repository structure and files
   - Classify the repository type (service, library, infrastructure, etc.)
   - Identify technology stack and frameworks
   - Discover services and their metadata
3. **Data Storage**: Results are persisted to the database for querying and reporting
4. **Workflow Orchestration**: LangGraph manages the state and flow between different analysis steps

### Key Components

- **Workflows**: High-level orchestration of analysis tasks (see `src/workflows/`)
- **Nodes**: Individual processing steps in the workflow (see `src/nodes/`)
- **Tools**: External integrations like GitHub API (see `src/tools/`)
- **AI Provider**: Abstraction layer supporting multiple LLM providers (see `src/ai_provider/`)

### Extensibility

The modular architecture makes it easy to:
- Add new LLM providers by implementing provider-specific initialization
- Create custom analysis workflows by composing existing nodes
- Extend repository analysis with new tools and prompts
- Support additional data stores beyond PostgreSQL/SQLite

