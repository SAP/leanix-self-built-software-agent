# Context Files Reference

This document explains how to create and use context files to improve AI discovery accuracy.

## Purpose

Context files provide domain-specific knowledge that helps the AI agents make better decisions during repository analysis. While the AI can detect many patterns from code, it can't know:

- Your organization's naming conventions
- Which team owns which repositories
- Whether a directory is a separate service or shared code
- Your preferred tech stack and frameworks
- Special deployment patterns

By providing this context, you get more accurate service discovery and classification.

## File Format

Context files are **plain Markdown**. There's no special syntax or schema — write what you'd tell a new team member about your codebase.

The AI reads the entire file and extracts relevant information during analysis.

### Recommended Sections

These sections are optional but helpful:

| Section | Purpose | Example Content |
|---------|---------|-----------------|
| **Service Naming** | Naming patterns and conventions | `{team}-{service}-{type}` |
| **Tech Stack** | Languages, frameworks, databases | Python/FastAPI, PostgreSQL |
| **Deployment** | CI/CD, containers, cloud patterns | GitHub Actions, Kubernetes |
| **Team Ownership** | Org structure and ownership rules | `platform-*` → Platform Team |
| **Special Notes** | Repository-specific clarifications | "internal/ is not a service" |

### Example Structure

```markdown
# MyOrg Discovery Context

## Service Naming
- Pattern: `{team}-{service}`
- Teams: platform, payments, users

## Tech Stack
- Backend: Python FastAPI
- Database: PostgreSQL
- Cache: Redis

## Deployment
- All services have Dockerfile in root
- Kubernetes manifests in /k8s

## Team Ownership
- platform-* repos owned by Platform Team
- payments-* repos owned by Payments Team
```

## File Locations

### Organization Context

Stored locally on your machine:

```
~/.sbs-discovery/{org}.md
```

The `{org}` matches the GitHub organization name. For example:
- GitHub org `acme-corp` → `~/.sbs-discovery/acme-corp.md`
- GitHub org `my-company` → `~/.sbs-discovery/my-company.md`

### Repository Context

Stored in the repository root:

```
.sbs-discovery.md
```

This file can be committed to the repository so all team members benefit from it.

## Inheritance Model

When both organization and repository context exist, they are merged:

1. **Organization context** is loaded first (base layer)
2. **Repository context** is appended after (overrides/extends)

The AI sees both contexts together, with repository-specific information taking precedence due to recency in the prompt.

### Example Merge

**Organization context** (`~/.sbs-discovery/acme.md`):
```markdown
## Tech Stack
- Backend: Python FastAPI
- Database: PostgreSQL
```

**Repository context** (`.sbs-discovery.md`):
```markdown
## Tech Stack Override
This service uses Go instead of Python for performance reasons.
```

**Result**: The AI knows the org default is Python/FastAPI but this specific repo uses Go.

## CLI Overrides

Override the automatic file detection with CLI flags:

```bash
# Override organization context
sbs-ai-discovery discover --org myorg --org-context ./custom-org.md

# Override repository context
sbs-ai-discovery discover --repo owner/repo --repo-context ./custom-repo.md

# Both overrides
sbs-ai-discovery discover --org myorg \
  --org-context ./org.md \
  --repo-context ./repo.md
```

When using `--org-context` or `--repo-context`:
- The specified file is used instead of the default location
- The file must exist (error if not found)
- Path is marked as `<cli-override>` in verbose output

## Best Practices

### Do

- **Keep it concise**: Under 4000 characters recommended (~1000 tokens)
- **Focus on non-obvious patterns**: Things the AI can't detect from code
- **Update when conventions change**: Stale context is worse than none
- **Commit repo context**: Share `.sbs-discovery.md` with your team
- **Use clear headings**: Makes the file scannable for both humans and AI

### Don't

- **Don't repeat obvious information**: The AI can see your package.json
- **Don't include secrets**: Context files may be committed/shared
- **Don't over-specify**: Let the AI infer what it can
- **Don't use complex formatting**: Simple markdown works best

## Size Guidelines

| Size | Recommendation |
|------|----------------|
| < 1000 chars | Good — focused and efficient |
| 1000-4000 chars | Acceptable — comprehensive |
| > 4000 chars | Consider trimming — may affect token budget |

Context is truncated at 4000 characters to prevent prompt bloat.

## Troubleshooting

### Context not being loaded

1. Check file location matches expected path
2. Verify file has `.md` extension
3. Use `--verbose` flag to see loaded context paths
4. Check for typos in organization name

### Context not affecting results

1. Ensure content is relevant to discovery (naming, tech stack, ownership)
2. Check that context isn't being overridden by repository context
3. Try being more explicit about patterns

### File too large warning

If your context exceeds 4000 characters:
1. Remove redundant information
2. Focus on patterns the AI can't detect
3. Split into org-level (shared) and repo-level (specific)

## Examples

See the `docs/examples/` directory for complete examples:

- [`org-context-example.md`](examples/org-context-example.md) — Organization-level context
- [`repo-context-example.md`](examples/repo-context-example.md) — Repository-level context
