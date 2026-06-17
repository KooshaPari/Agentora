"""
Built-in provider configurations for OAuth automation.
"""

from .auth0 import AUTH0_FLOW
from .authkit import AUTHKIT_FLOW
from .azure_ad import AZURE_AD_FLOW
from .github import GITHUB_FLOW
from .google import GOOGLE_FLOW, GOOGLE_WORKSPACE_FLOW
from .okta import OKTA_FLOW
from .onelogin import ONELOGIN_FLOW

__all__ = [
    "AUTH0_FLOW",
    "AUTHKIT_FLOW",
    "AZURE_AD_FLOW",
    "GOOGLE_FLOW",
    "GOOGLE_WORKSPACE_FLOW",
    "GITHUB_FLOW",
    "OKTA_FLOW",
    "ONELOGIN_FLOW",
]
