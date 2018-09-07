#!/usr/bin/python
import maat.c as c
from maat import *
from maat import install
from maat import std

CFLAGS = "-g3"

file("main.o").CC = "cc"
file("main.o").CFLAGS = "-O2"

c.program("main", ["main.c", "ok/ok.c", "lexer.l"], LIBS = ["m", "mylib"], RPATH = ["$ORIGIN"])
subdir("ko")
subdir("lib")

print "my compiler is %s" % curenv.CC

PROJECT = "test"
install.data("README")
install.data("doc")

phony("show", [], show("Hello, World!"))

f = makefile("COUCOU", "coucou")
std.ALL.append(f)
