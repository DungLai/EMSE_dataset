"""For pip."""
from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

exec(open("src/fonduer/_version.py").read())
setup(
    name="fonduer",
    version=__version__,
    description="Knowledge base construction system for richly formatted data.",
    long_description=open("README.rst").read(),
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    install_requires=[
        "bs4",
        "editdistance",
        "lxml",
        "nltk",
        "numpy>=1.11",
        "pandas",
        "psycopg2-binary",
        "pyyaml",
        "scipy>=0.18",
        "snorkel-metal==0.1.1",
        "spacy>=2.0.7",
        "sqlalchemy>=1.0.14",
        "torch>=0.4.0",
        "tqdm",
        "treedlib",
        "wand",
    ],
    extras_require={"spacy_ja": ["mecab-python3"]},
    keywords=["fonduer", "knowledge base construction", "richly formatted data"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest>=3.4.0", "flake8"],
    include_package_data=True,
    url="https://github.com/HazyResearch/fonduer",
    classifiers=[  # https://pypi.python.org/pypi?:action=list_classifiers
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
    ],
    project_urls={
        "Tracker": "https://github.com/HazyResearch/fonduer/issues",
        "Source": "https://github.com/HazyResearch/fonduer",
    },
    python_requires=">=3.6",
    author="Hazy Research",
    author_email="senwu@cs.stanford.edu",
    license="MIT",
)
