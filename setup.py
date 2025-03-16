from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="disease_hallmarks",
    version="0.2.0",
    author="Fedor Galkin",
    author_email="f.galkin@insilico.com", 
    description="A tool for analyzing diseases through the lens of aging hallmarks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Insilico-org/disease_hallmarks/",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
)
