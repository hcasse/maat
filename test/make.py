#!/usr/bin/python
import elfmake.c as c
import elfmake as m

c.program("main", ["main.c", "ok/ok.c"])

m.make()

print "TEST = %s" % m.get("TEST")
