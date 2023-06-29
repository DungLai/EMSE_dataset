# -*- coding: utf-8 -*-
#
# dirty_cat documentation build configuration file, created by
# sphinx-quickstart on Tue Mar 13 14:34:47 2018.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.doctest',
              'sphinx.ext.intersphinx',
              'sphinx.ext.mathjax',
              'sphinx.ext.viewcode',
              'sphinx.ext.githubpages',
              'sphinx.ext.napoleon',
              'sphinx_gallery.gen_gallery',
              ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'dirty_cat'
copyright = u'2018, dirty_cat developers'
author = u'dirty_cat developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version_file = os.path.join(
    '..', 'dirty_cat', 'VERSION.txt')
with open(version_file) as fh:
    version = fh.read().strip()
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for autodoc / autosummary ------------------------------------
# generate autosummary even if no references
autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']


autodoc_default_flags = ['members', 'inherited-members']




# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

html_sidebars = {
    '**': [
        'about.html',
        'globallinks.html',
        'relations.html',
        #'searchbox.html',
    ],
    'index': [
        'about.html',
        'localtoc.html',
        'relations.html',
        #'searchbox.html',
    ]
}

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    'logo': 'dirty_cat.svg',
    'github_user': 'dirty-cat',
    'github_repo': 'dirty_cat',
    'github_button': 'true',
    'show_powered_by': 'false',
    'logo_name': 'true',
    'gray_1': "#030",
    'gray_2': "#F1FFF1",
    'link': "#076B00",
#    'gray_3': "#090",
    'fixed_sidebar': 'true',
    'note_bg': "rgb(246, 248, 250);",
    'topic_bg': "rgb(246, 248, 250);",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'dirty_catdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'dirty_cat.tex', u'dirty\\_cat Documentation',
     u'dirty\\_cat developers', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'dirty_cat', u'dirty_cat Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'dirty_cat', u'dirty_cat Documentation',
     author, 'dirty_cat', 'Learning on non-curater categorical data.',
     'Data Science'),
]


# Configuration for intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://docs.scipy.org/doc/numpy', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference', None),
    'matplotlib': ('https://matplotlib.org/', None),
    'sklearn': ('https://scikit-learn.org/0.20', None),
    'skimage': ('http://scikit-image.org/docs/stable/', None),
    'mayavi': ('http://docs.enthought.com/mayavi/mayavi/', None),
    'statsmodels': ('http://www.statsmodels.org/stable/', None),
    'pandas': ('http://pandas.pydata.org/pandas-docs/stable/', None),
    'seaborn': ('http://seaborn.pydata.org/', None),
}


# -- sphinx-gallery configuration -----------------------------------------
from sphinx_gallery.sorting import FileNameSortKey
sphinx_gallery_conf = {
    'doc_module': 'dirty_cat',
    'filename_pattern': '',
    'backreferences_dir': os.path.join('generated'),
    'reference_url': {
        'dirty_cat': None,
        'numpy': 'http://docs.scipy.org/doc/numpy',
        'scipy': 'http://docs.scipy.org/doc/scipy/reference',
        'pandas': 'http://pandas.pydata.org/pandas-docs/stable/',
        #'seaborn': 'http://seaborn.pydata.org/',
        #'matplotlib': 'http://matplotlib.org/',
        'sklearn': 'http://scikit-learn.org/0.20',
        #'scikit-image': 'http://scikit-image.org/docs/stable/',
        #'mayavi': 'http://docs.enthought.com/mayavi/mayavi/',
        #'statsmodels': 'http://www.statsmodels.org/stable/',
        },
    'examples_dirs':'../examples',
    'gallery_dirs':'auto_examples',
    'within_subsection_order': FileNameSortKey,
    'download_section_examples': False,
}
