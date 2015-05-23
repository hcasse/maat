import os.path
from elfmake import *
import elfmake as base
import elfmake.recipe as recipe

need_c = False
need_cxx = False
cpp_ext = [".cpp", ".cxx", ".C"]
c_comps = ["gcc", "cc"]
cxx_comps = ["g++", "c++"] 

def comp_c_to_o(ress, deps):
	invoke(get("CC", "cc"), get("CFLAGS"), "-o", ress[0], "-c", deps[0])

def link_program(ress, deps):
	invoke(get("CC", "cc"), get("CFLAGS"), "-o", ress[0], deps, get("LDFLAGS"))

recipe.FunGen(".o", ".c", comp_c_to_o)


def program(name, sources):
	
	# C++ program?
	cxx = False
	for s in sources:
		if ext_of(s) in cpp_ext:
			cpp = True
			break
	if cxx:
		global need_cxx
		need_cxx = True
	else:
		global need_c
		need_c = True
	
	# build recipe
	objs = [recipe.gen(os.path.dirname(name), ".o", s) for s in sources]
	r = recipe.FunRecipe(link_program, [name], objs)


def configure():
	if need_c:
		config.find_program("C compiler", "CC", ["gcc", "cc"])
	if need_cxx:
		config.find_program("C++ compilaer", "CXX", ["g++", "c++"])
	
config.register("c", configure)
