"""Main module of ElfMake, a python-based build system."""
import action
import argparse
import config
import env
import imp
import os
import os.path
import recipe
import sys

# global variables
top = env.top		# top directory
todo = []			# goals to do
verbose = False		# verbose mode
do_config = False	# configuration need to be done

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


# global initializations
ALL = []
CLEAN = []
DISTCLEAN = []


# tools functions
def ext_of(p):
	return os.path.splitext(p)[1]


def make_rec(f):
	
	# apply dependencies
	if f.recipe:
		for d in f.recipe.deps:
			make_rec(d)
		
	# need update?
	update = False
	if not os.path.exists(f.path):
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
		penv = env.cenv
		env.cenv = f.recipe.env
		os.chdir(env.cenv.path)
		f.recipe.action()
		env.cenv = penv
		os.chdir(env.cenv.path)
		

def make():
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
		recipe.install_default_goals()
		try:
			global todo
			if not todo:
				todo = ["all"]
			for a in todo:
				f = recipe.get_file(a)
				make_rec(f)
		except env.ElfError, e:
			print "ERROR: %s" % e


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
	dpath = os.path.join(env.cenv.path, dir)
	path = os.path.join(dpath, "make.py")
	if not os.access(path, os.R_OK):
		raise env.ElfError("no 'make.py' in %s" % path)
	penv = env.cenv
	name = penv.name + "_" + dir
	env.cenv = env.MapEnv(name, dpath, penv)
	mod = imp.load_source(name, path)
	env.cenv.map = mod.__dict__
	env.cenv = penv
	

########## shortcut to recipe ###########

def goal(goal, deps):
	"""Define a goal that does not match an actual file.
	Making the goal executes always its action."""
	return recipe.goal(goal, deps)

def rule(ress, deps, *actions):
	"""Build a custom rule with actions."""
	return action.rule(ress, deps, actions)

def shell(cmd):
	"""Build a shell action."""
	return action.ShellAction(cmd)

def fun(f):
	"""Build a function action."""
	return action.FunAction(cmd)


######## useful functions ##########

def join(a1, a2):
	return os.path.join(a1, a2)

def isdir(path):
	return os.path.isdir(path)

def listdir(path):
	return os.listdir(path)
