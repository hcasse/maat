#!/usr/bin/python
from elfmake import *
import elfmake.config as config

goal("doc", ["doc/manual.thot"], "cd doc; ../../thot/thot.py manual.thot -DHTML_TEMPLATE=theme/template.html -DHTML_ONE_FILE_PER=chapter")

goal("autodoc", [],
	[
		"mkdir -p autodoc",
		"epydoc --html elfmake -o autodoc/ -v"
	])
	
make()
