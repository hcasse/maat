from elfmake import *
import elfmake.c as c

CC = "gcc"
c.program("ko", ["ko.c"])

#make()
