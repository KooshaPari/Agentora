# KInfra Authentication Integration

How to configure authentication middleware to work with KInfra monitoring routes.

## Problem

KInfra provides monitoring routes that should **always** be accessible:
- `/kinfra` - Dashboard
- `/__status__` - Status API
- `/__action__/*` - Service actions
- `/__logs__/*` - Log viewer

However, application authentication middleware (AuthKit, NextAuth, custom auth) will intercept these routes by default, causing:
- ❌ Dashboard inaccessible when not logged in
- ❌ Status pages redirect to sign-in
- ❌ Monitoring unavailable during service failures

## Solution

**Exclude KInfra routes from authentication middleware.**

## Framework-Specific Configuration

### Next.js (WorkOS AuthKit)

```typescript
// middleware.ts
import { authkitMiddleware } from '@workos-inc/authkit-nextjs';

export default authkitMiddleware({
  middlewareAuth: {
    enabled: true,
    unauthenticatedPaths: [
      '/',
      '/sign-in',
      '/sign-up',
      // KInfra routes (REQUIRED)
      '/kinfra',
      '/kinfra/:path*',
      '/__status__',
      '/__action__/:path*',
      '/__logs__/:path*'
    ]
  }
});

export const config = {
  matcher: [
    // Exclude KInfra routes from auth matching
    '/((?!_next/static|_next/image|favicon.ico|kinfra|__status__|__action__|__logs__|.*\\.svg$).*)'
  ]
};
```

### Next.js (NextAuth)

```typescript
// middleware.ts
import { withAuth } from 'next-auth/middleware';

export default withAuth({
  callbacks: {
    authorized: ({ req }) => {
      // Always allow KInfra routes
      if (req.nextUrl.pathname.startsWith('/kinfra')) return true;
      if (req.nextUrl.pathname.startsWith('/__status__')) return true;
      if (req.nextUrl.pathname.startsWith('/__action__')) return true;
      if (req.nextUrl.pathname.startsWith('/__logs__')) return true;

      // Normal auth check
      return !!req.nextauth.token;
    }
  }
});

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|kinfra|__status__|__action__|__logs__).*)']
};
```

### Express.js (Passport)

```javascript
// server.js
const express = require('express');
const passport = require('passport');

app.use((req, res, next) => {
  // Skip auth for KInfra routes
  if (req.path.startsWith('/kinfra') ||
      req.path.startsWith('/__status__') ||
      req.path.startsWith('/__action__') ||
      req.path.startsWith('/__logs__')) {
    return next();
  }

  // Normal auth
  passport.authenticate('local')(req, res, next);
});
```

### Django

```python
# settings.py
AUTHENTICATION_EXEMPT_URLS = [
    r'^/kinfra',
    r'^/__status__',
    r'^/__action__/',
    r'^/__logs__/',
]

# middleware.py
class AuthMiddleware:
    def __call__(self, request):
        # Skip KInfra routes
        for pattern in settings.AUTHENTICATION_EXEMPT_URLS:
            if re.match(pattern, request.path):
                return self.get_response(request)

        # Normal auth
        # ...
```

### Flask

```python
# app.py
from functools import wraps

KINFRA_ROUTES = ['/kinfra', '/__status__', '/__action__', '/__logs__']

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth for KInfra
        if any(request.path.startswith(route) for route in KINFRA_ROUTES):
            return f(*args, **kwargs)

        # Normal auth
        if not session.get('user'):
            return redirect('/login')

        return f(*args, **kwargs)
    return decorated
```

### Nginx (Reverse Proxy)

```nginx
# nginx.conf
location ~ ^/(kinfra|__status__|__action__|__logs__) {
    # No auth required
    proxy_pass http://localhost:9100;
}

location / {
    # Require auth
    auth_request /auth;
    proxy_pass http://localhost:9100;
}
```

## Required Exclusions

**Minimum required paths:**

```
/kinfra              - Dashboard HTML
/__status__          - Status JSON API
/__action__/restart  - Restart action
/__action__/stop     - Stop action
/__logs__/*          - Log viewer
```

**Optional (for enhanced security):**

```
/kinfra/health       - Public health check endpoint
/kinfra/status       - Public status page
```

## Security Considerations

### Option 1: Localhost Only (Default)
KInfra fallback server binds to `127.0.0.1` by default.

**Pros:**
- Only accessible from server itself
- No external access
- Safe for production

