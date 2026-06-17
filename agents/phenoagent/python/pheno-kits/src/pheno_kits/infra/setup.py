"""Setup configuration for KInfra Python library.

Cross-platform infrastructure library for dynamic port allocation and secure tunneling.
Provides seamless port management and tunneling capabilities for services.
"""

from pathlib import Path

from setuptools import find_packages, setup

# Read the README file
this_directory = Path(__file__).parent
long_description = ""
readme_file = this_directory / "README.md"
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")
else:
    long_description = """
KInfra - Cross-platform infrastructure library for dynamic port allocation and secure tunneling.

Features:
- Smart port allocation with conflict resolution
- Automatic cloudflared tunnel management
- Service lifecycle management
- Multi-language SDK support
- Zero-config operation
"""

setup(
    name="kinfra",
    version="1.0.0",
    author="KInfra Team",
    author_email="admin@kinfra.dev",
    description="Cross-platform infrastructure library for dynamic port allocation and secure tunneling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kooshapari/kinfra",
    project_urls={
        "Bug Tracker": "https://github.com/kooshapari/kinfra/issues",
        "Documentation": "https://kinfra.dev/docs",
        "Source": "https://github.com/kooshapari/kinfra",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "psutil>=5.9.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "all": [
            "aiohttp>=3.8.0",
            "psutil>=5.9.0",
            "pyyaml>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kinfra=kinfra.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords=[
        "infrastructure",
        "port-allocation",
        "tunneling",
        "cloudflared",
        "networking",
        "devops",
        "microservices",
        "development",
        "automation",
    ],
    zip_safe=False,
    test_suite="tests",
    license="MIT",
    platforms=["any"],
)
