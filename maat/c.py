#	MAAT C module
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

import common
import action
import install
import recipe
import std

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
CONFIG_LEX = config.FindProgram("lexer generator", "LEX", ["flex", "lex"])
CONFIG_YACC = config.FindProgram("parser generator", "YACC", ["bison", "yacc"]) 

config.set_if("CFLAGS_Debug", lambda: "-g3")
config.set_if("CFLAGS_Release", lambda: "-O3")

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
env.root.CC = "cc"
env.root.CXX = "c++"
env.root.AR = "ar"

# convenient
def contains(files, suffs):
	for f in files:
		if f.path.get_ext() in suffs:
			return True
	return False
		

def is_cxx(deps):
	return contains(deps, cpp_ext)

def check_sources(srcs):
	"""Check if sources contain C++ files or C file and select configuration accordingly."""
	if contains(srcs, [".c"]):
		config.register(CONFIG_CC)
	if contains(srcs, cpp_ext):
		config.register(CONFIG_CXX)
	if contains(srcs, [".l"]):
		config.register(CONFIG_LEX)
	if contains(srcs, [".y"]):
		config.register(CONFIG_YACC)
	

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
			cc = [self.prog.CXX, self.prog.CXXFLAGS]
		else:
			cc = self.prog.CC
		return [cc, self.prog.CFLAGS, "-o", self.prog, self.objs, self.prog.LDFLAGS, self.added()]
	
	def execute(self, ctx):
		action.invoke(self.command(), ctx)
			
	def commands(self, cmds):
		cmds.append("%s" % action.make_line(self.command()))
	
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
def comp_l_to_c(ress, deps):
	return [
		action.ShellAction([ress[0].LEX, ress[0].FLAGS, deps[0] ]),
		action.Rename("lex.yy.c", ress[0])
	]
def comp_y_to_c(ress, deps):
	return [ress[0].YACC, ress[0].FLAGS, deps[0], "-o", ress[0]]	
	

gen_command(".o", ".c",  comp_c_to_o)
gen_command(".o", ".cxx", comp_cxx_to_o)
gen_command(".o", ".cpp", comp_cxx_to_o)
gen_command(".o", ".c++", comp_cxx_to_o)
gen_command(".o", ".C",   comp_cxx_to_o)
gen_command(".o", ".cc",   comp_cxx_to_o)
gen_action(".c", ".l", comp_l_to_c)
gen_command(".c", ".y", comp_y_to_c)


# Library Delegate
class LibSolver(common.Delegate):
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
		buf = ""
		for l in f.xreadlines():
			buf = buf + l
			if buf[-2:] == "\\\n":
				buf = buf[:-2]
				continue
			p = buf.find(":")
			if p >= 0:
				ts = [file(t) for t in buf[:p].split()]
				ds = [file(d) for d in buf[p+1:-1].split()]
				for t in ts:
					if t.recipe:
						for d in ds:
							t.recipe.add_dep(d)
			buf = ""
	except IOError, e:
		pass

def make_objects(dir, sources, CFLAGS, CXXFLAGS, dyn = False):
	"""Build the objects and their recipes and return the list of objects.
	".o" are automatically added to CLEAN list."""
	check_sources(sources)
	objs = []
	for s in sources:
		fs = recipe.gen(dir, ".o", s.path)
		std.CLEAN = std.CLEAN + fs
		o = file(fs[-1])
		objs.append(o)
		if CFLAGS:
			o.CFLAGS = CFLAGS
		if CXXFLAGS:
			o.CXXFLAGS = CXXFLAGS
		added = ""
		if dyn:
			added = "-fPIC"
		if o.BUILD_MODE <> "":
			f = o["CFLAGS_%s" % o.BUILD_MODE]
			if f <> None:
				added = "%s %s" % (added, f)
			f = o["CXXFLAGS_%s" % o.BUILD_MODE]
			if f <> None:
				added = "%s %s" % (added, f)
		d = file(maat_dir / o.path.parent().relative_to_top())
		if not d.recipe:
			recipe.ActionRecipe([d], [], action.MakeDir(d.path))
			d.set_hidden()
		o.recipe.deps.append(d)
		df = (d.path / (o.path.get_base().get_file() + ".d"))
		added = added + " -MMD -MF %s" % df.relative_to_cur()
		if added:
			o.ADDED_FLAGS = added
		parse_dep(df)	
	return objs
	

