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

"""Classes used to represent recipes."""
import os
import os.path
import sys

from maat import action
import maat.common as common
import maat.env as env
import maat.io as io
import maat.sign as sign

file_db = { }		# file database
ext_db = { }		# extension database


# base classes
class File(env.MapEnv):
	"""Representation of files. Several properties defines a file:
	* sticky files are files that must remains after build,
	* phony files does not represent real files and their action are
	  always performed,
	* meta files are targets that are executed only if one of their
	  dependency is updated (but are also phony),
	* hidden means that the execution is not displayed,
	* target are files that are targets,
	* goal represents phony goals displayed as entries to the user
	  (goals are also phony)."""
	
	def __init__(self, path):
		env.MapEnv.__init__(self, path.get_file() , env.cur.path, env.cur)
		self.path = path
		file_db[str(path)] = self
		self.recipe = None
		self.is_sticky = False
		self.is_phony = False
		self.is_meta = False
		self.is_hidden = False
		self.is_target = False
		self.actual_path = None
		self.is_goal = False

	def set_phony(self):
		"""Mark the file as phony, i.e. does not match a real file."""
		self.is_phony = True

	def set_meta(self):
		"""Mark a file as meta."""
		self.is_meta = True
		self.is_phony = True

	def set_target(self):
		"""Mark a file as a target."""
		self.is_target = True
	
	def set_hidden(self):
		"""Mark a file as a hidden."""
		self.is_hidden = True
	
	def set_sticky(self):
		"""Mark a file as sticky, that is, a final target (not intermediate)."""
		self.sticky = True
	
	def set_goal(self):
		"""Mark the file as a goal."""
		self.is_goal = True
		self.is_phony = True
	
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
					bpath = env.top.path / bpath
					bpath = common.Path(bpath)
					if self.path.prefixed_by(env.top.path):
						self.actual_path = bpath / self.path.relative_to(env.top.path)
					else:
						self.actual_path =  bpath / self.path
		return self.actual_path

	def __div__(self, arg):
		return self.path / str(arg)
	
	def time(self):
		"""Get the last update time of the file."""
		if self.is_goal:
			return 0
		elif self.is_meta:
			if self.recipe:
				return max([d.time() for d in self.recipe.deps])
			else:
				return 0 
		else:
			return self.actual().get_mod_time()
	
	def younger_than(self, f):
		"""Test if the current file is younger than the given one."""
		if (not f.is_meta and not f.is_phony) and not f.actual().exists():
			return True
		elif f.actual().is_dir():
			return False
		else:
			return self.time() < f.time()

	def needs_update(self):
		"""Test if the current file needs to be updated:
		* it doesn't have a recipe
		* if it doesn't exist and it is not phony
		* if the signature has changed,
		* if the dependencies are younger."""
		if self.is_goal or self.is_phony:
			#print "DEBUG: %s updated because it is phony!" % self
			return True
		elif not self.actual().exists():
			if self.recipe != None:
				#print "DEBUG: %s updated because it doesn't exist!" % self
				return True
			else:
				raise common.MaatError("don't know how to build %s?" % self.path)
		elif self.recipe == None:
			return False
		elif not sign.test(self):
			#print "DEBUG: %s updated because signature changed!" % self
			return True
		else:
			for d in self.recipe.deps:
				if d.needs_update() or self.younger_than(d):
					#print "DEBUG: %s updated because it is younger than %s!" % (self, d)
					return True
			return False

	def collect_updates(self, targets):
		"""Collect the files that needs to be updated and store them
		in the targets list."""
		if self.recipe:
			for d in self.recipe.deps:
				d.collect_updates(targets)
		if self not in targets and self.needs_update():
			targets.append(self)
			
	
	def collect_all(self, targets):
		"""Collect all the files that may be made."""
		if self.recipe and self not in targets:
			for d in self.recipe.deps:
				d.collect_all(targets)
			targets.append(self)
	
	def __str__(self):
		path = self.actual()
		if path.prefixed_by(env.topdir) or path.prefixed_by(env.curdir()):
			return str(path.relative_to_cur())
		else:
			return str(path)

	def __repr__(self):
		return self.__str__()

	def add_dep(self, dep):
		"""Add a dependency to the recipe building this file."""
		self.recipe.deps.append(dep)


