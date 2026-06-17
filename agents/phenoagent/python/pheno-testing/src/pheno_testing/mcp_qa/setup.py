"""
Setup configuration for mcp-QA shared testing library.
"""

from setuptools import find_packages, setup

setup(
    name="mcp-qa",
    version="0.1.0",
    description="Shared testing infrastructure for MCP servers",
    author="Atoms Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastmcp>=0.4.0",
        "pytest>=8.0.0",
        "pytest-asyncio>=0.23.0",
        "httpx>=0.27.0",
        "playwright>=1.40.0",
        "textual>=0.47.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "cryptography>=41.0.0",
        "pyotp>=2.8.0",
    ],
    extras_require={
        "dev": [
            "black",
            "ruff",
            "mypy",
            "pytest-cov",
        ]
    },
    entry_points={
        "pytest11": [
            "mcp_qa_auth = mcp_qa.pytest_plugins.auth_plugin",
        ],
    },
)
