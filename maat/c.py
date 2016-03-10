import os.path
from maat import *
import maat as base
import maat.recipe as recipe
import maat.action as action
import maat.std as std

# internals
need_c = False
need_cxx = False
need_lib = False
cpp_ext = [".cpp", ".cxx", ".C", ".c++"]
c_comps = ["gcc", "cc"]
cxx_comps = ["g++", "c++"] 


# system dependent configuration
if curenv.IS_WINDOWS:
	EXE_SUFFIX = ".exe"
	LIB_PREFIX = ""
	LIB_SUFFIX = ".lib"
else:
	EXE_SUFFIX = ""
	LIB_PREFIX = "lib"
	LIB_SUFFIX = ".a"


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

def find_lib(lib):
	file = recipe.find_exact(lib)
	if file <> None and file.PROVIDE_LDFLAGS:
			return file.PROVIDE_LDFLAGS
	else:
		return "-l%s" % lib

def make_libs(libs):
	if not libs:
		return []
	if not isinstance(libs, list):
		libs = str(libs).split()
	return [find_lib(lib) for lib in libs]

def check_sources(srcs):
	"""Check if sources contain C++ files or C file and select configuration accordingly."""
	global need_c	
	if not need_c:
		need_c = contains_c(srcs)

	global need_cxx
	if not need_cxx:
		need_cxx = contains_cxx(srcs)

# commands
def comp_c_to_o(r):
	return [r.ress[0].CC, r.ress[0].CFLAGS, "-o", r.ress[0], "-c", r.deps[0]]
def comp_cxx_to_o(r):
	return [r.ress[0].CXX, r.ress[0].CXXFLAGS, r.ress[0].CFLAGS, "-o", r.ress[0], "-c", r.deps[0]]

class ProgramLinker(action.Action):
	prog = None
	objs = None
	is_cxx = None
	
	def __init__(self, prog, objs, is_cxx):
		self.prog = prog
		self.objs = objs
		self.is_cxx = is_cxx
	
	def command(self):
		
		# prepare added flags
		added = []
		if self.prog.ADDED_PATHS:
			added = ["-L%s" % p for p in self.prog.ADDED_PATHS]
		if self.prog.ADDED_LIBS:
			added = added + ["-l%s" % l for l in self.prog.ADDED_LIBS]
		if self.prog.ADDED_LDFLAGS:
			added = added + self.prog.ADDED_LDFLAGS
		
		# perform the build
		if self.is_cxx:
			return [self.prog.CXX, self.prog.CFLAGS, self.prog.CXXFLAGS, "-o", self.prog, self.objs, self.prog.LDFLAGS, added]
		else:
			return [self.prog.CC, self.prog.CFLAGS, "-o", self.prog, self.objs, self.prog.LDFLAGS, added]
	
	def execute(self, ctx):
		action.invoke(self.command(), ctx)
			
	def display(self, out):
		out.write("\t%s\n" % action.make_line(self.command()))
	

def link_lib(r):
	return [r.ress[0].AR, "rcs", r.ress[0], r.deps]

# generic recipes
gen_command(".o", ".c",   comp_c_to_o)
gen_command(".o", ".cxx", comp_cxx_to_o)
gen_command(".o", ".cpp", comp_cxx_to_o)
gen_command(".o", ".c++", comp_cxx_to_o)
gen_command(".o", ".C",   comp_cxx_to_o)


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
		

def make_objects(dir, sources, CFLAGS, CXXFLAGS):
	"""Build the objects and their recipes and return the list of objects.
	".o" are automatically added to CLEAN list."""
	check_sources(sources)
	objs = [file(recipe.gen(dir, ".o", s.path)) for s in sources]
	if CFLAGS or CXXFLAGS:
		for o in objs:
			if CFLAGS:
				o.CFLAGS = CFLAGS
			if CXXFLAGS:
				o.CXXFLAGS = CXXFLAGS
	std.CLEAN = std.CLEAN + objs
	return objs
	

def program(name, sources, LDFLAGS = None, CFLAGS = None, CXXFLAGS = None, LIBS = None):
	"""Called to build a C or C++ program."""
	
	# record prog file
	prog = file(name + EXE_SUFFIX)
	recipe.add_alias(prog, name)

	# build objects
	sources = [file(s) for s in sources]
	objs = make_objects(prog.path.parent(), sources, CFLAGS, CXXFLAGS)
	
	# build program
	recipe.ActionRecipe([prog], objs, ProgramLinker(prog, objs, contains_cxx(sources)))
	if LDFLAGS:
		prog.LDFLAGS = LDFLAGS
	if LIBS:
		post_inits.append(LibSolver(prog, LIBS))
	
	# record it
	std.ALL.append(prog)
	std.DISTCLEAN.append(prog)


def lib(name, sources, CFLAGS = None, CXXFLAGS = None, PREFIX = LIB_PREFIX, SUFFIX = LIB_SUFFIX):
	"""Called to build a static library."""
	global need_lib
	need_lib = True

	# record prog file
	lib = file(PREFIX + name + SUFFIX)
	recipe.add_alias(lib, name)
	lib.PROVIDE_PATH = lib.path.parent()
	lib.PROVIDE_LIB = name

	# build objects
	sources = [file(s) for s in sources]
	objs = make_objects(lib.path.parent(), sources, CFLAGS, CXXFLAGS)
	
	# build program
	recipe.GenActionRecipe([lib], objs, action.Invoke(link_lib))
	
	# record it
	std.ALL.append(lib)
	std.DISTCLEAN.append(lib)


def configure(c):
	if need_c:
		config.find_program("C compiler", "CC", ["gcc", "cc"], ctx = c)
	if need_cxx:
		config.find_program("C++ compiler", "CXX", ["g++", "c++"], ctx = c)
	if need_lib:
		config.find_program("library linker", "AR", ["ar"], ctx = c)
	
config.register("c", configure)
