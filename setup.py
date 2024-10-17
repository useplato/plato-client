from setuptools import setup, find_packages

setup(
    name="potato",  # Your package name
    version="0.1",  # Version number
    packages=find_packages(),  # Finds and includes all packages
    install_requires=[],  # External dependencies (if any)
    author="Rob Farlow",  # Your name
    author_email="rob@usepotato.com",  # Your email
    description="Potato Brower Python Client",  # A short description
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/usepotato/potato-python-client",  # Project's URL (if applicable)
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",  # Minimum Python version
)
