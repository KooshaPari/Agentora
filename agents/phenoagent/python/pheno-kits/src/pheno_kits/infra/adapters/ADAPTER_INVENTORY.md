Adapter Inventory
=================

Purpose: map every infrastructure adapter we ship today, highlight gaps, and stage a roadmap that covers metaphoric primitive levels from 0.01 (bare metal) to 0.99 (fully managed plug-and-play).

1. Existing Adapters
--------------------

| Adapter | Module | Primitive Level | Primary Scope & Responsibilities | Config Highlights | Strengths | Current Gaps |
|---------|--------|-----------------|----------------------------------|-------------------|-----------|--------------|
| `DockerAdapter` | `docker.py` | 0.40 | Lifecycle for Docker containers (create, start, restart, remove, health) | `image`, `ports`, `environment`, `volumes`, `network`, restart policy, health config | Battle-tested local + remote container story, good health integration | Only single-container flows, no compose/stack orchestration, assumes Docker CLI |
| `SystemDaemonAdapter` | `daemon.py` | 0.20 | Controls systemd/launchd services via native tooling | `service_name`, optional `daemon_type`, `use_sudo`, health config | Bridges OS-managed daemons with our async loop; autodetects manager | No Windows support; no templating for new service units; limited to start/stop/is-active |
| `CommandAdapter` | `command.py` | 0.15 | Run arbitrary CLI start/stop/status commands with optional backgrounding | `start_command`, `stop_command`, `status_command`, `health_check`, background toggle | Lowest common denominator for process orchestration; flexible health checks | No log/stream capture; no supervisor semantics (autorestart, backoff); env/injection missing |
| `APIAdapter` | `api.py` | 0.55 | Generic HTTP/REST control plane for remote services | `api_base_url`, auth block, endpoint/method/body overrides, health config | Abstracts many SaaS/control-plane APIs with aiohttp session management | Limited auth strategies (no OAuth/device); no async webhook/polling; assumes JSON |
| `NeonAdapter` | `cloud/neon.py` | 0.70 | Neon serverless Postgres lifecycle (SDK + CLI fallback) | `project_id`, `api_key`, `branch_name`, `compute_units`, SDK toggle | Rich metadata (connection strings), adaptive SDK/CLI usage | Hard-coded Neon API surface; no pooling of branches; minimal error translation |
| `SupabaseAdapter` | `cloud/supabase.py` | 0.75 | Supabase project pause/resume, status, metadata (SDK/CLI) | `project_id`, `access_token`, `use_sdk`, region, org, db password | Handles auth gracefully, stores connection strings | Missing project provisioning; no rate-limit/backoff logic; CLI path assumptions |
| `VercelAdapter` | `cloud/vercel.py` | 0.80 | Vercel deploy/promote/cancel with health on deployment URL | `access_token`, `project_name` or `deployment_id`, `target`, `auto_promote` | SDK/CLI fallback, metadata with URLs, health check integration | No build logs/alias mgmt; limited environment variable/secret injection; preview env gaps |
| `ResourceFactory` | `factory.py` | N/A | Type-to-adapter factory, includes lazy loading of cloud adapters | `type` discriminator (`docker`, `daemon`, `command`, `api`, `supabase`, `vercel`, `neon`) | Centralized creation, extensible, handles missing cloud deps | Manual mapping; no dynamic registry or validation; no support for adapter chaining |

2. Missing Adapters (Prioritized by Common Use Cases)
----------------------------------------------------

| Priority | Adapter Concept | Target Primitive Level | Rationale & Coverage Gap | Notes |
|----------|-----------------|------------------------|--------------------------|-------|
| P0 | `KubernetesAdapter` (per deployment/statefulset) | 0.45 | Most teams run workloads on k8s; need manifests apply/status/rollback, namespace scoping | Use `kubectl` CLI fallback + `kubernetes` Python SDK; tie into health via probes/events |
| P0 | `VMInstanceAdapter` (EC2/GCE/DigitalOcean) | 0.25 | Bare VM lifecycle (start/stop/resize) still fundamental | Provide provider abstraction with Terraform/lightweight SDK fallback |
| P1 | `ComposeAdapter` / `ContainerStackAdapter` | 0.50 | Multi-container stacks (docker-compose, podman) common for local dev | Wrap Compose CLI + support service-level health aggregation |
| P1 | `ServerlessAdapter` (Lambda/Cloud Functions) | 0.60 | Triggering deployments/invocations for FaaS; complements API adapter with packaging | Expose deploy + version alias mgmt; integrate with artifact builders |
| P1 | `DatabaseAdapter` (generic managed SQL/NoSQL) | 0.65 | RDS, Cloud SQL, Firestore; unify managed DB operations beyond Neon/Supabase | Adapter with schema migrations hooks, secret rotation |
| P2 | `CacheAdapter` (Redis/MemoryStore) | 0.35 | Cache provisioning + flush for dev/test flows | Could reuse Docker/local providers and managed APIs |
| P2 | `QueueAdapter` (SQS/PubSub/Kafka) | 0.55 | Messaging primitives for async workflows | Provide topic/queue creation and purge |
| P3 | `StaticHostingAdapter` (S3/Cloudflare Pages) | 0.65 | Bridges static asset deploys similar to Vercel but for storage-backed CDNs | Pairs with bundlers/build step |
| P3 | `SecretsAdapter` (Vault/SSM) | 0.30 | Manage secure secret stores, rotate credentials feeding other adapters | Enables cross-adapter secret provisioning |

