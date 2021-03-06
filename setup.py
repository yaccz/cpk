#! /usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import cpk

setup(
    name='cpk',
    version=cpk.__version__,
    description='Password Manager storing data in gnupg encrypted graph',
    author='Jan Matejka',
    author_email='yac@blesmrt.net',
    url='https://github.com/yaccz/cpk',

    packages = find_packages(
        where = '.'
    ),

    install_requires = [
        "setuptools",
        "sqlalchemy",
        "argparse",
        "pyxdg",
        "PyYAML",
    ],

    package_data = {
        "cpk": [ "data/*/*" ]
    },

    entry_points = {
        'console_scripts': ['cpk = cpk.app:main']},

    classifiers = [
        "Programming Language :: Python :: 3 :: Only"
    ],
)