def add_alias(file, name):
	"""Add an alias for the given file with the given name."""
	file_db[name] = file


def get_file(path):
	"""Get the file matching the given path in the DB. Apply
	localization rules relative to a particular make.py if the path
	is not absolute."""
	
	# apply localisation rule
	if not os.path.isabs(str(path)):
		path = env.cur.path / path
	else:
		path = common.Path(path)
	path = path.norm()
	
	# find the file
	if str(path) in file_db:
		return file_db[str(path)]
	else:
		return File(path)


def get_goal(path):
	"""Get the goal matching the given path in the DB. Apply
	localization rules relative to a particular make.py if the path
	is not absolute. If the goal cannot be found, raise a MaatError."""
	
	# apply localisation rule
	if not os.path.isabs(str(path)):
		fpath = env.cur.path / path
	else:
		fpath = common.Path(path)
	fpath = fpath.norm()
	
	# find the file
	if str(fpath) in file_db:
		return file_db[str(fpath)]
	else:
		raise common.MaatError("goal %s does not exist" % path)


def get_files(paths):
	"""Apply get_file on straight arguments of recipes."""
	if paths == None:
		return []
	if not isinstance(paths, list):
		paths = [ get_file(paths) ]
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
		self.env = env.cur
		self.cwd = ress[0].get('cwd')
		if not self.cwd:
			self.cwd = self.env.path

	def action(self, ctx):
		"""Execute the receipe."""
		pass

	def display_action(self, out):
		"""Display the action of the receipe."""
		cmds = []
		self.commands(cmds)
		for cmd in cmds:
			out.write("\t%s\n" % cmd)
	
	def commands(self, cmds):
		"""Get commands to build the recipe."""
		pass

	def display(self, out):
		out.write("%s: %s\n" % (" ".join([str(f) for f in self.ress]), " ".join([str(f) for f in self.deps])))
		self.display_action(out)
		out.write("\n")

	def signature(self):
		return ""
	
	def add_dep(self, dep):
		if dep not in self.deps:
			self.deps.append(dep)


class FunRecipe(Recipe):
	"""A recipe that activates a function."""
	fun = None
	
	def __init__(self, fun, ress, deps):
		Recipe.__init__(self, ress, deps)
		self.fun = fun

	def commands(self, cmds):
		cmds.append("<internal>")

	def action(self, ctx):
		self.fun(self.ress, self.deps, ctx)


class Ext:
	"""Represent the support for a file extension."""
	ext = None
	gens = None
	backs = None
	
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
	if ext in ext_db:
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
		
		# update forward link
		self.dep.update(res, self)
		for e in self.res.gens:
			if e not in self.dep.gens:
				self.dep.update(e, self)


	def write(self, out):
		"""Print the action of the generator."""
		pass

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

	def write(self, out):
		out.write("\t<fun>\n")
	
	def gen(self, res, dep):
		return FunRecipe(self.fun, [res], [dep])


class ActionRecipe(Recipe):
	"""A recipe that supports an action. object for generation."""
	act = None
	
	def __init__(self, ress, deps, *actions):
		Recipe.__init__(self, ress, deps)
		self.act = action.make_actions(*actions)

	def get_action(self):
		return self.act

	def action(self, ctx):
		self.get_action().execute(ctx)
	
	def commands(self, cmds):
		self.get_action().commands(cmds)

	def signature(self):
		return self.get_action().signature()


