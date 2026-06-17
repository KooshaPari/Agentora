# CONTRIBUTING.md - Contributing to phenotype-hub

## Getting Started

1. Clone the repository
2. Install dependencies: `npm install`
3. Start development: `npm run dev`

## Development Workflow

### Adding a New Component

1. Create in `packages/ui/src/`
2. Export from `packages/ui/src/index.ts`
3. Use in `apps/web/`

### 3D Scene Development

1. Add Three.js components in `apps/web/components/`
2. Use React Three Fiber hooks
3. Test performance with Chrome DevTools

### Code Standards

- TypeScript strict mode
- Functional components
- Tailwind for styling
- `cn()` utility for class merging

## Testing

```bash
# Type check
npm run typecheck

# Build test
npm run build
```

## Submitting Changes

1. Create feature branch
2. Make changes
3. Test in dev and production modes
4. Submit PR

## License

MIT
