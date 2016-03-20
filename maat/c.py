#	MAAT top-level script
#	Copyright (C) 2016 H. Casse <hugues.casse@laposte.net>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
from maat import *
import maat as base
import maat.recipe as recipe
import maat.action as action
import maat.std as std
from maat import install

# internals
need_c = False
need_cxx = False
need_lib = False
cpp_ext = [".cpp", ".cxx", ".C", ".c++"]
c_comps = ["gcc", "cc"]
cxx_comps = ["g++", "c++"] 

# configuration
CONFIG_CC = config.FindProgram("C compiler", "CC", ["gcc", "cc"])
CONFIG_CXX = config.FindProgram("C++ compiler", "CXX", ["g++", "c++"])
CONFIG_AR = config.FindProgram("library linker", "AR", ["ar"])


# system dependent configuration
if curenv.IS_WINDOWS:
	EXE_SUFFIX = ".exe"
	LIB_PREFIX = ""
	LIB_SUFFIX = ".lib"
	DLIB_PREFIX = ""
	DLIB_SUFFIX = ".dll"
else:
	EXE_SUFFIX = ""
	LIB_PREFIX = "lib"
	LIB_SUFFIX = ".a"
	DLIB_PREFIX = "lib"
	DLIB_SUFFIX = ".so"


# default configuration
env.rootenv.CC = "cc"
env.rootenv.CXX = "c++"
env.rootenv.AR = "ar"

# convenient
def contains_cxx(files):
	for f in files:
		if f.path.get_ext() in cpp_ext:
			return True
	return False

def contains_c(files):
	for f in files:
		if f.path.get_ext() == ".c":
			return True
	return False

def is_cxx(deps):
	return contains_cxx([dep.recipe.deps[0] for dep in deps if dep.recipe])

def check_sources(srcs):
	"""Check if sources contain C++ files or C file and select configuration accordingly."""
	if contains_c(srcs):
		config.register(CONFIG_CC)
	if contains_cxx(srcs):
		config.register(CONFIG_CXX)
	

# commands
class Linker(action.Action):
	prog = None
	objs = None
	is_cxx = None
	
	def __init__(self, prog, objs, is_cxx):
		self.prog = prog
		self.objs = objs
		self.is_cxx = is_cxx
	
	def added(self):
		added = []
		if self.prog.ADDED_PATHS:
			added = ["-L%s" % p for p in self.prog.ADDED_PATHS]
		if self.prog.ADDED_LIBS:
			added = added + ["-l%s" % l for l in self.prog.ADDED_LIBS]
		if self.prog.ADDED_LDFLAGS:
			added = added + [self.prog.ADDED_LDFLAGS]
		if self.prog.RPATH:
			added = added + ["-Wl,-rpath=\"%s\"" % escape(str(p)) for p in list_of(self.prog.RPATH)]
		return added
	
	def command(self):
		if self.is_cxx:
			cc = [self.prog.CC, self.prog.CXXFLAGS]
		else:
			cc = self.prog.CC
		return [cc, self.prog.CFLAGS, "-o", self.prog, self.objs, self.prog.LDFLAGS, self.added()]
	
	def execute(self, ctx):
		action.invoke(self.command(), ctx)
			
	def display(self, out):
		out.write("\t%s\n" % action.make_line(self.command()))
	
def link_lib(ress, deps):
	return [ress[0].AR, "rcs", ress[0], deps]

	
def make_dep_dir(r):
	p = r.ress[0].path.parent()
	temp(maat_dir / p.relative_to_top())


# generic recipes
def comp_c_to_o(ress, deps):
	return [ress[0].CC, ress[0].CFLAGS, "-o", ress[0], "-c", deps[0], ress[0].ADDED_FLAGS]
def comp_cxx_to_o(ress, deps):
	return [ress[0].CXX, ress[0].CXXFLAGS, ress[0].CFLAGS, "-o", ress[0], "-c", deps[0], ress[0].ADDED_FLAGS]

gen_command(".o", ".c",  comp_c_to_o)
gen_command(".o", ".cxx", comp_cxx_to_o)
gen_command(".o", ".cpp", comp_cxx_to_o)
gen_command(".o", ".c++", comp_cxx_to_o)
gen_command(".o", ".C",   comp_cxx_to_o)
gen_command(".o", ".cc",   comp_cxx_to_o)


# Library Delegate
class LibSolver(Delegate):
	prog = None
	libs = None
	
	def __init__(self, prog, libs):
		self.prog = prog
		if isinstance(libs, list):
			self.libs = libs
		else:
			self.libs = str(libs).split()
	
	def perform(self, ctx):
		paths = []
		libs = []
		ldflags = []
		
		# find the dependency
		for lib in self.libs:
			file = recipe.find_exact(lib)
			if file <> None:
				if file.PROVIDE_LIB:
					libs.append(file.PROVIDE_LIB)
				if file.PROVIDE_PATH:
					paths.append(file.PROVIDE_PATH)
				if file.PROVIDE_LDFLAGS:
					ldflags.append(file.PROVIDE_LDFLAGS)
				self.prog.recipe.deps.append(file)
			else:
				libs.append(lib)

		# record information
		self.prog.ADDED_LIBS = libs
		self.prog.ADDED_PATHS = paths
		self.prog.ADDED_LDFLAGS = ldflags

