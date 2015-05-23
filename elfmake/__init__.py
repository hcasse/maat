import argparse
import config
import env
import os
import os.path
import recipe
import subprocess
import sys

# global variables
top = env.top		# top directory
all = []			# all goals
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
			raise ElfError("file '%s' does not exist and no recipe is able to build it" % f.path)
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
		f.recipe.action()


def make():
	"""Perform the real build."""
	config.load(do_config)
	if do_config:
		config.make()
	else:
		try:
			for a in all:
				f = recipe.get_file(a)
				make_rec(f)
		except ElfError, e:
			print "ERROR: %s" % e


def make_line(args):
	line = ""
	for a in args:
		if isinstance(a, list):
			line = line + make_line(a)
		else:
			line = line + " " + env.to_string(a)
	return line


def invoke(*cmd):
	"""Launch the given command in the current shell."""
	line = make_line(cmd)
	print line
	r = subprocess.call(line, shell=True)
	if r <> 0:
		raise ElfError("build failed")


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

#def env(id, default = ""):
#	"""Get environment variable value."""
#	return os.getenv(id, default)
