"""Classes used to represent recipes."""
import env
import os
import os.path

file_db = { }		# file database
ext_db = { }		# extension database

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
		cpath = env.cenv.path
		if self.path.startswith(cpath):
			return self.path[len(cpath) + 1:]
		elif self.path.startswith(top):
			p = cpath[len(top):]
			n = p.count('/')
			return "../" * n + self.path[len(top) + 1:]
		else:
			return self.path


def get_file(path):
	"""Get the file matching the given path in the DB. Apply
	localisation rules relative to a particular make.py if the path
	is not absolute."""
	path = os.path.normpath(path)
	
	# apply localisation rule
	if not os.path.isabs(path):
		path = os.path.join(env.cenv.path, path)
	
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

	def __init__(self, ress, deps = None):
		self.ress = get_files(ress)
		self.deps = get_files(deps)
		for f in self.ress:
			f.recipe = self
		self.env = env.cenv

	def action(self):
		"""Execute the receipe."""
		pass


class FunRecipe(Recipe):
	"""A recipe that activates a function."""
	fun = None
	
	def __init__(self, fun, ress, deps):
		Recipe.__init__(self, ress, deps)
		self.fun = fun

	def action(self):
		self.fun(self.ress, self.deps)


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


def goal(goal, deps):
	"""Build a goal with the following dependencies."""

	# look for an existing goal
	path = os.path.join(env.cenv.path, goal)
	try:
		file = file_db[path]
		if not isinstance(file, Goal):
			raise env.ElfError("a goal already named '%s' already exist!" % goal)
		elif file.recipe:
			file.recipe.deps.append(deps)
			return
	except KeyError, e:
		file = Goal(path)
	
	# make the recipe
	file.recipe = Recipe(goal, deps)
	

def install_default_goals():
	"""Install default goals."""
	path = os.path.join(env.cenv.path, "all")
	if not file_db.has_key(path):
		goal("all", env.cenv.get("ALL"))
	