def program(name, sources, LDFLAGS = None, CFLAGS = None, CXXFLAGS = None,
LIBS = None, RPATH = None, INSTALL_TO = ""):
	"""Called to build a C or C++ program."""
	
	# record prog file
	prog = file(name + EXE_SUFFIX)
	recipe.add_alias(prog, name)

	# build objects
	sources = recipe.get_files(sources)
	objs = make_objects(prog.path.parent(), sources, CFLAGS, CXXFLAGS)
	
	# build program
	recipe.ActionRecipe([prog], objs, Linker(prog, objs, is_cxx(sources)))
	if LDFLAGS:
		prog.LDFLAGS = LDFLAGS
	if prog.BUILD_MODE <> "":
		f = prog["LDFLAGS_%s" % prog.BUILD_MODE]
		if f <> None:
			prog.ADDED_LDFLAGS = "%s %s" % (prog.ADDED_LDFLAGS, f)
	if LIBS:
		common.post_inits.append(LibSolver(prog, LIBS))
	if RPATH:
		prog.RPATH = RPATH
	
	# record it
	std.ALL.append(prog)
	std.DISTCLEAN.append(prog)
	if INSTALL_TO <> None:
		prog.INSTALL_TO = INSTALL_TO
		install.program(prog)


def lib(name, sources, CFLAGS = None, CXXFLAGS = None, PREFIX = LIB_PREFIX, 
SUFFIX = LIB_SUFFIX, type = "static", DYN_PREFIX = DLIB_PREFIX, DYN_SUFFIX = DLIB_SUFFIX,
LDFLAGS =  None, LIBS = None, RPATH = None, INSTALL_TO = "", DYN_INSTALL_TO = ""):
	"""Called to build a static library."""
	global need_lib
	need_lib = True
	todo = []

	# check type
	if type not in ["static", "dynamic", "both"]:
		common.script_error("library type must be one of static (default), dynamic or both.")

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
		if INSTALL_TO <> None:
			lib.INSTALL_TO = INSTALL_TO
			install.lib(lib)

	# build dynamic library
	if type in ["dynamic", "both"]:
		lib = file(DYN_PREFIX + name + DYN_SUFFIX)
		recipe.ActionRecipe([lib], objs, Linker(lib, objs, is_cxx(sources)))
		lib.ADDED_LDFLAGS = "-shared"
		if LDFLAGS:
			lib.LDFLAGS = LDFLAGS
		if lib.BUILD_MODE <> "":
			f = lib["LDFLAGS_%s" % lib.BUILD_MODE]
			if f <> None:
				lib.ADDED_LDFLAGS = "%s %s" % (lib.ADDED_LDFLAGS, f)
		if LIBS:
			post_inits.append(LibSolver(prog, LIBS))
		if RPATH:
			prog.RPATH = RPATH
		todo.append(lib)
		std.ALL.append(lib)
		std.DISTCLEAN.append(lib)
		if is_cxx(sources):
			config.register(CONFIG_CXX)
		else:
			config.register(CONFIG_CC)
		if DYN_INSTALL_TO <> None:
			lib.DYN_INSTALL_TO = DYN_INSTALL_TO
			install.dlib(lib)

	# build main goal
	lib = file(name)
	r = recipe.meta(lib, todo)
	recipe.add_alias(lib, name)
	lib.PROVIDE_PATH = lib.path.parent()
	lib.PROVIDE_LIB = name
