#!/usr/bin/python
import maat.c as c
import maat as m

CFLAGS = "-g3"

m.file("main.o").set("CC", "cc")

c.program("main", ["main.c", "ok/ok.c"])
m.subdir("ko")

#m.make()
