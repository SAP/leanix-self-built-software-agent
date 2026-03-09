# Contributing Rules

- All contributions must be licensed under Apache 2.0.
- Create a GitHub issue before implementing changes; wait for team approval before opening a PR.
- Contributors must accept the Developer Certificate of Origin (DCO) on their first PR.
- Follow [SAP's guidelines on AI-generated code](https://github.com/SAP/.github/blob/main/CONTRIBUTING_USING_GENAI.md) when contributing code produced by generative AI tools.

## Code Ownership

All files are owned by `@SAP/leanix-self-built-software-agent-team` (see `CODEOWNERS`).

## PR Checklist

Before opening a pull request, verify:

- [ ] Tests pass: `uv run pytest`
- [ ] Linter passes: `uv run ruff check .`
- [ ] Code formatted: `uv run ruff format .`
- [ ] Type checks pass: `uv run mypy .`
- [ ] New dependencies added to `pyproject.toml` under `[project.dependencies]` or `[dependency-groups.dev]`
- [ ] New CLI commands registered in `src/cli/main.py` via `cli.add_command()`
- [ ] New workflow nodes registered in `src/workflows/repo_type_workflow.py` with `graph.add_node()` and connected via `graph.add_edge()` or `graph.add_conditional_edges()`
