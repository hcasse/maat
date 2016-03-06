"""Main module of ElfMake, a python-based build system."""
import action
import argparse
import config
import env
import glob as pyglob
import imp
import inspect
import io
import os
import recipe
import services
import shutil
import subprocess
import sys


# global variables
topdir = env.topdir	# top directory
todo = []			# goals to do
verbose = False		# verbose mode
do_config = False	# configuration need to be done
do_list = False		# list the goals
do_print_db = False	# print the data base
post_inits = []		# function to call just before building


# environment management
curenv = None			# current environment
"""Current environment."""
curdir = None			# current directory
"""Current directory."""
envstack = []

def set_env(e):
	global curenv
	global curdir
	env.cenv = e
	curenv = e
	curdir = env.Path(e.path)
	e.path.set_cur()
	
def push_env(env):
	"""Push a new environment."""
	envstack.append(curenv)
	set_env(env)

def pop_env():
	"""Pop the top environment."""
	set_env(envstack.pop())

set_env(env.cenv)


# parse arguments
if not inspect.stack()[-1][1].endswith("pydoc"):

	# parse arguments
	parser = argparse.ArgumentParser(description = "ElfMake Builder")
	parser.add_argument('free', type=str, nargs='*', metavar="goal", help="goal or Definitions")
	parser.add_argument('-v',  '--verbose', action="store_true", default=False, help="verbose mode")
	parser.add_argument('-l', '--list', action="store_true", default=False, help="display available goals")
	parser.add_argument('-p', '--print-data-base', action="store_true", default=False, help="print the recipe database")


	# get arguments
	args = parser.parse_args()
	verbose = args.verbose
	do_config = False
	do_list = args.list
	do_print_db = args.print_data_base

	# parse free arguments
	for a in args.free:
		p = a.split("=", 2)
		if len(p) == 1:
			todo.append(a)
			if a == "config":
				do_config = True
		else:
			env.osenv.set(p[0], p[1])


# make process
def make_rec(f, ctx):
	
	# apply dependencies
	if f.recipe:
		for d in f.recipe.deps:
			make_rec(d, ctx)
		
	# need update?
	update = f.is_goal
	if not f.path.exists():
		if not f.recipe:
			raise env.ElfError("file '%s' does not exist and no recipe is able to build it" % f.path)
		else:
			update = True
	else:
		if f.recipe:
			for d in f.recipe.deps:
				if f.younger_than(d):
					update = True
					break
	
	# if needed, perform update
	if update:
		push_env(f.recipe.env)
		env.Path(f.recipe.cwd).set_cur()
		ctx.print_info("Making %s" % f)
		f.recipe.action(ctx)
		pop_env()


def make(ctx = io.Context()):
	"""Do nothing: only kept for backward compatibility."""
	pass


def make_work(ctx = io.Context()):
	"""Perform the real build."""
	
	# are we at the top make.py?
	if env.cenv <> env.topenv:
		return
	
	# load configuration
	config.load(do_config)
	
	# configuration action
	if do_config:
		config.make()
	
	# build action
	else:
		
		# prepare context
		for post in post_inits:
			post()
		ctx = io.Context()
		if verbose:
			ctx.command_ena = True

		# command line services
		if do_list:
			services.list_goals(ctx)
		elif do_print_db:
			services.print_db()
		
		# do the build
		else:
			try:
				global todo
				if not todo:
					todo = ["all"]
				for a in todo:
					f = recipe.get_file(a)
					make_rec(f, ctx)
				ctx.print_success("all is fine!");
			except env.ElfError, e:
				ctx.print_error(e)
			except KeyboardInterrupt, e:
				sys.stderr.write("\n")
				ctx.print_error("action interrupted by user!")


def make_at_exit():
	set_env(env.topenv)
	make_work()
	
import atexit
atexit.register(make_at_exit)


############## environment management #############

def defined(id):
	"""Test if a symbol is defined."""
	return env.cenv.is_def(id)


def get(id, default = None):
	"""Get a variable value."""
	v = env.cenv.get(id)
	if v == None:
		return default
	else:
		return v


def set(id, val):
	"""Set a variable value."""
	env.cenv.set(id, val)


def append(id, val):
	"""Append a value to a variable."""
	curenv.append(id, val)


def subdir(dir):
	"""Process a make.py in a subdirectory."""
	
	# avoid reflexivity
	if curdir == dir:
		io.DEF.print_warning("reflexive subdir ignored in %s" % curdir)
		return
	
	# look for existence of make.py
	dpath = (env.cenv.path / dir).norm()
	path = dpath / "make.py"
	if not path.can_read():
		raise env.ElfError("no 'make.py' in %s" % path)
		
	# push new environment
	name = (curenv.name + "_" + str(dir)).replace(".", "_")
	push_env(env.MapEnv(name, dpath, curenv))
	
	# load make.py
	mod = imp.load_source(name, str(path))
	env.cenv.map = mod.__dict__
	
	# pop new environment
	pop_env()
	return mod


########## shortcut to recipe ###########

def goal(goal, deps, actions = action.NULL):
	"""Define a goal that does not match an actual file.
	Making the goal executes always its action."""
	return recipe.goal(goal, deps, actions)

def rule(ress, deps, *actions):
	"""Build a custom rule with actions."""
	return action.rule(ress, deps, actions)

def shell(cmd):
	"""Build a shell action."""
	return action.ShellAction(cmd)

def fun(f):
	"""Build a function action."""
	return action.FunAction(cmd)


######## file system functions ##########

def join(a1, a2):
	"""Join two parts of a file path."""
	return env.Path(a1) / a2

def isdir(path):
	"""Test if the given path is a directory."""
	return env.Path(path).is_dir()

def listdir(path = None):
	"""List the content of a directory. If no argument is passed,
	the current directory is listed."""
	if not path:
		path = env.cenv.path
	return os.listdir(str(path))

def file(p):
	"""Convert a simple string to a ElfMake file."""
	return recipe.get_file(p)

def ext_of(p):
	"""Get extension of a path.
	Deprecated: use suffix()!"""
	return env.Path(p).get_ext()

def suffix(p):
	"""Get extension of a path or a list of paths."""
	if isinstance(p, list):
		return [env.Path(x).get_ext() for x in p]
	else:
		return env.Path(p).get_ext()

def path(p):
	"""Convert simple string to ElfMake path."""
	if p == None or p is env.Path:
		return p
	else:
		return env.Path(str(p))

def glob(re):
	"""Select content of a directory from a filesystem regular expression."""
	return pyglob.glob(re)


# compatibility functions

def mkdir(path):
	"""Build a directory if not existing, building possibly intermediate
	directories."""
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except os.error, e:
			io.DEF.print_error("cannot create '%s': %s" % (path, e))
			exit(1)

def grep(re, cmd, stdout = True, stderr = False):
	"""Perform a grep on the output of the given command."""
	return action.Grep(re, cmd, out = stdout, err = stderr)

def remove(args, ignore_error = False):
	"""Remove the given directories and files."""
	return action.Remove(args, ignore_error)	

def shell(cmd):
	"""Execute a command and return its results as a string."""
	try:
		return subprocess.check_output(cmd, shell = True).replace('\n', ' ')
	except subprocess.CalledProcessError, e:
		io.DEF.print_error("error with call to '%s': %s" % (cmd, e))
		exit(1)
