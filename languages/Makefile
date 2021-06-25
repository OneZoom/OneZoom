# Maintain translations for web2py as gettext po files to make life
# easier for translators.
#
# These rules assume the en-us.py file is generated from source and
# contain every translatable string in the application.  It further
# ignore the default.py and plural-*.py files, because I do not know
# how to best handle them as po files.
#
# Too migrate once from py to po files, run this:
#   make migrate oztree.pot pofiles clean
#
# To generate py files for use when building, run
#   make
#
# To see translation status, run
#   make stats
#
# You need a version of Translation Toolkit where
# https://github.com/translate/translate/issues/3254 is fixed, for
# example the version from Debian.

TRANSLATIONS = ar ca cs de es fr-ca fr hi hu id it my-mm my nl \
	pl pt-br pt ro ru sk sv tr uk zh-cn zh-tw zh

POFILES = $(TRANSLATIONS:=.po)
PYFILES = $(TRANSLATIONS:=.py)

all: $(PYFILES)

pyfiles: $(PYFILES)
pofiles: $(POFILES)

oztree.pot: en-us.py
	web2py2po -P -i en-us.py -o oztree.pot

$(POFILES): oztree.pot
	msgmerge $@ oztree.pot -o $@.new && mv $@.new $@

.po.py:
	po2web2py -i $^ -o $@

clean:
	$(RM) $(PYFILES)

stats:
	for f in $(POFILES); do \
	  printf "%-15s " $$f; msgfmt --output /dev/null --statistics $$f; \
	done

# This target should only be used once, when starting to maintain
# translations as PO files.
migrate:
	for f in $(PYFILES); do \
	  echo web2py2po -P -i $$f -o $${f%.py}.po ; \
	  web2py2po -P -i $$f -o $${f%.py}.po ; \
	done

.SUFFIXES: .po .py .pot
