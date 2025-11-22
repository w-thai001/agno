#!/usr/bin/env python3
"""
MLA-FSA Framework - Setup Script

Meta-Learning Architecture Financial Services Agent Framework
A comprehensive framework for building, testing, and deploying
intelligent financial services agents.

Installation:
    pip install .
    pip install -e .  # Development mode
    pip install .[dev]  # With development dependencies
    pip install .[all]  # All optional dependencies
"""

import os
import sys
from pathlib import Path

from setuptools import find_packages, setup

# Ensure Python version compatibility
if sys.version_info < (3, 8):
    sys.exit("Error: MLA-FSA Framework requires Python 3.8 or higher.")

# Read the README for long description
HERE = Path(__file__).parent.resolve()
README_PATH = HERE / "README.md"
REQUIREMENTS_PATH = HERE / "requirements.txt"

long_description = ""
if README_PATH.exists():
    long_description = README_PATH.read_text(encoding="utf-8")

# Parse requirements.txt for dependencies
def parse_requirements(filename: str) -> list:
    """Parse requirements file, filtering out comments and empty lines."""
    requirements = []
    path = HERE / filename

    if not path.exists():
        return requirements

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Handle inline comments
            if "#" in line:
                line = line.split("#")[0].strip()
            if line:
                requirements.append(line)

    return requirements


# Core dependencies (minimal installation)
CORE_REQUIRES = [
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0",
    "aiohttp>=3.8.0,<4.0.0",
    "websockets>=11.0.0,<13.0.0",
    "networkx>=3.1,<4.0.0",
    "python-json-logger>=2.0.0,<3.0.0",
    "pyyaml>=6.0.0,<7.0.0",
    "click>=8.1.0,<9.0.0",
    "rich>=13.0.0,<14.0.0",
    "tenacity>=8.2.0,<9.0.0",
    "cachetools>=5.3.0,<6.0.0",
]

# Testing dependencies
TEST_REQUIRES = [
    "pytest>=7.4.0,<9.0.0",
    "pytest-asyncio>=0.21.0,<1.0.0",
    "pytest-cov>=4.1.0,<6.0.0",
    "pytest-xdist>=3.3.0",
    "pytest-timeout>=2.2.0",
    "pytest-mock>=3.11.0",
    "pytest-html>=4.0.0",
    "pytest-json-report>=1.5.0",
    "coverage[toml]>=7.3.0,<8.0.0",
]

# Development dependencies
DEV_REQUIRES = TEST_REQUIRES + [
    "black>=23.9.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "pylint>=3.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
    "types-requests>=2.31.0",
    "types-pyyaml>=6.0.0",
]

# Documentation dependencies
DOCS_REQUIRES = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.4.0",
    "mkdocstrings[python]>=0.23.0",
    "docstring-parser>=0.15",
]

# Performance monitoring dependencies
MONITORING_REQUIRES = [
    "prometheus-client>=0.17.0",
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "memory-profiler>=0.61.0",
    "aiomonitor>=0.6.0",
]

# Financial data dependencies
FINANCE_REQUIRES = [
    "yfinance>=0.2.28",
    "pandas>=2.0.0,<3.0.0",
    "numpy>=1.24.0,<2.0.0",
]

# AI/ML integration dependencies
AI_REQUIRES = [
    "openai>=1.0.0,<2.0.0",
    "anthropic>=0.7.0,<1.0.0",
]

# Database dependencies
DB_REQUIRES = [
    "sqlalchemy>=2.0.0,<3.0.0",
    "aiosqlite>=0.19.0",
    "redis>=4.6.0,<6.0.0",
]

# All optional dependencies
ALL_REQUIRES = (
    TEST_REQUIRES
    + DEV_REQUIRES
    + DOCS_REQUIRES
    + MONITORING_REQUIRES
    + FINANCE_REQUIRES
    + AI_REQUIRES
    + DB_REQUIRES
)

setup(
    # Package metadata
    name="mla-fsa-framework",
    version="1.0.0",
    author="Agno Team",
    author_email="team@agno.dev",
    description="Meta-Learning Architecture Financial Services Agent Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agno-agi/agno",
    project_urls={
        "Documentation": "https://docs.agno.dev/fsa-framework",
        "Source": "https://github.com/agno-agi/agno",
        "Bug Tracker": "https://github.com/agno-agi/agno/issues",
        "Changelog": "https://github.com/agno-agi/agno/blob/main/CHANGELOG.md",
    },
    license="MIT",
    keywords=[
        "financial-services",
        "agent",
        "ai",
        "machine-learning",
        "meta-learning",
        "fsa",
        "workflow",
        "automation",
        "testing",
        "monitoring",
    ],

    # Package configuration
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    package_dir={"": "."},
    include_package_data=True,
    package_data={
        "mla_fsa_framework": [
            "config/*.json",
            "config/*.yaml",
            "templates/*.html",
            "schemas/*.json",
        ],
    },

    # Python version requirement
    python_requires=">=3.8",

    # Dependencies
    install_requires=CORE_REQUIRES,
    extras_require={
        "test": TEST_REQUIRES,
        "dev": DEV_REQUIRES,
        "docs": DOCS_REQUIRES,
        "monitoring": MONITORING_REQUIRES,
        "finance": FINANCE_REQUIRES,
        "ai": AI_REQUIRES,
        "db": DB_REQUIRES,
        "all": ALL_REQUIRES,
    },

    # Entry points for CLI commands
    entry_points={
        "console_scripts": [
            # Main FSA CLI
            "mla-fsa=agno.fsa_integration_layer:main",

            # Test suite generator
            "fsa-test-gen=agno.fsa10_test_suite_generator:main",

            # Individual tools
            "fsa-server=agno.fsa_integration_layer:run_server_cli",
            "fsa-dashboard=agno.fsa_integration_layer:generate_dashboard_cli",
            "fsa-health=agno.fsa_integration_layer:health_check_cli",
        ],
        "pytest11": [
            # Pytest plugin for FSA testing
            "fsa_testing=agno.fsa10_test_suite_generator:pytest_plugin",
        ],
    },

    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Framework :: AsyncIO",
        "Framework :: Pytest",
        "Typing :: Typed",
    ],

    # Additional metadata
    zip_safe=False,
    platforms=["any"],
)


# Post-installation message
def post_install_message():
    """Display post-installation instructions."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MLA-FSA Framework Installation Complete                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Quick Start:                                                                ║
║  -----------                                                                 ║
║  1. Start the monitoring server:                                             ║
║     $ mla-fsa server --port 8765                                             ║
║                                                                              ║
║  2. Generate test suite:                                                     ║
║     $ fsa-test-gen --module your_fsa.py --output tests/                      ║
║                                                                              ║
║  3. Check system health:                                                     ║
║     $ fsa-health --json                                                      ║
║                                                                              ║
║  4. Generate dashboard:                                                      ║
║     $ fsa-dashboard --output dashboard.html                                  ║
║                                                                              ║
║  Documentation: https://docs.agno.dev/fsa-framework                          ║
║  Support: https://github.com/agno-agi/agno/issues                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    setup()
