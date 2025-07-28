#!/usr/bin/env python3
"""
DST Submittals Generator Setup Script
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dst-submittals-generator",
    version="1.0.0",
    author="DST Engineering",
    author_email="engineering@dst.com",
    description="A comprehensive tool for generating professional HVAC submittal documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dst-engineering/dst-submittals-generator",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Other Audience",
        "Topic :: Office/Business :: Office Suites",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "dst-submittals=src.create_final_pdf:main",
        ],
    },
    keywords="hvac, submittal, pdf, document, automation, engineering",
    project_urls={
        "Bug Reports": "https://github.com/dst-engineering/dst-submittals-generator/issues",
        "Source": "https://github.com/dst-engineering/dst-submittals-generator",
        "Documentation": "https://github.com/dst-engineering/dst-submittals-generator#readme",
    },
)