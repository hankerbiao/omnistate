#!/usr/bin/env python3
"""
DMLV4 执行进度回传SDK - 安装配置
"""

from setuptools import setup, find_packages
import os

# 读取README文件
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# 读取版本信息
exec(open(os.path.join(here, "dmlv4_execution_sdk", "__init__.py")).read())

setup(
    name="dmlv4-execution-sdk",
    version=__version__,
    description="DMLV4 执行进度回传SDK - 为外部测试框架提供进度上报能力",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DMLV4 Team",
    author_email="dev@dmlv4.com",
    url="https://github.com/dmlv4/execution-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "examples": [
            "pytest>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dmlv4-reporter=dmlv4_execution_sdk.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "dmlv4_execution_sdk": [
            "examples/*.py",
            "*.md",
        ],
    },
    keywords="testing progress reporting sdk workflow dmlv4",
    project_urls={
        "Bug Reports": "https://github.com/dmlv4/execution-sdk/issues",
        "Source": "https://github.com/dmlv4/execution-sdk",
        "Documentation": "https://docs.dmlv4.com/sdk",
    },
)