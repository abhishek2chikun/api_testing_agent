"""
Setup file for API Testing Agent.
Allows installation with: pip install -e .
"""
from setuptools import setup, find_packages

setup(
    name="api-testing-agent",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "requests",
        "PyGithub",
        "openai",
        "python-dotenv",
        "pydantic",
        "PyYAML",
        "pytest",
        "schemathesis",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
    },
    entry_points={
        "console_scripts": [
            "api-testing-agent=main:main",
        ],
    },
    python_requires=">=3.9",
)

