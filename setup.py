#!/usr/bin/env python
from setuptools import setup
from os import unlink
from os.path import exists
from shutil import copy2


copy2('aprio.py', 'aprio')

setup(
    name = "aprio",
    version = "1.0",
    scripts = ['aprio'],
    
    install_requires = ['python-daemon', 'argparse', 'psutil'],
    package_data = {
        '': ['LICENSE', '*.md']
    },
    
    author = "Joseph Hunkeler",
    author_email = 'jhunkeler@gmail.com',
    description = """Automatically prioritizes processes based on user-defined
    thresholds""",
    license = "GPL",
    keywords = 'renice nice priority posix daemon automatic',
    url = 'http://bitbucket.org/jhunkeler/aprio'
)

if exists('aprio'):
    unlink('aprio')
