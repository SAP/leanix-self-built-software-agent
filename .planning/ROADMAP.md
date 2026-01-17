# Roadmap: sbs-ai-discovery User Context System

## Overview

Enhance the AI discovery tool to accept user-provided context via markdown files. This context flows to LLM agents to improve service/tech stack detection accuracy. The system supports organization-level defaults (local config) with per-repository overrides, enabling teams to codify their domain knowledge.

## Domain Expertise

None — Python/LangChain patterns established in codebase.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Context Model** - Define data structures and state extensions for user context
- [x] **Phase 2: Context Discovery** - Implement file detection from local config and repositories
- [x] **Phase 3: Agent Integration** - Pass context to LLM agents for enhanced reasoning
- [x] **Phase 4: CLI Integration** - Add CLI options and command support
- [ ] **Phase 5: Testing & Documentation** - Add tests and document the feature

## Phase Details

### Phase 1: Context Model ✓
**Goal**: Define data structures for user-provided context and extend workflow state
**Depends on**: Nothing (first phase)
**Research**: Unlikely (internal dataclass patterns)
**Plans**: 1/1 complete

Key deliverables:
- Context dataclass with fields for different context types
- Extend `RootRepoState` to carry context through workflow
- Context merge logic (org + repo inheritance)

### Phase 2: Context Discovery ✓
**Goal**: Implement automatic discovery of context files from local config and repositories
**Depends on**: Phase 1
**Research**: Unlikely (file system operations)
**Plans**: 1/1 complete

Key deliverables:
- Local org config discovery: `~/.sbs-discovery/{org}.md`
- Repo context discovery: `.sbs-discovery.md` in repo root
- Context loader with merge/inheritance behavior
- CLI flag overrides: `--org-context`, `--repo-context`

### Phase 3: Agent Integration ✓
**Goal**: Pass user context to relevant LLM agents to enhance discovery accuracy
**Depends on**: Phase 2
**Research**: Unlikely (existing LangChain prompt patterns)
**Plans**: 1/1 complete

Key deliverables:
- Update agent prompts to include user context section
- Integrate with: repo type agent, tech stack agent, SBS name discovery
- Token usage awareness (don't bloat prompts)
- Context formatting for LLM consumption

### Phase 4: CLI Integration ✓
**Goal**: Expose context system through CLI commands and options
**Depends on**: Phase 3
**Research**: Unlikely (Click patterns established)
**Plans**: 2/2 complete

Key deliverables:
- Add `--org-context` and `--repo-context` flags to discover command
- Context validation and error messages
- Display loaded context info in verbose mode
- Support for context file initialization helper

### Phase 5: Testing & Documentation
**Goal**: Ensure quality and document the feature for users
**Depends on**: Phase 4
**Research**: Unlikely (pytest patterns)
**Plans**: TBD

Key deliverables:
- Unit tests for context model and merge logic
- Integration tests for context discovery
- Update README with context file format and usage
- Example context files for common scenarios

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Context Model | 1/1 | Complete | 2026-01-17 |
| 2. Context Discovery | 1/1 | Complete | 2026-01-17 |
| 3. Agent Integration | 1/1 | Complete | 2026-01-17 |
| 4. CLI Integration | 2/2 | Complete | 2026-01-17 |
| 5. Testing & Documentation | 2/3 | In progress | - |

---

*Created: 2026-01-17*
