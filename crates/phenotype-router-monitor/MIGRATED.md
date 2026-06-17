# Migration: phenotype-router-monitor → canonical owner

**Date:** 2026-06-17  
**Disposition:** Agentora PhenoProc audit copy — **not canonical**  
**Canonical:** https://github.com/KooshaPari/phenotype-tooling  
**Authority:** `PHENOTYPE_HEXAKIT_REPOINT.md` wave 3

## For consumers

Do not depend on this Agentora staging path. Use:

```toml
`phenotype-router-monitor` = { git = "https://github.com/KooshaPari/phenotype-tooling", branch = "main" }
```

## For Agentora maintainers

- Do not register `phenotype-router-monitor` as a workspace member.
- Remove this stub when zero path deps remain.
