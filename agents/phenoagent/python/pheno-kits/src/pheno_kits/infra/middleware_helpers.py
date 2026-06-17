"""
Middleware Helpers - Auth bypass patterns for KInfra routes

Provides helpers and constants for excluding KInfra monitoring routes from authentication.
"""

# Required KInfra paths that must bypass authentication
KINFRA_PATHS = [
    "/kinfra",  # Dashboard
    "/kinfra/",  # Dashboard with trailing slash
    "/__status__",  # Status API
    "/__action__/",  # Action endpoints
    "/__logs__/",  # Log viewer
]

# Regex pattern for path matching
KINFRA_PATH_PATTERN = r"^/(kinfra|__status__|__action__|__logs__)"

# Glob patterns for various frameworks
KINFRA_GLOB_PATTERNS = [
    "/kinfra",
    "/kinfra/:path*",
    "/__status__",
    "/__action__/:path*",
    "/__logs__/:path*",
]


def should_bypass_auth(path: str) -> bool:
    """Check if a path should bypass authentication.

    Args:
        path: Request path

    Returns:
        True if path is a KInfra route that should bypass auth

    Example:
        >>> should_bypass_auth('/kinfra')
        True
        >>> should_bypass_auth('/dashboard')
        False
    """
    return any(path.startswith(kinfra_path.rstrip("/")) for kinfra_path in KINFRA_PATHS)


def get_nextjs_authkit_config() -> dict:
    """Get Next.js AuthKit middleware configuration with KInfra paths excluded.

    Returns:
        Config dict ready for authkitMiddleware()

    Example:
        >>> from kinfra.middleware_helpers import get_nextjs_authkit_config
        >>> export default authkitMiddleware(get_nextjs_authkit_config())
    """
    return {
        "middlewareAuth": {
            "enabled": True,
            "unauthenticatedPaths": [
                "/",
                "/sign-in",
                "/sign-up",
                # KInfra monitoring routes
                *KINFRA_GLOB_PATTERNS,
            ],
        },
    }


def get_nextjs_matcher_pattern() -> str:
    """Get Next.js middleware matcher pattern excluding KInfra routes.

    Returns:
        Regex pattern for Next.js config.matcher

    Example:
        >>> export const config = { matcher: [get_nextjs_matcher_pattern()] }
    """
    return "/((?!_next/static|_next/image|favicon.ico|kinfra|__status__|__action__|__logs__|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"


def get_express_middleware():
    """Get Express.js middleware function that bypasses auth for KInfra routes.

    Returns:
        Express middleware function

    Example:
        >>> app.use(get_express_middleware())
    """

    def kinfra_auth_bypass(req, res, next):
        """
        Express middleware to bypass auth for KInfra routes.
        """
        if should_bypass_auth(req.path):
            return next()

        # Continue to normal auth
        return next()

    return kinfra_auth_bypass


def get_django_exempt_urls() -> list:
    """Get Django URL patterns to exempt from authentication.

    Returns:
        List of regex patterns for Django

    Example:
        >>> AUTHENTICATION_EXEMPT_URLS = get_django_exempt_urls()
    """
    return [r"^/kinfra", r"^/__status__", r"^/__action__/", r"^/__logs__/"]


# Framework-specific examples as strings for easy copy-paste

NEXTJS_AUTHKIT_EXAMPLE = """
// middleware.ts
import { authkitMiddleware } from '@workos-inc/authkit-nextjs';

export default authkitMiddleware({
  middlewareAuth: {
    enabled: true,
    unauthenticatedPaths: [
      '/', '/sign-in', '/sign-up',
      // KInfra routes (required for monitoring)
      '/kinfra', '/kinfra/:path*',
      '/__status__', '/__action__/:path*', '/__logs__/:path*'
    ]
  }
});

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|kinfra|__status__|__action__|__logs__|.*\\.svg$).*)'
  ]
};
"""

NEXTJS_NEXTAUTH_EXAMPLE = """
// middleware.ts
import { withAuth } from 'next-auth/middleware';

export default withAuth({
  callbacks: {
    authorized: ({ req }) => {
      // Always allow KInfra routes
      const path = req.nextUrl.pathname;
      if (path.startsWith('/kinfra') || path.startsWith('/__status__') ||
          path.startsWith('/__action__') || path.startsWith('/__logs__')) {
        return true;
      }
      return !!req.nextauth.token;
    }
  }
});
"""

EXPRESS_EXAMPLE = """
// server.js
const KINFRA_PATHS = ['/kinfra', '/__status__', '/__action__', '/__logs__'];

app.use((req, res, next) => {
  // Skip auth for KInfra routes
  if (KINFRA_PATHS.some(path => req.path.startsWith(path))) {
    return next();
  }

  // Normal auth
  requireAuth(req, res, next);
});
"""

DJANGO_EXAMPLE = """
# settings.py
AUTHENTICATION_EXEMPT_URLS = [
    r'^/kinfra',
    r'^/__status__',
    r'^/__action__/',
    r'^/__logs__/',
]

# middleware.py
from django.conf import settings
import re

class KInfraAuthBypass:
    def __call__(self, request):
        for pattern in settings.AUTHENTICATION_EXEMPT_URLS:
            if re.match(pattern, request.path):
                return self.get_response(request)
        # Continue to auth
        # ...
"""

FLASK_EXAMPLE = """
# app.py
from functools import wraps

KINFRA_ROUTES = ['/kinfra', '/__status__', '/__action__', '/__logs__']

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if any(request.path.startswith(r) for r in KINFRA_ROUTES):
            return f(*args, **kwargs)

        if not session.get('user'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/<path:path>')
@require_auth
def catch_all(path):
    # ...
"""


def print_integration_guide(framework: str = "nextjs"):
    """Print integration guide for a specific framework.

    Args:
        framework: 'nextjs', 'express', 'django', 'flask'

    Example:
        >>> from kinfra.middleware_helpers import print_integration_guide
        >>> print_integration_guide('nextjs')
    """
    examples = {
        "nextjs": NEXTJS_AUTHKIT_EXAMPLE,
        "nextjs-authkit": NEXTJS_AUTHKIT_EXAMPLE,
        "nextjs-nextauth": NEXTJS_NEXTAUTH_EXAMPLE,
        "express": EXPRESS_EXAMPLE,
        "django": DJANGO_EXAMPLE,
        "flask": FLASK_EXAMPLE,
    }

    example = examples.get(framework.lower())
    if example:
        print(f"\n=== KInfra Auth Integration for {framework.upper()} ===\n")
        print(example)
        print("\n" + "=" * 60)
    else:
        print(f"No example for framework: {framework}")
        print(f"Available: {', '.join(examples.keys())}")