3. Generification Opportunities
-------------------------------

- **Adapter Registry**: replace the manual if/elif ladder in `ResourceFactory` with a pluggable registry (`register_adapter(type, cls)`) so downstream kits can extend without editing core code.
- **Shared Health Strategies**: consolidate duplicated TCP/HTTP logic into mixins; expose declarative health config (`{"strategy": "tcp", "host": "...", "retries": 5}`) consumed uniformly across adapters, including cloud ones that currently short-circuit to `True`.
- **Credential Providers**: introduce a credential resolver (env, secrets adapter, interactive prompt) to avoid each adapter reading environment variables independently.
- **Lifecycle Hooks**: allow pre/post hooks (`before_start`, `after_stop`) to support migrations, schema prep, or log streaming without subclassing.
- **Error Normalization**: funnel SDK/CLI exceptions into typed errors (`AuthenticationError`, `NotFoundError`, `QuotaExceededError`) so callers can react programmatically.
- **Async Command Utilities**: extract subprocess management (background processes, output capture, timeouts) to utilities to reduce duplication across `CommandAdapter`, `SystemDaemonAdapter`, and forthcoming adapters.
- **Config Validation**: add pydantic-style schemas for adapter config to surface misconfigurations early and produce docstrings automatically.
- **Cross-Adapter Composition**: enable chaining (e.g., start secrets adapter → inject into docker env) through dependency graph metadata on `ResourceState`.

4. Primitive Level Coverage
---------------------------

- **Scale Definition**:
  - 0.01–0.19: Bare metal / OS primitives (process, daemon, VM startup).
  - 0.20–0.39: Local orchestration layers (system supervisors, container runtime).
  - 0.40–0.59: Cluster/control plane wrappers (compose, k8s, generic APIs).
  - 0.60–0.79: Managed services abstractions (serverless, managed DB/cache).
  - 0.80–0.99: Fully managed SaaS with deployment workflows (Vercel, Supabase UI-level ops).

- **Current Coverage**:
  - 0.15 `CommandAdapter`
  - 0.20 `SystemDaemonAdapter`
  - 0.40 `DockerAdapter`
  - 0.55 `APIAdapter`
  - 0.70 `NeonAdapter`
  - 0.75 `SupabaseAdapter`
  - 0.80 `VercelAdapter`

- **Gap Analysis**:
  - <0.10 (raw hardware/provisioning) missing → `VMInstanceAdapter`, `SecretsAdapter`.
  - 0.30–0.45 cluster orchestration missing → `ComposeAdapter`, `KubernetesAdapter`.
  - 0.60–0.70 breadth limited to databases → need `ServerlessAdapter`, `QueueAdapter`, `CacheAdapter`.
  - >0.85 plug-and-play SaaS (e.g., Shopify, Stripe, Notion) not yet covered; consider templated `SaaSAdapter` derived from API adapter with opinionated defaults.

5. Pre-built Configurations
---------------------------

```python
# Local Postgres for dev via DockerAdapter
resources = {
    "dev_db": {
        "type": "docker",
        "image": "postgres:16",
        "ports": {5432: 5432},
        "environment": {"POSTGRES_PASSWORD": "postgres"},
        "volumes": {"./data/postgres": "/var/lib/postgresql/data"},
        "health_check": {"type": "tcp", "port": 5432},
    }
}
```

```python
# Background Node service managed by CommandAdapter
resources = {
    "web_app": {
        "type": "command",
        "start_command": ["npm", "run", "start"],
        "stop_command": ["npm", "run", "stop"],
        "status_command": ["npm", "run", "status"],
        "run_in_background": True,
        "health_check": {"type": "http", "port": 3000, "path": "/healthz"},
    }
}
```

```python
# System daemon (systemd) for a Celery worker
resources = {
    "celery_worker": {
        "type": "daemon",
        "service_name": "celery-worker",
        "daemon_type": "systemd",
        "use_sudo": True,
        "health_check": {"type": "tcp", "port": 5555},
    }
}
```

```python
# Supabase production project toggle
resources = {
    "supabase_prod": {
        "type": "supabase",
        "project_id": "abc123",
        "access_token": "${SUPABASE_ACCESS_TOKEN}",
        "use_sdk": True,
    }
}
```

```python
# Vercel preview deployment rollout
resources = {
    "frontend_preview": {
        "type": "vercel",
        "project_name": "app-frontend",
        "access_token": "${VERCEL_TOKEN}",
        "target": "preview",
        "auto_promote": False,
    }
}
```

```python
# Remote control-plane resource via APIAdapter (generic)
resources = {
    "cloud_sql_proxy": {
        "type": "api",
        "api_base_url": "https://gcloud.example.com/sql/projects/my-project/instances/db",
        "auth": {"type": "bearer", "token": "${GCLOUD_TOKEN}"},
        "start_endpoint": "/start",
        "stop_endpoint": "/stop",
        "status_endpoint": "/status",
        "health_check": {"type": "http", "expected_status": 200, "poll_interval": 10.0},
    }
}
```

Next Steps
----------

- Ratify missing-adapter roadmap and slot into upcoming sprint(s).
- Design registry + config validation changes (`ResourceFactory` refactor).
- Stand up reference implementations for at least one P0 adapter (k8s or VM) to close lowest-level and mid-level gaps simultaneously.
