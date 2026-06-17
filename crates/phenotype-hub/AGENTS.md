# AGENTS.md - Agent Guidelines for phenotype-hub

## Project Identity

- **Name**: phenotype-hub
- **Type**: Next.js Monorepo with 3D Visualization
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-hub`
- **Stack**: React 19, Next.js 15, Three.js, Tailwind CSS

## Development Workflow

### Commands

```bash
# Install dependencies
npm install

# Start development server (runs on port 3002)
npm run dev

# Build for production
npm run build

# Type checking
npm run typecheck

# Linting
npm run lint
```

### Workspace Structure

- `apps/web` - Next.js application
- `packages/ui` - Shared UI components
- Uses Turborepo for task orchestration

## Code Standards

- **TypeScript**: Strict mode enabled
- **Components**: Functional components with hooks
- **Styling**: Tailwind CSS utility classes
- **3D**: React Three Fiber patterns

## Phenotype Org Rules

- UTF-8 encoding in all files
- Monorepo discipline: shared packages in `packages/`, apps in `apps/`
- Test in both dev and production builds before committing
