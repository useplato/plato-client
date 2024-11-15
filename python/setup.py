"""This script sets up the Plato Python Client package using setuptools."""

import os

from setuptools import find_packages, setup

os.system("rm -rf ./dist")

setup(
    name="plato-cli",  # Your package name
    version="0.1.14",  # Version number
    packages=find_packages(),  # Finds and includes all packages
    install_requires=["pydantic", "requests"],
    author="Rob Farlow",  # Your name
    author_email="rob@plato.so",  # Your email
    description="Plato Python Client",  # A short description
    long_description=open("../README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/useplato/plato-client",  # Project's URL (if applicable)
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",  # Minimum Python version
)
