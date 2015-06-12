"""Main module of ElfMake, a python-based build system."""
import action
import argparse
import config
import env
import imp
import io
import os
import os.path
import recipe
import std
import sys

# global variables
topdir = env.topdir	# top directory
todo = []			# goals to do
verbose = False		# verbose mode
do_config = False	# configuration need to be done
IS_WINDOWS = sys.platform in ['win32', 'win64', 'cygwin']
IS_UNIX = not IS_WINDOWS


# environment management
curenv = None			# current environment
curdir = None			# current directory
envstack = []

def set_env(e):
	global curenv
	global curdir
	env.cenv = e
	curenv = e
	curdir = e.path
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
parser = argparse.ArgumentParser(description = "ElfMake Builder")
parser.add_argument('free', type=str, nargs='*', metavar="goal", help="goal or Definitions")
parser.add_argument('-v',  '--verbose', action="store_true", default=False, help="verbose mode")
parser.add_argument('-c',  '--config', action="store_true", default=False, help="perform configuration")
args = parser.parse_args()
verbose = args.verbose
do_config = args.config

for a in args.free:
	p = a.split("=", 2)
	if len(p) == 1:
		todo.append(a)
	else:
		env.osenv.set(p[0], p[1])


# make process
def make_rec(f, ctx = io.Context()):
	
	# apply dependencies
	if f.recipe:
		for d in f.recipe.deps:
			make_rec(d)
		
	# need update?
	update = False
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
		std.install_default_goals()
		try:
			global todo
			if not todo:
				todo = ["all"]
			for a in todo:
				f = recipe.get_file(a)
				make_rec(f)
		except env.ElfError, e:
			ctx.print_error(e)
		except KeyboardInterrupt, e:
			sys.stderr.write("\n")
			ctx.print_error("action interrupted by user!")
		ctx.print_success("all is fine!");


############## environment management #############

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
	env.cenv.append(id, val)


def subdir(dir):
	"""Process a make.py in a subdirectory."""
	
	# look for existence of make.py
	dpath = (env.cenv.path / dir).norm()
	path = dpath / "make.py"
	if not path.can_read():
		raise env.ElfError("no 'make.py' in %s" % path)
		
	# push new environment
	name = (curenv.name + "_" + dir).replace(".", "_")
	push_env(env.MapEnv(name, dpath, curenv))
	
	# load make.py
	mod = imp.load_source(name, str(path))
	env.cenv.map = mod.__dict__
	
	# pop new environment
	pop_env()


########## shortcut to recipe ###########

def goal(goal, deps, actions = None):
	"""Define a goal that does not match an actual file.
	Making the goal executes always its action."""
	return action.goal(goal, deps, actions)

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
	return env.Path(a1) / a2

def isdir(path):
	return os.path.isdir(path)

def listdir(path = None):
	if not path:
		path = env.cenv.path
	return os.listdir(path)

def file(p):
	return recipe.get_file(p)

def path(p):
	return recipe.get_file(p).path

def paths(ps):
	return [path(p) for p in ps]

def ext_of(p):
	return os.path.splitext(p)[1]

def fix(p):
	return recipe.fix(p)

def cwd():
	return env.cenv.path

def grep(re, *cmd):
	return action.GrepAction(re, cmd)
