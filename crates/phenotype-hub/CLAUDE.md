# CLAUDE.md - Development Guidelines for phenotype-hub

## Project Overview

Next.js 15 monorepo with 3D visualization capabilities using React Three Fiber and Three.js.

## Key Directories

- `apps/web/` - Next.js application entry point
- `packages/ui/src/` - Shared React components (Button, Card, Badge)
- `apps/web/app/` - Next.js App Router pages

## Development Commands

```bash
# Start dev server
npm run dev

# Build
npm run build

# Type check
npm run typecheck
```

## Architecture Principles

- **Monorepo**: Turborepo with workspace protocol
- **3D First**: React Three Fiber for WebGL rendering
- **Component Library**: Shared UI in packages/ui
- **Type Safety**: Full TypeScript coverage

## Phenotype Org Rules

- UTF-8 encoding only
- Worktree discipline: canonical repo stays on `main`
- CI completeness: verify builds pass before merging
- Never commit agent directories (`.claude/`, etc.)
