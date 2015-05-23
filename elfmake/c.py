import os.path
from elfmake import *
import elfmake as base
import elfmake.recipe as recipe

base.CC="cc"
base.CFLAGS=""
base.LDFLAGS=""

def comp_c_to_o(ress, deps):
	invoke(base.CC, base.CFLAGS, "-o", ress[0], "-c", deps[0])

def link_program(ress, deps):
	invoke(base.CC, base.CFLAGS, "-o", ress[0], deps, base.LDFLAGS)

recipe.FunGen(".o", ".c", comp_c_to_o)

def program(name, sources):
	objs = [recipe.gen(os.path.dirname(name), ".o", s) for s in sources]
	recipe.FunRecipe(link_program, [name], objs)
	all.append(name)
