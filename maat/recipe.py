"""Classes used to represent recipes."""
import env
import action
import io
import os
import os.path
import sys

file_db = { }		# file database
ext_db = { }		# extension database


# base classes
class File(env.MapEnv):
	"""Representation of files."""
	path = None
	recipe = None
	is_goal = False
	is_target = False
	is_sticky = False
	is_phony = False
	actual_path = None
	
	def __init__(self, path):
		env.MapEnv.__init__(self, path.get_file() , env.cenv.path, env.cenv)
		self.path = path
		file_db[str(path)] = self

	def set_phony(self):
		"""Mark the file as phony, i.e. does not match a real file."""
		self.is_phony = True

	def set_goal(self):
		"""Mark a file as a goal."""
		self.is_goal = True
		self.is_phony = True
	
	def set_target(self):
		"""Mark a file as a target."""
		self.is_target = True
	
	def set_sticky(self):
		"""Mark a file as sticky, that is, a final target (not intermediate)."""
		self.sticky = True

	def actual(self):
		"""Get the actual path of the file. For target file, this path
		is relative to BPATH variable."""
		if not self.actual_path:
			if not self.is_target:
				self.actual_path = self.path
			else:
				bpath = self["BPATH"]
				if not bpath:
					self.actual_path = self.path
				else:
					bpath = env.topenv.path / bpath
					bpath = env.Path(bpath)
					if self.path.prefixed_by(env.topenv.path):
						self.actual_path = bpath / self.path.relative_to(env.topenv.path)
					else:
						self.actual_path =  bpath / self.path
		return self.actual_path

	def __div__(self, arg):
		return self.path / str(arg)
	
	def time(self):
		"""Get the last update time of the file."""
		if self.is_phony:
			if self.recipe:
				return max([d.time() for d in self.recipe.deps])
			else:
				return 0 
		else:
			return self.actual().get_mod_time()
	
	def younger_than(self, f):
		"""Test if the current file is younger than the given one."""
		if self.is_phony:
			return True
		else:
			return self.time() < f.time()
	
	def __str__(self):
		path = self.actual()
		if path.prefixed_by(env.topdir) or path.prefixed_by(env.curdir()):
			return str(path.relative_to_cur())
		else:
			return str(path)


def add_alias(file, name):
	"""Add an alias for the given file with the given name."""
	file_db[name] = file


def get_file(path):
	"""Get the file matching the given path in the DB. Apply
	localisation rules relative to a particular make.py if the path
	is not absolute."""
	
	# apply localisation rule
	if not os.path.isabs(str(path)):
		path = env.cenv.path / path
	else:
		path = env.Path(path)
	path = path.norm()
	
	# find the file
	if file_db.has_key(str(path)):
		return file_db[str(path)]
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
			p = get_file(p)
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
			f.is_target = True
		self.env = env.cenv
		self.cwd = ress[0].get('cwd')
		if not self.cwd:
			self.cwd = self.env.path

	def action(self, ctx):
		"""Execute the receipe."""
		pass

	def display_action(self, out):
		pass

	def display(self, out):
		out.write("%s: %s\n" % (" ".join([str(f) for f in self.ress]), " ".join([str(f) for f in self.deps])))
		self.display_action(out)
		out.write("\n")



class FunRecipe(Recipe):
	"""A recipe that activates a function."""
	fun = None
	
	def __init__(self, fun, ress, deps):
		Recipe.__init__(self, ress, deps)
		self.fun = fun

	def display_action(self, out):
		out.write("\t<internal>\n")

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
	dir = env.Path(dir)
	dep = env.Path(dep)
	
	# prepare the kernel
	b = dep.get_base()
	dext = dep.get_ext()
	#b, dext = os.path.splitext(dep)
	#_, n = os.path.split(b)
	n = b.get_file()
	kern = dir / n	#os.path.join(dir, n)

	# initialize lookup process
	if not ext_db.has_key(dext):
		io.DEF.print_error("don't know how to build '%s' from '%s'" % (rext, dep))
		exit(1)
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


def fix(path):
	"""Fix a path according to the current directory."""
	if isinstance(path, list):
		return [str(get_file(p)) for p in path]
	else:
		return str(get_file(path))


class ActionRecipe(Recipe):
	"""A recipe that supports an action. object for generation."""
	act = None
	
	def __init__(self, ress, deps, *actions):
		Recipe.__init__(self, ress, deps)
		self.act = action.make_actions(*actions)

	def action(self, ctx):
		self.act.execute(ctx)
	
	def display_action(self, out):
		self.act.display(out)


class GenActionRecipe(ActionRecipe):
	"""Recipe with action supporting generation."""
	
	def __init__(self, ress, deps, actions):
		ActionRecipe.__init__(self, ress, deps, actions)
		self.act = self.act.instantiate(self)


class ActionGen(Gen):
	"""A recipe generator supporting simple actions."""
	action = None
	
	def __init__(self, res, dep, action):
		Gen.__init__(self, res, dep)
		self.action = action
		
	def gen(self, res, dep):
		return GenActionRecipe([res], [dep], self.action)
	

def rule(ress, deps, *actions):
	"""Build a rule with actions."""
	ActionRecipe(ress, deps, make_actions(actions))


def goal(goal, deps, actions = action.Action()):
	"""Build a goal with the following dependencies."""
	path = env.Path(env.cenv.path) / goal
	file = get_file(str(path))
	if file.recipe:
		raise env.ElfError("a goal already named '%s' already exist!" % goal)
	else:
		file.set_goal()
		file.recipe = ActionRecipe(goal, deps, actions)
		return


def find_exact(name):
	"""Look if an entity with exactly the given name exists and return it."""
	try:
		return file_db[name]
	except KeyError, e:
		return None

	
