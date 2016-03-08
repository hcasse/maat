import os.path
from maat import *
import maat as base
import maat.recipe as recipe
import maat.action as action
import maat.std as std

# internals
need_c = False
need_cxx = False
cpp_ext = [".cpp", ".cxx", ".C"]
c_comps = ["gcc", "cc"]
cxx_comps = ["g++", "c++"] 

# default configuration
env.rootenv.CC = "cc"
env.rootenv.CXX = "c++"

# convenient
def is_cxx(deps):
	for dep in deps:
		if dep.recipe and dep.recipe.deps:
			if dep.recipe.deps[0].path.get_ext() in cpp_ext:
				return True
	return False
	
def select_linker(prog, deps):
	if is_cxx(deps):
		return prog.CXX
	else:
		return prog.CC

# generic recipes
def comp_c_to_o(r):
	return [r.ress[0].CC, r.ress[0].CFLAGS, "-o", r.ress[0], "-c", r.deps[0]]
def comp_cxx_to_o(r):
	return [r.ress[0].CXX, r.ress[0].CXXFLAGS, r.ress[0].CFLAGS, "-o", r.ress[0], "-c", r.deps[0]]
def link_program(r):
	return [select_linker(r.ress[0], r.deps), r.ress[0].CFLAGS, r.ress[0].CXXFLAGS, "-o", r.ress[0], r.deps, r.ress[0].LDFLAGS]

gen_command(".o", ".c",   comp_c_to_o)
gen_command(".o", ".cxx", comp_cxx_to_o)
gen_command(".o", ".cpp", comp_cxx_to_o)
gen_command(".o", ".c++", comp_cxx_to_o)
gen_command(".o", ".C",   comp_cxx_to_o)


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
	std.DISTCLEAN.append(r.ress[0])


def configure(c):
	if need_c:
		config.find_program("C compiler", "CC", ["gcc", "cc"], ctx = c)
	if need_cxx:
		config.find_program("C++ compiler", "CXX", ["g++", "c++"], ctx = c)
	
config.register("c", configure)