class DelayedRecipe(ActionRecipe):
	"""An action recipe extracting the action from a given function
	but just before being run."""
	ress = None
	deps = None
	fun = None
	
	def __init__(self, ress, deps, fun):
		ActionRecipe.__init__(self, ress, deps)
		self.ress = list(ress)
		self.deps = list(deps)
		self.fun = fun
		self.act = None
	
	def get_action(self):
		if self.act == None:
			self.act = action.make_actions(self.fun(self.ress, self.deps))
		return self.act
	

class ActionGen(Gen):
	"""A generator that build an action recipe from actions obtained
	from a function where target and ressource are passed to."""
	fun = None
	
	def __init__(self, res, dep, fun):
		Gen.__init__(self, res, dep)
		self.fun = fun
	
	def gen(self, res, dep):
		res = get_file(res)
		dep = get_file(dep)
		return DelayedRecipe([res], [dep], self.fun)

	def write(self, out):
		a = action.make_actions(self.fun([File(common.Path("*" + self.res.ext))], [File(common.Path("*" + self.dep.ext))]))
		cmds = []
		a.commands(cmds)
		for c in cmds:
			out.write("\t%s\n" % c)


def gen(dir, rext, dep):
	"""Generate recipes to build res. A generation string is found between
	file src and res. Each intermediate file has for name the kernel of res
	(generated files will be put in the res directory). Returns the list of
	files to build (last file having rext as extension)."""
	dir = common.Path(dir)
	dep = common.Path(dep)
	
	# prepare the kernel
	b = dep.get_base()
	dext = dep.get_ext()
	n = b.get_file()
	kern = dir / n

	# initialize lookup process
	if not ext_db.has_key(dext):
		common.script_error("don't know how to build '%s' from '%s'" % (rext, dep))
		#raise Common.MaatError("DEBUG:")
	ext = ext_db[dext]
	prev = dep
	
	# end when dep is found
	ress = []
	while ext.ext != rext:
		gen = ext.gens[rext]
		next = kern + gen.res.ext
		gen.gen(next, prev)
		ress.append(next)
		prev = next
		ext = gen.res

	# return result
	return ress


def fix(path):
	"""Fix a path according to the current directory."""
	if isinstance(path, list):
		return [str(get_file(p)) for p in path]
	else:
		return str(get_file(path))


def rule(ress, deps, *actions):
	"""Build a rule with actions."""
	return ActionRecipe(ress, deps, action.make_actions(actions)).ress[0]


def phony(goal, deps, *actions):
	"""Build a goal with the following dependencies that does not
	match a real file."""
	path = common.Path(env.cur.path) / goal
	file = get_file(str(path))
	if file.recipe:
		common.script_error("a goal named '%s' already exist!" % goal)
	else:
		file.set_phony()
		return ActionRecipe(goal, deps, *actions).ress[0]


def hidden(ress, deps, *actions):
	"""Build an hidden and phony rule, that is, a rule without action
	grouping several other rules in its dependencies.
	The result is the recipe itself."""
	a = phony(ress, deps, *actions)
	a.set_hidden()
	return a


def meta(ress, deps, *actions):
	"""Build a meta rule, that is, a rule 
	grouping several other rules in its dependencies."""
	a = phony(ress, deps, *actions)
	a.set_meta()
	return a


def goal(ress, deps, *actions):
	"""Build a goal, that is a phony target but displayed to the user
	when using -l option."""
	a = phony(ress, deps, *actions)
	a.set_goal()
	return a


def find_exact(name):
	"""Look if an entity with exactly the given name exists and return it."""
	try:
		return file_db[name]
	except KeyError as e:
		return None


def ensure_dir(path):
	"""Add a rule ensuring that the directory matching the path is created.
	Rreturn the target of the rule."""
	target = get_file(path)
	if not target.recipe:
		ActionRecipe([target], [], action.MakeDir(path))
	return target


def parse_deps(path):
	"""Scan and add to the database dependencies (without action) expressed
	with standard Makefile format. The paths in the dependency file are
	interpreted relatively to the current directory."""
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
	except IOError as e:
		pass
