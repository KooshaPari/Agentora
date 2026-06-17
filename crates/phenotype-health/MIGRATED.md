# Migration: phenotype-health → canonical owner

**Date:** 2026-06-17  
**Disposition:** Agentora PhenoProc audit copy — **not canonical**  
**Canonical:** https://github.com/KooshaPari/HexaKit  
**Authority:** `PHENOTYPE_HEXAKIT_REPOINT.md` wave 3

## For consumers

Do not depend on this Agentora staging path. Use:

```toml
`phenotype-health` = { git = "https://github.com/KooshaPari/HexaKit", branch = "main" }
```

## For Agentora maintainers

- Do not register `phenotype-health` as a workspace member.
- Remove this stub when zero path deps remain.
