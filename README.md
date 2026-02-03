![](docs/capture.gif)

[![REUSE status](https://api.reuse.software/badge/github.com/SAP/leanix-self-built-software-agent)](https://api.reuse.software/info/github.com/SAP/leanix-self-built-software-agent)

# SAP LeanIX Self Built Software Agent

## About this project

A CLI tool and library for automated discovery and analysis of self-built software in GitHub repositories using AI agents. Identifies services, dependencies, technology stacks, and runtime details without human intervention.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
  - [Recommended](#recommended)
  - [Homebrew](#homebrew)
  - [Python Version](#python-version)
- [Getting Started](#getting-started)
  - [Configuration](#configuration)
    - [Required Variables](#required-variables)
  - [Discover Repositories](#discover-repositories)
  - [User-Provided Context](#user-provided-context)
    - [How It Works](#how-it-works)
    - [Example Usage](#example-usage)
    - [What to Include in Context Files](#what-to-include-in-context-files)
    - [Quick Start](#quick-start)
  - [Sync Command](#sync-command)
  - [Output Formats](#output-formats)
  - [Supported LLM Models](#supported-llm-models)
- [Database Setup](#database-setup)
  - [SQLite (Quick Start)](#sqlite-quick-start)
  - [PostgreSQL (Production)](#postgresql-production)

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
git clone https://github.com/SAP/leanix-self-built-software-agent.git
cd leanix-self-built-software-agent
uv venv && uv sync
source .venv/bin/activate
```

### Homebrew

```bash
# Install uv
brew install uv

# Clone and setup
git clone https://github.com/SAP/leanix-self-built-software-agent.git
cd leanix-self-built-software-agent
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

**Anthropic (Custom Hosting):**
```bash
export ANTHROPIC_BASE_URL="https://your-custom-anthropic-endpoint.com"
export ANTHROPIC_AUTH_TOKEN="your-auth-token"
```
Uses `x-api-key` header for authentication.

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

### User-Provided Context

Improve discovery accuracy by providing domain-specific context that the AI agents use during analysis. Context files help the AI understand your organization's naming conventions, tech stack choices, and team ownership patterns.

#### How It Works

The tool automatically looks for context files in two locations:

| Scope            | Location                         | Purpose                          |
| ---------------- | -------------------------------- | -------------------------------- |
| **Organization** | `~/.sbs-discovery/{org}.md`      | Shared patterns across all repos |
| **Repository**   | `.sbs-discovery.md` in repo root | Repo-specific overrides          |

When both exist, repository context extends and overrides organization context.

#### Example Usage

```bash
# Auto-detect context files from standard locations
sbs-ai-discovery discover --org myorg

# Override organization context with a custom file
sbs-ai-discovery discover --org myorg --org-context ./custom-org-context.md

# Override repository context
sbs-ai-discovery discover --repo owner/repo --repo-context ./my-context.md

# Both overrides together
sbs-ai-discovery discover --org myorg \
  --org-context ./org.md \
  --repo-context ./repo.md
```

#### What to Include in Context Files

Focus on patterns the AI can't easily detect from code alone:

- **Service Naming**: Your `{team}-{service}` naming patterns
- **Tech Stack Hints**: Preferred frameworks, databases, infrastructure
- **Team Ownership**: Which prefixes belong to which teams
- **Deployment Indicators**: CI/CD patterns, container configurations
- **Special Cases**: Monorepos, shared libraries, internal tools

#### Quick Start

Create an organization context file:

```bash
mkdir -p ~/.sbs-discovery
cat > ~/.sbs-discovery/myorg.md << 'EOF'
# MyOrg Discovery Context

## Service Naming
- Services follow pattern: `{team}-{service}-{type}`
- Teams: platform, payments, users

## Tech Stack
- Backend: Python FastAPI, Go
- Frontend: React TypeScript
- Database: PostgreSQL, Redis
EOF
```

For detailed format documentation and examples, see [docs/CONTEXT_FILES.md](docs/CONTEXT_FILES.md).

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
## Support, Feedback, Contributing

This project is open to feature requests/suggestions, bug reports etc. via [GitHub issues](https://github.com/SAP/leanix-self-built-software-agent/issues). Contribution and feedback are encouraged and always welcome. For more information about how to contribute, the project structure, as well as additional contribution information, see our [Contribution Guidelines](CONTRIBUTING.md).

## Security / Disclosure
If you find any bug that may be a security problem, please follow our instructions at [in our security policy](https://github.com/SAP/leanix-self-built-software-agent/security/policy) on how to report it. Please do not create GitHub issues for security-related doubts or problems.

## Code of Conduct

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone. By participating in this project, you agree to abide by its [Code of Conduct](https://github.com/SAP/.github/blob/main/CODE_OF_CONDUCT.md) at all times.

## Licensing

Copyright 2026 SAP SE or an SAP affiliate company and leanix-self-built-software-agent contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/leanix-self-built-software-agent).
