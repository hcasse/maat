"""Classes used to represent recipes."""
import env
import os
import os.path
import sys

file_db = { }		# file database
ext_db = { }		# extension database

# ANSI coloration
NORMAL = "\033[0m"
BOLD = "\033[1m"
FAINT = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BACK_BLACK = "\033[40m"
BACK_RED = "\033[41m"
BACK_GREEN = "\033[42m"
BACK_YELLOW = "\033[43m"
BACK_BLUE = "\033[44m"
BACK_MAGENTA = "\033[45m"
BACK_CYAN = "\033[46m"
BACK_WHITE = "\033[47m"


# execution context
class CommandPrinter:
	"""Base class for printing commands."""
	
	def write(self, cmd):
		sys.stdout.write((BOLD + BLUE + "%s" + NORMAL + "\n") % cmd)

class NullStream:
	"""Stream that prints nothings."""
	
	def write(self, line):
		pass


command_stream = CommandPrinter()
null_stream = NullStream()

class Context:
	"""A context is used to configure the execution of an action."""
	cmd = command_stream
	out = sys.stdout
	err = sys.stderr


# base classes
class File(env.MapEnv):
	"""Representation of files."""
	path = None
	recipe = None
	
	def __init__(self, path):
		env.MapEnv.__init__(self, env.cenv.path, env.cenv)
		self.path = path
		file_db[path] = self
	
	def time(self):
		"""Get the last update time of the file."""
		return os.path.getmtime(self.path)
	
	def younger_than(self, f):
		"""Test if the current file is younger than the given one."""
		return self.time() < f.time()
	
	def __str__(self):
		if self.path.startswith(env.topdir) or self.path.startswith(os.getcwd()):
			return os.path.relpath(self.path)
		else:
			return self.path


def get_file(path):
	"""Get the file matching the given path in the DB. Apply
	localisation rules relative to a particular make.py if the path
	is not absolute."""
	
	# apply localisation rule
	if not os.path.isabs(path):
		path = os.path.join(env.cenv.path, path)
	path = os.path.normpath(path)
	
	# find the file
	if file_db.has_key(path):
		return file_db[path]
	else:
		return File(path)


def get_files(paths):
	"""Apply get_file on straight arguments of recipes."""
	if not paths:
		return []
	if not isinstance(paths, list):
		paths = [ paths ]
	r = []
	for p in paths:
		if not isinstance(p, File):
			p = get_file(str(p))
		r.append(p)
	return r


class Recipe:
	"""A recipe to build files."""
	ress = None
	deps = None
	env = None
	cwd = None

	def __init__(self, ress, deps = None):
		ress = get_files(ress)
		deps = get_files(deps)
		self.ress = ress
		self.deps = deps
		for f in ress:
			f.recipe = self
		self.env = env.cenv
		if hasattr(ress[0], 'cwd'):
			self.cwd = ress[0].cwd
		else:
			self.cwd = self.env.path

	def action(self, ctx):
		"""Execute the receipe."""
		pass


class FunRecipe(Recipe):
	"""A recipe that activates a function."""
	fun = None
	
	def __init__(self, fun, ress, deps):
		Recipe.__init__(self, ress, deps)
		self.fun = fun

	def action(self, ctx):
		self.fun(self.ress, self.deps, ctx)


class Ext:
	"""Represent the support for a file extension."""
	ext = None
	gens = None
	back = None
	
	def __init__(self, ext):
		self.ext = ext
		self.gens = { }
		self.backs = []
		ext_db[ext] = self

	def update(self, ext, gen):
		"""Update extension for the given generator
		and perform backward propagation."""
		self.gens[ext] = gen
		for back in self.backs:
			back.dep.update(ext, back)


def get_ext(ext):
	"""Obtain an extension."""
	if ext_db.has_key(ext):
		return ext_db[ext]
	else:
		return Ext(ext)

	
class Gen:
	"""A generator of recipe."""
	res = None
	dep = None

	def __init__(self, res, dep):
		self.res = get_ext(res)
		self.dep = get_ext(dep)

		# update back link
		self.res.backs.append(self)
		
		# update current gens
		self.dep.update(res, self)
		for ext in self.dep.gens:
			self.res.update(ext, self)

	def gen(self, res, dep):
		"""Generate a recipe to produce the given result
		from the given dependency."""
		pass


class FunGen(Gen):
	"""A simple recipe generator from a function."""
	fun = None
	
	def __init__(self, res, dep, fun):
		Gen.__init__(self, res, dep)
		self.fun = fun
	
	def gen(self, res, dep):
		return FunRecipe(self.fun, [res], [dep])


def gen(dir, rext, dep):
	"""Generate recipes to build res. A generation string is found between
	file src and res. Each intermediate file has for name the kernel of res
	(generated files will be put in the res directory). """
	
	# prepare the kernel
	b, dext = os.path.splitext(dep)
	_, n = os.path.split(b)
	kern = os.path.join(dir, n)
	
	# initialize lookup process
	if not ext_db.has_key(dext):
		raise env.ElfError("don't know how to build '%s' from '%s'" % (rext, dep))
	ext = ext_db[dext]
	prev = dep
	
	# end when dep is found
	while ext.ext <> rext:
		gen = ext.gens[rext]
		next = kern + gen.res.ext
		gen.gen(next, prev)
		prev = next
		ext = gen.res

	# return result
	return prev


class Goal(File):
	"""A goal is a file that do not match real file.
	It is always rebuilt."""

	def Goal(self, path):
		File.__init__(self, path)
	
	def younger_than(self, f):
		return True


def fix(path):
	"""Fix a path according to the current directory."""
	if isinstance(path, list):
		return [str(get_file(p)) for p in path]
	else:
		return str(get_file(path))

	
	
