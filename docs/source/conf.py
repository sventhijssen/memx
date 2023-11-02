# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'MemX'
copyright = '2023, Sven Thijssen'
author = 'Sven Thijssen'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

extensions = [
    "sphinx.ext.autosummary",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

templates_path = ['_templates']
exclude_patterns = []

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.

# The short X.Y version.
# version = networkx.__version__
# The full version, including dev info
# release = networkx.__version__.replace("_", "")

# Options for HTML output
# -----------------------
html_baseurl = "https://memx-library.org/documentation/stable/"
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "collapse_navigation": True,
    "navigation_depth": 2,
    "show_prev_next": False,
    # "icon_links": [
    #     {"name": "Home Page", "url": "https://memx-library.org", "icon": "fas fa-home"},
    #     {
    #         "name": "GitHub",
    #         "url": "https://github.com/sventhijssen/memx",
    #         "icon": "fab fa-github-square",
    #     },
    # ],
    # "external_links": [{"name": "Guides", "url": "https://networkx.org/nx-guides/"}],
    "navbar_end": ["navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc", "edit-this-page"],
    "header_links_before_dropdown": 7,
    # "switcher": {
    #     "json_url": (
    #         "https://networkx.org/documentation/latest/_static/version_switcher.json"
    #     ),
    #     "version_match": "latest" if "dev" in version else version,
    # },
    # "show_version_warning_banner": True,
}
html_sidebars = {
    "**": ["sidebar-nav-bs", "sidebar-ethical-ads"],
    "index": [],
    "install": [],
    "tutorial": [],
}

html_logo = "_static/memx_banner.png"
# html_favicon = "_static/favicon.ico"

html_static_path = ['_static']
