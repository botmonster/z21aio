# Makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
PAPER         ?=
BUILDDIR      ?= build

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) source
# the i18n builder cannot share the same doctrees and builddir
# without some nastiness.
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) source

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ $(ALLSPHINXOPTS) $(O)

help:
	@$(SPHINXBUILD) -M help $(ALLSPHINXOPTS) $(O)

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*

.PHONY: html
html:
	@echo "Building HTML documentation..."
	@$(SPHINXBUILD) -M html $(ALLSPHINXOPTS) $(O)
	@echo "HTML output built in $(BUILDDIR)/html"

.PHONY: dirhtml
dirhtml:
	$(SPHINXBUILD) -M dirhtml $(ALLSPHINXOPTS) $(O)

.PHONY: singlehtml
singlehtml:
	$(SPHINXBUILD) -M singlehtml $(ALLSPHINXOPTS) $(O)

.PHONY: pickle
pickle:
	$(SPHINXBUILD) -M pickle $(ALLSPHINXOPTS) $(O)

.PHONY: json
json:
	$(SPHINXBUILD) -M json $(ALLSPHINXOPTS) $(O)

.PHONY: htmlhelp
htmlhelp:
	$(SPHINXBUILD) -M htmlhelp $(ALLSPHINXOPTS) $(O)

.PHONY: qthelp
qthelp:
	$(SPHINXBUILD) -M qthelp $(ALLSPHINXOPTS) $(O)

.PHONY: devhelp
devhelp:
	$(SPHINXBUILD) -M devhelp $(ALLSPHINXOPTS) $(O)

.PHONY: epub
epub:
	$(SPHINXBUILD) -M epub $(ALLSPHINXOPTS) $(O)

.PHONY: latex
latex:
	$(SPHINXBUILD) -M latex $(ALLSPHINXOPTS) $(O)

.PHONY: latexpdf
latexpdf:
	$(SPHINXBUILD) -M latexpdf $(ALLSPHINXOPTS) $(O)

.PHONY: latexpdfja
latexpdfja:
	$(SPHINXBUILD) -M latexpdfja $(ALLSPHINXOPTS) $(O)

.PHONY: text
text:
	$(SPHINXBUILD) -M text $(ALLSPHINXOPTS) $(O)

.PHONY: man
man:
	$(SPHINXBUILD) -M man $(ALLSPHINXOPTS) $(O)

.PHONY: texinfo
texinfo:
	$(SPHINXBUILD) -M texinfo $(ALLSPHINXOPTS) $(O)

.PHONY: gettext
gettext:
	$(SPHINXBUILD) -M gettext $(ALLSPHINXOPTS) $(O)

.PHONY: changes
changes:
	$(SPHINXBUILD) -M changes $(ALLSPHINXOPTS) $(O)

.PHONY: linkcheck
linkcheck:
	$(SPHINXBUILD) -M linkcheck $(ALLSPHINXOPTS) $(O)

.PHONY: doctest
doctest:
	$(SPHINXBUILD) -M doctest $(ALLSPHINXOPTS) $(O)

.PHONY: coverage
coverage:
	$(SPHINXBUILD) -M coverage $(ALLSPHINXOPTS) $(O)

.PHONY: xml
xml:
	$(SPHINXBUILD) -M xml $(ALLSPHINXOPTS) $(O)

.PHONY: pseudoxml
pseudoxml:
	$(SPHINXBUILD) -M pseudoxml $(ALLSPHINXOPTS) $(O)

.PHONY: serve
serve: html
	cd $(BUILDDIR)/html && python -m http.server 8000
