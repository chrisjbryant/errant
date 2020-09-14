from pathlib import Path
from setuptools import setup, find_packages

# Get base working directory.
base_dir = Path(__file__).resolve().parent

# Readme text for long description
with open(base_dir/"README.md") as f:
    readme = f.read()
    
setup(
    name = "errant",
    version = "2.2.2",
    license = "MIT",
    description = "The ERRor ANnotation Toolkit (ERRANT). Automatically extract and classify edits in parallel sentences.",
    long_description = readme,
    long_description_content_type = "text/markdown",
    author = "Christopher Bryant, Mariano Felice",
    author_email = "christopher.bryant@cl.cam.ac.uk",
    url = "https://github.com/chrisjbryant/errant",    
    keywords = ["automatic annotation", "grammatical errors", "natural language processing"],
    python_requires = ">= 3.3",
    install_requires = ["spacy>=2.2.0", "python-Levenshtein==0.12.0"],
    packages = find_packages(),    
    include_package_data=True,
    entry_points = {
        "console_scripts": [
            "errant_compare = errant.commands.compare_m2:main",
            "errant_m2 = errant.commands.m2_to_m2:main",
            "errant_parallel = errant.commands.parallel_to_m2:main"]},
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        "Topic :: Education",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing :: Linguistic"]
)
