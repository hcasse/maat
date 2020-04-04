#!/usr/bin/python

from maat import *
from maat import ocaml

ocaml.program("prog", ["lib.ml", "prog.ml"])
