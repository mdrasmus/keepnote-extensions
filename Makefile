#
# Makefile for keepnote extensions
#

KEEPNOTE=../keepnote-dev/


# Copy over builtin modules
cpbuiltin:
	rm -rf builtin
	mkdir -p builtin
	cp -r $(KEEPNOTE)/extensions/* builtin/

