# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as f:
    description = f.read()

setup(
    name="lima-cli",
    author="Jose Tiago Macara Coutinho",
    author_email="coutinhotiago@gmail.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={
        'console_scripts': [
            'lima = lima_cli:main'
        ],
    },
    description="Lima CLI",
    license="GPLv3+",
    long_description=description,
    long_description_content_type="text/markdown",
    keywords="Lima, CLI, detector",
    packages=find_packages(),
    url="https://github.com/tiagocoutinho/lima-cli",
    version="0.1.0",
    python_requires=">=3.5"
)
