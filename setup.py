#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from typing import Dict
from setuptools import find_packages, setup


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

VERSION :Dict[str, str] = {}
with open(os.path.join(here, "errant", "version.py")) as f:
    exec(f.read(), VERSION)

setup(
    name="errant",
    version=VERSION["VERSION"],
    description="ERRor ANnotation Toolkit: Automatically extract and classify grammatical errors in parallel original and corrected sentences.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sai Prasanna",
    author_email="sai.r.prasanna@gmail.com",
    python_requires=">=3.6.0",
    url="https://github.com/sai-prasanna/errant",
    packages=find_packages(exclude=["*.tests", "*.tests.*",
                                    "tests.*", "tests"]),
    install_requires=[
        "spacy==1.9.0",
        "nltk>=3.0",
        "python-Levenshtein>=0.12.0'"
    ],
    entry_points={
        "console_scripts": [
            "errant=errant.commands.run:run"
        ]
    },
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
