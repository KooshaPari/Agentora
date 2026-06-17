# Migration: phenotype-colab-extensions → canonical owner

**Date:** 2026-06-17  
**Disposition:** Agentora PhenoProc audit copy — **not canonical**  
**Canonical:** https://github.com/KooshaPari/HexaKit  
**Authority:** `PHENOTYPE_HEXAKIT_REPOINT.md` wave 3

## For consumers

Do not depend on this Agentora staging path. Use:

```toml
`phenotype-colab-extensions` = { git = "https://github.com/KooshaPari/HexaKit", branch = "main" }
```

## For Agentora maintainers

- Do not register `phenotype-colab-extensions` as a workspace member.
- Remove this stub when zero path deps remain.
