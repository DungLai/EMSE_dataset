#!/usr/bin/env python
import csv
import importlib
import os
import shutil
import sys
from setuptools import setup, find_packages

# Constants
DISTNAME = 'Kymatio'
DESCRIPTION = 'Wavelet scattering transforms in Python with GPU acceleration'
URL = 'https://kymatio.github.io'
LICENSE = 'BSD-3-Clause'


# Parse description
with open('README.md') as f:
    LONG_DESCRIPTION = f.read()


# Parse version.py
kymatio_version_spec = importlib.util.spec_from_file_location(
    'kymatio_version', 'kymatio/version.py')
kymatio_version_module = importlib.util.module_from_spec(kymatio_version_spec)
kymatio_version_spec.loader.exec_module(kymatio_version_module)
VERSION = kymatio_version_module.version


# Parse requirements.txt
with open('requirements.txt', 'r') as f:
    REQUIREMENTS = f.read().split('\n')


setup_info = dict(
    # Metadata
    name=DISTNAME,
    version=VERSION,
    author=('Edouard Oyallon, Eugene Belilovsky, Sergey Zagoruyko, '
            'Michael Eickenberg, Mathieu Andreux, Georgios Exarchakis, '
            'Louis Thiry, Vincent Lostanlen, Joakim AndÃ©n, '
            'TomÃ¡s Angles, Gabriel Huang, Roberto Leonarduzzi'),
    author_email=('edouard.oyallon@centralesupelec.fr, belilove@iro.umontreal.ca, '
                  'sergey.zagoruyko@inria.fr, michael.eickenberg@berkeley.edu, '
                  'mathieu.andreux@ens.fr, georgios.exarchakis@ens.fr, '
                  'louis.thiry@ens.fr, vincent.lostanlen@nyu.edu, janden@flatironinstitute.org, '
                  'tomas.angles@ens.fr, gabriel.huang@umontreal.ca, roberto.leonarduzzi@ens.fr'),
    url=URL,
    download_url='https://github.com/kymatio/kymatio/releases',
    classifiers=['Intended Audience :: Education',
                 'Intended Audience :: Science/Research',
                 'License :: OSI Approved :: BSD License',
                 'Natural Language :: English',
                 'Operating System :: MacOS',
                 'Operating System :: Microsoft :: Windows',
                 'Operating System :: POSIX :: Linux',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8',
                 'Topic :: Multimedia :: Graphics :: 3D Modeling',
                 'Topic :: Multimedia :: Sound/Audio :: Analysis',
                 'Topic :: Scientific/Engineering :: Artificial Intelligence',
                 'Topic :: Scientific/Engineering :: Chemistry',
                 'Topic :: Scientific/Engineering :: Image Recognition',
                 'Topic :: Scientific/Engineering :: Information Analysis',
                 'Topic :: Scientific/Engineering :: Mathematics',
                 'Topic :: Scientific/Engineering :: Physics',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 ],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    license=LICENSE,
    packages=find_packages(exclude=('test',)),
    install_requires=REQUIREMENTS,
    zip_safe=True,
)

setup(**setup_info)
