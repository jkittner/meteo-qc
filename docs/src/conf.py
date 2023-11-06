project = 'meteo-qc'
copyright = '2022, Jonas Kittner'
author = 'Jonas Kittner'
release = '0.4.1'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
    'sphinxarg.ext',
]
autodoc_typehints = 'both'
typehints_fully_qualified = True
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('http://pandas.pydata.org/pandas-docs/dev', None),
}

html_theme = 'furo'

source_suffix = {'.md': 'markdown'}
