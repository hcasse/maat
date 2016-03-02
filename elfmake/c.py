import os.path
from elfmake import *
import elfmake as base
import elfmake.recipe as recipe
import elfmake.action as action
import elfmake.std as std

need_c = False
need_cxx = False
cpp_ext = [".cpp", ".cxx", ".C"]
c_comps = ["gcc", "cc"]
cxx_comps = ["g++", "c++"] 

def comp_c_to_o(ress, deps, ctx):
	action.invoke([ress[0].get("CC", "cc"), ress[0].get("CFLAGS"), "-o", ress[0], "-c", deps[0]], ctx)

def comp_cxx_to_o(ress, deps, ctx):
	action.invoke([ress[0].get("CXX", "c++"), ress[0].get("CXXFLAGS"), ress[0].get("CFLAGS"), "-o", ress[0], "-c", deps[0]], ctx)

def select_linker(deps):
	for dep in deps:
		if dep.recipe and dep.recipe.deps:
			if dep.recipe.deps[0].path.get_ext() in cpp_ext:
				return get("CXX", "c++")
	return get("CC", "cc")

def link_program(ress, deps, ctx):
	action.invoke([select_linker(deps), get("CFLAGS"), get("CXXFLAGS"), "-o", ress[0], deps, get("LDFLAGS")], ctx)

recipe.FunGen(".o", ".c", comp_c_to_o)
recipe.FunGen(".o", ".cxx", comp_cxx_to_o)
recipe.FunGen(".o", ".cpp", comp_cxx_to_o)
recipe.FunGen(".o", ".c++", comp_cxx_to_o)
recipe.FunGen(".o", ".C", comp_cxx_to_o)


def program(name, sources):
	if get("IS_WINDOWS"):
		name = name + ".exe"
	name = env.Path(name)
	
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
	objs = [recipe.gen(name.parent(), ".o", s) for s in sources]
	r = recipe.FunRecipe(link_program, [name], objs)
	
	# record it
	std.ALL.append(r.ress[0].path)
	std.CLEAN = std.CLEAN + [file(obj) for obj in objs]
	std.DISTCLEAN.append(r.ress[0].path)


def configure(c):
	if need_c:
		config.find_program("C compiler", "CC", ["gcc", "cc"], ctx = c)
	if need_cxx:
		config.find_program("C++ compiler", "CXX", ["g++", "c++"], ctx = c)
	
config.register("c", configure)
