# Task-Specific Workflows

## Adding a New LangGraph Agent Node

An agent node uses an LLM to process state. Steps:

1. Create `src/nodes/agents/my_agent.py`
2. Use this function signature — agents always receive `config`:
   ```python
   def my_agent(state: RootRepoState, config: RunnableConfig) -> RootRepoState:
   ```
3. Initialize the LLM:
   ```python
   model_name = config.get("configurable", {}).get("model_name")
   llm = init_llm_by_provider(model_name)
   ```
4. Build the chain using **PromptTemplate + JsonOutputParser** (preferred) or **ReAct with tools** (when tool use is needed). See `key-patterns.md` for both patterns.
5. Mutate `state` with results and return it.
6. Register the node in `src/workflows/repo_type_workflow.py`:
   ```python
   graph.add_node("my_agent", my_agent)
   ```
7. Connect it with edges:
   ```python
   graph.add_edge("previous_node", "my_agent")
   graph.add_edge("my_agent", "next_node")
   ```

## Adding a New Runnable Node

A runnable node performs non-LLM processing. Steps:

1. Create `src/nodes/runnables/my_runnable.py`
2. Use this function signature — runnables do **not** receive `config`:
   ```python
   def my_runnable(state: RootRepoState) -> RootRepoState:
   ```
3. Implement the logic, mutate `state`, and return it.
4. Register and connect in `src/workflows/repo_type_workflow.py` (same as agents).

## Adding a New CLI Command

1. Create `src/cli/my_command.py`
2. Define the command using Click decorators:
   ```python
   @click.command()
   @click.option("--my-option", help="Description")
   def my_command(my_option: str) -> None:
       """Command description for --help."""
       # Use Rich for terminal output
   ```
3. Register in `src/cli/main.py`:
   ```python
   from src.cli.my_command import my_command
   cli.add_command(my_command)
   ```

## Adding a New LLM Provider

1. Edit `src/ai_provider/ai_provider.py`
2. Add a private init function:
   ```python
   def _init_my_provider_llm(model_name: str) -> Any:
       return MyProviderChat(model=model_name, ...)
   ```
3. Add an env var detection block in `init_llm_by_provider()`, following the existing priority chain:
   ```python
   if os.getenv("MY_PROVIDER_KEY"):
       model = model_name or "default-model"
       return _init_my_provider_llm(model)
   ```
4. Add the dependency to `pyproject.toml` under `[project.dependencies]`.

## Adding a New Evaluation Function

1. Edit `src/evals/output_scoring_eval.py`
2. Follow existing signature patterns — evals compare predicted state against gold standard:
   ```python
   def my_evaluation(pred: RootRepoState, gold: GoldExpectedOutput) -> float:
       """Return a score between 0.0 and 1.0."""
   ```
   For boolean evaluations:
   ```python
   def my_evaluation_boolean(pred: RootRepoState, gold: GoldExpectedOutput) -> bool:
   ```
3. Use helpers like `names_from_state()` and `names_from_gold()` for set-based comparisons.
