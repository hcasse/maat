#!/usr/bin/python
from elfmake import *
import elfmake.config as config

goal("doc", ["doc/manual.thot"], "cd doc; ../../thot/thot.py manual.thot")

goal("autodoc", [],
	[
		"mkdir -p autodoc",
		"epydoc --html elfmake -o autodoc/ -v"
	])
	
make()
