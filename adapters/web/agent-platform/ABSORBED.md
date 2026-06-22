# agent-platform absorbed (FR-COLLECTION-2026-06, 2026-06-21)

TypeScript agent runtime port (`@opentelemetry/api`, T66 modality coordination)
from `KooshaPari/agent-platform` moved into `adapters/web/agent-platform/`
as a secondary adapter. Lives outside the `cargo` workspace (TS, not Rust).

Source repo archived/deleted; verified no remaining downstream Cargo deps
reference `KooshaPari/agent-platform`.

Build (standalone):

```bash
cd adapters/web/agent-platform
pnpm install
pnpm test
```
