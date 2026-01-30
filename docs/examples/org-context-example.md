# ACME Corp Discovery Context

This file provides organization-wide context for AI discovery.
Location: `~/.sbs-discovery/acme-corp.md`

## Service Naming

All services follow the pattern: `acme-{team}-{service}`

Teams and their prefixes:
- `platform-*` — Platform Engineering (auth, infra, tooling)
- `payments-*` — Payments Team (billing, subscriptions, invoicing)
- `users-*` — User Services (profiles, preferences, notifications)
- `orders-*` — Order Management (cart, checkout, fulfillment)

## Tech Stack

### Backend
- **Primary**: Python 3.11+ with FastAPI
- **High-performance**: Go 1.21+ for latency-critical services
- **Legacy**: Some older services use Flask (being migrated)

### Frontend
- React 18 with TypeScript
- Next.js for SSR applications
- Tailwind CSS for styling

### Databases
- **Primary**: PostgreSQL 15
- **Cache**: Redis 7
- **Search**: Elasticsearch 8

### Messaging
- Apache Kafka for event streaming
- RabbitMQ for task queues (legacy, being migrated to Kafka)

## Deployment

### Container Strategy
- All deployable services have `Dockerfile` in repository root
- Multi-stage builds required for production images
- Base images from internal registry: `acme-registry.io/base/*`

### Kubernetes
- Manifests stored in `/k8s` directory
- Helm charts in `/charts` for complex services
- All services deploy to `acme-{env}` namespaces

### CI/CD
- GitHub Actions for all pipelines
- Workflow files in `.github/workflows/`
- Required workflows: `lint.yml`, `test.yml`, `build.yml`

## Team Ownership

| Prefix | Team | Slack Channel |
|--------|------|---------------|
| `platform-*` | Platform Engineering | #platform-eng |
| `payments-*` | Payments | #payments-team |
| `users-*` | User Services | #user-services |
| `orders-*` | Order Management | #orders |
| `infra-*` | Infrastructure | #infra |
| `shared-*` | Shared Libraries | #platform-eng |

## Special Patterns

### Monorepos
- `acme-platform-monorepo` contains multiple services in `/services/*`
- Each subdirectory is a separate deployable unit

### Shared Libraries
- Repositories ending with `-lib` or `-common` are libraries, not services
- Published to internal PyPI/npm registries

### Internal Tools
- Repositories starting with `internal-` are developer tools
- Not deployed to production, run locally or in CI
