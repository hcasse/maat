#!/usr/bin/python
from maat import *
import maat.config as config

goal("doc", ["doc/manual.thot"], "cd doc; ../../thot/thot.py manual.thot -DHTML_TEMPLATE=theme/template.html -DHTML_ONE_FILE_PER=chapter")

goal("autodoc", [],
	[
		"mkdir -p autodoc",
		"epydoc --html maat -o autodoc/ -v"
	])

file("doc").DESCRIPTION = "Build the manual of Maat."
file("autodoc").DESCRIPTION = "Build the autotic documentation of Maat for developers."
