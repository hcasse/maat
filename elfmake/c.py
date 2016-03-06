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

def is_cxx(deps):
	for dep in deps:
		if dep.recipe and dep.recipe.deps:
			if dep.recipe.deps[0].path.get_ext() in cpp_ext:
				return True
	return False
	

def select_linker(prog, deps):
	if is_cxx(deps):
		return prog.get("CXX", "c++")
	else:
		return prog.get("CC", "cc")


# generic recipes
def comp_c_to_o(r):
	return [r.ress[0].get("CC", "cc"), r.ress[0].get("CFLAGS"), "-o", r.ress[0], "-c", r.deps[0]]
def comp_cxx_to_o(r):
	return [r.ress[0].get("CXX", "c++"), r.ress[0].get("CXXFLAGS"), r.ress[0].get("CFLAGS"), "-o", r.ress[0], "-c", r.deps[0]]
def link_program(r):
	return [select_linker(r.ress[0], r.deps), r.ress[0].get("CFLAGS"), r.ress[0].get("CXXFLAGS"), "-o", r.ress[0], r.deps, r.ress[0].get("LDFLAGS")]

recipe.ActionGen(".o", ".c",   action.Invoke(comp_c_to_o))
recipe.ActionGen(".o", ".cxx", action.Invoke(comp_cxx_to_o))
recipe.ActionGen(".o", ".cpp", action.Invoke(comp_cxx_to_o))
recipe.ActionGen(".o", ".c++", action.Invoke(comp_cxx_to_o))
recipe.ActionGen(".o", ".C",   action.Invoke(comp_cxx_to_o))


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
	r = recipe.ActionRecipe([name], objs, action.Invoke(link_program))
	
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