**Cons:**
- Can't access dashboard remotely
- Need SSH tunnel for remote access

### Option 2: IP Whitelist
```python
# In fallback_server.py or proxy_server.py
ALLOWED_IPS = ['127.0.0.1', '10.0.0.0/8', '192.168.0.0/16']

async def _handle_request(self, request):
    client_ip = request.remote
    if not any(ipaddress.ip_address(client_ip) in ipaddress.ip_network(net) for net in ALLOWED_IPS):
        return web.Response(status=403)
    # ... rest of handler
```

### Option 3: Admin Token
```python
# Set admin token
os.environ['KINFRA_ADMIN_TOKEN'] = 'your-secret-token'

# In middleware/auth
if request.path.startswith('/kinfra'):
    auth_header = request.headers.get('Authorization')
    if auth_header != f"Bearer {os.getenv('KINFRA_ADMIN_TOKEN')}":
        return Response(status=401)
```

### Option 4: SSO (Recommended for Production)
```python
# Use same SSO as application but lighter check
if request.path.startswith('/kinfra'):
    # Only verify token validity, no role checks
    if not verify_token(request.headers.get('Authorization')):
        return redirect('/login')
```

## Cloudflare Tunnel Configuration

### Automatic (via KInfra)
KInfra's tunnel manager automatically configures ingress rules:

```yaml
# Auto-generated by KInfra
ingress:
  - hostname: byte.kooshapari.com
    path: /kinfra
    service: http://localhost:9100  # Proxy routes to fallback

  - hostname: byte.kooshapari.com
    path: /__status__
    service: http://localhost:9100

  - hostname: byte.kooshapari.com
    path: /api
    service: http://localhost:9100  # Proxy routes to service or fallback

  - hostname: byte.kooshapari.com
    service: http://localhost:9100  # Default route
```

### Manual (if needed)
```yaml
# .cloudflared/config.yml
ingress:
  # KInfra routes (no auth required)
  - hostname: byte.kooshapari.com
    path: /kinfra
    service: http://localhost:9000  # Direct to fallback server

  # Application routes (auth required)
  - hostname: byte.kooshapari.com
    service: http://localhost:8001  # Your app
```

## Verification

### Test KInfra Routes Work Without Auth

```bash
# Should return dashboard HTML (not redirect to sign-in)
curl http://localhost:9100/kinfra

# Should return JSON status
curl http://localhost:9100/__status__

# Should work even when logged out
curl https://byte.kooshapari.com/kinfra
```

### Test Application Routes Require Auth

```bash
# Should redirect to sign-in (or return 401)
curl http://localhost:9100/home

# Should require auth
curl https://byte.kooshapari.com/dashboard
```

## Common Patterns

### Pattern 1: Public Dashboard
```typescript
// Everyone can see dashboard
unauthenticatedPaths: ['/kinfra', '/__status__']
```

### Pattern 2: Admin Only
```typescript
// Only admins can access dashboard
middleware: (req) => {
  if (req.nextUrl.pathname.startsWith('/kinfra')) {
    return req.user?.role === 'admin';
  }
  return !!req.user;
}
```

### Pattern 3: IP-Restricted
```nginx
# Nginx: Only allow from internal network
location /kinfra {
    allow 10.0.0.0/8;
    allow 192.168.0.0/16;
    deny all;
    proxy_pass http://localhost:9100;
}
```

## Quick Reference

### Paths to Exclude from Auth

```javascript
const KINFRA_PATHS = [
  '/kinfra',           // Dashboard
  '/kinfra/*',         // Dashboard sub-pages
  '/__status__',       // Status API
  '/__action__/*',     // Action endpoints
  '/__logs__/*'        // Log viewer
];
```

### Regex Pattern (for matchers)

```regex
/(kinfra|__status__|__action__|__logs__)/
```

### Next.js Matcher Exclusion

```javascript
'/((?!_next/static|_next/image|kinfra|__status__|__action__|__logs__|favicon.ico).*)'
```

## Summary

**Always exclude KInfra paths from authentication:**
- `/kinfra` - Dashboard must work when services down
- `/__status__` - Health checks don't require auth
- `/__action__/*` - Actions (can add separate auth if needed)
- `/__logs__/*` - Logs (can add separate auth if needed)

**Result:** Monitoring always available, even during auth failures or service downtime! 🎉
