# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from setuptools import find_packages, setup

here = os.path.dirname(__file__)


def read_requirements(file_):
    requires = []
    links = []
    with open(os.path.join(here, file_)) as f:
        for line in f.readlines():
            line = line.strip()

            if line.startswith("https://"):
                links.append(line + "-1.0.0")
                extras = ""
                if "[" in line:
                    extras = "[" + line.split("[")[1].split("]")[0] + "]"
                line = line.split("#")[1].split("egg=")[1] + extras
            elif line == "" or line.startswith("#") or line.startswith("-"):
                continue
            line = line.split("#")[0].strip()
            requires.append(line)

    return sorted(list(set(requires))), links


install_requires, dependency_links = read_requirements("requirements.txt")


with open(os.path.join(here, "VERSION")) as f:
    version = f.read().strip()

extras_require = {
    "nlp": [
        "spacy==2.1.3",
        "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-2.1.0/en_core_web_sm-2.1.0.tar.gz#egg=en-core-web-sm",
    ]
}

setup(
    name="bugbug",
    version=version,
    description="ML tools for Mozilla projects",
    author="Marco Castelluccio",
    author_email="mcastelluccio@mozilla.com",
    install_requires=install_requires,
    extra_require=extras_require,
    dependency_links=dependency_links,
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    include_package_data=True,
    license="MPL2",
    entry_points={
        "console_scripts": [
            "bugbug-data-commits = scripts.commit_retriever:main",
            "bugbug-data-bugzilla = scripts.bug_retriever:main",
            "bugbug-train = scripts.trainer:main",
        ]
    },
)