def parse_dep(path):
	try:
		f = open(str(path), "r")
		for l in f.xreadlines():
			p = l.find(":")
			if p >= 0:
				ts = [file(t) for t in l[:p].split()]
				ds = [file(d) for d in l[p+1:-1].split()]
				for t in ts:
					if t.recipe:
						for d in ds:
							t.recipe.add_dep(d)
	except IOError, e:
		pass	

def make_objects(dir, sources, CFLAGS, CXXFLAGS, dyn = False):
	"""Build the objects and their recipes and return the list of objects.
	".o" are automatically added to CLEAN list."""
	check_sources(sources)
	objs = [file(recipe.gen(dir, ".o", s.path)) for s in sources]
	for o in objs:
		if CFLAGS:
			o.CFLAGS = CFLAGS
		if CXXFLAGS:
			o.CXXFLAGS = CXXFLAGS
		added = ""
		if dyn:
			added = "-fPIC"
		d = file(maat_dir / o.path.parent().relative_to_top())
		if not d.recipe:
			recipe.ActionRecipe([d], [], action.MakeDir(d.path))
		o.recipe.deps.append(d)
		df = (d.path / (o.path.get_base().get_file() + ".d"))
		added = added + " -MMD -MF %s" % df.relative_to_cur()
		if added:
			o.ADDED_FLAGS = added
		parse_dep(df)	
	std.CLEAN = std.CLEAN + [obj.path.relative_to(env.topenv.path) for obj in objs]
	return objs
	

def program(name, sources, LDFLAGS = None, CFLAGS = None, CXXFLAGS = None,
LIBS = None, RPATH = None, to = None):
	"""Called to build a C or C++ program."""
	
	# record prog file
	prog = file(name + EXE_SUFFIX)
	recipe.add_alias(prog, name)

	# build objects
	sources = [file(s) for s in sources]
	objs = make_objects(prog.path.parent(), sources, CFLAGS, CXXFLAGS)
	if contains_cxx(sources):
		config.register(CONFIG_CXX)
	else:
		config.register(CONFIG_CC)
	
	# build program
	recipe.ActionRecipe([prog], objs, Linker(prog, objs, contains_cxx(sources)))
	if LDFLAGS:
		prog.LDFLAGS = LDFLAGS
	if LIBS:
		post_inits.append(LibSolver(prog, LIBS))
	if RPATH:
		prog.RPATH = RPATH
	
	# record it
	std.ALL.append(prog)
	std.DISTCLEAN.append(prog)
	install.program(prog, to)


def lib(name, sources, CFLAGS = None, CXXFLAGS = None, PREFIX = LIB_PREFIX, 
SUFFIX = LIB_SUFFIX, type = "static", DYN_PREFIX = DLIB_PREFIX, DYN_SUFFIX = DLIB_SUFFIX,
LDFLAGS =  None, LIBS = None, RPATH = None, to = None):
	"""Called to build a static library."""
	global need_lib
	need_lib = True
	todo = []

	# check type
	if type not in ["static", "dynamic", "both"]:
		raise env.ElfError("library type must be one of static (default), dynamic or both.")

	# build objects
	sources = [file(s) for s in sources]
	objs = make_objects(env.cenv.path, sources, CFLAGS, CXXFLAGS, type in ["dynamic", "both"])

	# build static library
	if type in ["static", "both"]:
		lib = file(PREFIX + name + SUFFIX)
		recipe.ActionRecipe([lib], objs, action.Invoke(link_lib([lib], objs)))
		todo.append(lib)
		std.ALL.append(lib)
		std.DISTCLEAN.append(lib)
		config.register(CONFIG_AR)
		install.lib(lib, to)

	# build dynamic library
	if type in ["dynamic", "both"]:
		lib = file(DYN_PREFIX + name + DYN_SUFFIX)
		recipe.ActionRecipe([lib], objs, Linker(lib, objs, contains_cxx(sources)))
		lib.ADDED_LDFLAGS = "-shared"
		if LDFLAGS:
			prog.LDFLAGS = LDFLAGS
		if LIBS:
			post_inits.append(LibSolver(prog, LIBS))
		if RPATH:
			prog.RPATH = RPATH
		todo.append(lib)
		std.ALL.append(lib)
		std.DISTCLEAN.append(lib)
		if contains_cxx(sources):
			config.register(CONFIG_CXX)
		else:
			config.register(CONFIG_CC)
		install.dlib(lib, to)

	# build main goal
	lib = file(name)
	r = recipe.phony(lib, todo)
	recipe.add_alias(lib, name)
	lib.PROVIDE_PATH = lib.path.parent()
	lib.PROVIDE_LIB = name
