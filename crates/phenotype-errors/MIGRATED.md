# Migration: phenotype-errors → canonical owner

**Date:** 2026-06-18  
**Disposition:** Agentora PhenoProc audit copy — **not canonical**  
**Canonical:** https://github.com/KooshaPari/phenotype-types  
**Authority:** `PHENOTYPE_HEXAKIT_REPOINT.md` wave 1 (W18b repoint)

## For consumers

Do not depend on this Agentora staging path. Use:

```toml
phenotype-errors = { git = "https://github.com/KooshaPari/phenotype-types", branch = "main" }
```

## For Agentora maintainers

- Do not register `phenotype-errors` as a workspace member.
- Remove this stub when zero path deps remain.
