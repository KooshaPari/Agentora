# Migration: phenotype-config-loader → canonical owner

**Date:** 2026-06-18  
**Disposition:** Agentora PhenoProc audit copy — **not canonical**  
**Canonical:** https://github.com/KooshaPari/phenotype-config  
**Authority:** `PHENOTYPE_HEXAKIT_REPOINT.md` wave 1 (W18b repoint)

## For consumers

Do not depend on this Agentora staging path. Use:

```toml
phenotype-config-loader = { git = "https://github.com/KooshaPari/phenotype-config", branch = "main" }
```

## For Agentora maintainers

- Do not register `phenotype-config-loader` as a workspace member.
- Remove this stub when zero path deps remain.
