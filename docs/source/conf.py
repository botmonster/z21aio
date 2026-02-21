# Configuration file for the Sphinx documentation builder.

import sys
from pathlib import Path

# Add src directory to path so autodoc can find modules
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Project information
project = "z21aio"
copyright = "2026, botmonster"
author = "botmonster"
release = "1.0.5"

# Sphinx extensions
extensions = [
    "sphinx.ext.autodoc",  # Extract docstrings from Python code
    "sphinx.ext.napoleon",  # Parse Google-style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx.ext.intersphinx",  # Link to Python standard library
]

# Napoleon extension settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": False,
    "show-inheritance": True,
}

# Theme settings
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "logo_only": False,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "collapse_navigation": False,  # Expand all sections in left sidebar by default
}

# HTML output settings
html_static_path = []
html_favicon = None
html_logo = None

# Intersphinx mapping for Python standard library
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# RST settings
rst_prolog = """
.. |project| replace:: z21aio
"""

# Source file settings
source_suffix = ".rst"
master_doc = "index"
language = "en"
