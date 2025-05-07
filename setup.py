from setuptools import find_packages, setup

setup(
    name="coderatchet",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0",
        "pytest-cov>=4.0",
    ],
    python_requires=">=3.8",
)
