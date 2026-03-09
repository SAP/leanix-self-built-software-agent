# Code Style & Conventions

## Data Modeling

- **Dataclasses** with `@dataclass(slots=True)` for all state/data objects (see `src/dto/`)
- **Pydantic `BaseModel`** only for structured LLM output schemas (used with `JsonOutputParser`)
- **Enums** use the `str + Enum` pattern for JSON serialization:
  ```python
  class RepoType(str, Enum):
      MONO_REPO = "mono-repo"
  ```
- Central workflow state is `RootRepoState` in `src/dto/state_dto.py`

## LLM Agent Patterns

All agents live in `src/nodes/agents/`. Two patterns exist:

**Pattern 1 — PromptTemplate + JsonOutputParser chain** (preferred for new agents):
```python
def my_agent(state: RootRepoState, config: RunnableConfig) -> RootRepoState:
    model_name = config.get("configurable", {}).get("model_name")
    llm = init_llm_by_provider(model_name)
    parser = JsonOutputParser(pydantic_object=MyOutputSchema)
    prompt = PromptTemplate(
        input_variables=["my_input"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
        template="...",
    )
    chain = prompt | llm | parser
    result = chain.invoke({"my_input": "..."})
    # mutate state, return state
```

**Pattern 2 — ReAct agent with tools** (for agents needing tool use):
```python
def my_agent(state: RootRepoState, config: RunnableConfig) -> RootRepoState:
    llm = init_llm_by_provider(model_name)
    react_prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(tools=tools, llm=llm, prompt=react_prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True,
                             handle_parsing_errors=True, max_iterations=3)
    response = executor.invoke({"input": prompt}, return_only_outputs=True)
```

Key: agent functions always take `(state: RootRepoState, config: RunnableConfig)` and return `RootRepoState`.

## Runnable Node Pattern

Runnables in `src/nodes/runnables/` are non-LLM pipeline steps. They take only `state` (no `config`):
```python
def my_runnable(state: RootRepoState) -> RootRepoState:
```

## CLI Conventions

- CLI uses Click with `@click.group()` in `src/cli/main.py`
- Commands registered via `cli.add_command(command_fn, name="...")` at module level
- Rich used for terminal output (tables, panels, progress bars)
- Version read from package metadata: `importlib.metadata.version('ai-based-discovery')`

## Logging

- Use `structlog` throughout: `logger = structlog.get_logger()`
- No `print()` statements — use `logger.info()`, `logger.debug()`, etc.
- `DEFAULT_IS_LOCAL` env var controls log format (pretty for local, JSON for production)

## Context Injection

- User context loaded from `~/.sbs-discovery/{org}.md` (org-level) and `.sbs-discovery.md` (repo root)
- Context merged in `src/dto/context_dto.py:merge_contexts()` and stored in `state.discovery_context`
- Format for prompt injection via `src/utils/context_injection.py:format_context_for_prompt()`
- Max 4000 chars (approx 1000 tokens), auto-truncated with marker

## Configuration

- Environment variables loaded from `.env` file (via `dotenv`)
- Key env vars: `GITHUB_TOKEN`, `DATABASE_URL`, `DEFAULT_IS_LOCAL`, `LLM_DEPLOYMENT`
- Provider-specific env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`, `AICORE_CLIENT_ID`, `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `OPENAI_API_VERSION`
- Config module: `src/config/config.py`
- Ruff and mypy use default configurations from `pyproject.toml`
