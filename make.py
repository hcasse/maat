#!/usr/bin/python
from maat import *
import maat.config as config
import maat.std as std

doc = goal("doc", ["doc/manual.thot"], "cd doc; ../../thot/thot.py manual.thot -DHTML_TEMPLATE=theme/template.html -DHTML_ONE_FILE_PER=chapter")
doc.DESCRIPTION = "Build the manual of Maat."

autodoc = goal("autodoc", [],
	[
		"mkdir -p autodoc",
		"epydoc --html maat -o autodoc/ -v"
	])
autodoc.DESCRIPTION = "Build the automatic documentation of Maat for developers."
