# Repository Discovery Context

This file provides repository-specific context for AI discovery.
Location: `.sbs-discovery.md` in the repository root.

---

## About This Repository

This is the main user authentication service for ACME Corp. It handles all user identity operations including login, registration, password management, and OAuth integrations.

## Service Details

| Field | Value |
|-------|-------|
| **Service Name** | acme-platform-auth |
| **Type** | Microservice |
| **Team** | Platform Engineering |
| **On-call** | #platform-eng-oncall |

## Architecture Notes

### Endpoints
- **REST API**: `/api/v1/*` — Public-facing authentication endpoints
- **gRPC**: Port 50051 — Internal service-to-service communication
- **Health**: `/health` and `/ready` for Kubernetes probes

### External Integrations
- **Keycloak**: Used as identity provider via OIDC
- **SendGrid**: Email verification and password reset
- **Twilio**: SMS-based 2FA

## Directory Structure Notes

These clarifications help the AI understand non-obvious patterns:

| Directory | Purpose | Deployable? |
|-----------|---------|-------------|
| `/src/api` | REST API handlers | Part of main service |
| `/src/grpc` | gRPC service definitions | Part of main service |
| `/internal/` | Shared internal libraries | **No** — not a separate service |
| `/scripts/` | Development and migration scripts | **No** — not deployed |
| `/k8s/` | Kubernetes manifests | Deployment config only |

## Tech Stack Overrides

This service uses some technologies different from the org standard:

- **Database**: Uses both PostgreSQL (users) and Redis (sessions)
- **Framework**: Custom auth framework built on FastAPI
- **Additional**: JWT tokens with RS256 signing

## Testing Notes

- Integration tests require running Keycloak instance
- Use `docker-compose -f docker-compose.test.yml up` for test dependencies
- E2E tests in `/tests/e2e/` hit the actual OAuth flow
