#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import find_packages, setup


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

VERSION = {}
with open(os.path.join(here, 'errant', 'version.py')) as f:
    exec(f.read(), VERSION)

setup(
    name='Errant',
    version=VERSION['VERSION'],
    description='ERRor ANnotation Toolkit: Automatically extract and classify grammatical errors in parallel original and corrected sentences.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Sai Prasanna',
    author_email='sai.r.prasanna@gmail.com',
    python_requires='>=3.6.0',
    url='https://github.com/sai-prasanna/errant.git',
    packages=find_packages(exclude=["*.tests", "*.tests.*",
                                    "tests.*", "tests"]),
    install_requires=[
        'spacy>=2.0,<2.1',
        'nltk',
        'python-Levenshtein==0.12.0'
    ],
    entry_points={
        'console_scripts': [
            "errant=errant.commands.run:run"
        ]
    },
    extras_require={},
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)
