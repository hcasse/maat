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

"""Main module of Maat, a python-based build system."""
import action
import argparse
import common
import config
import datetime
import env
import glob as pyglob
import imp
import inspect
import io
import lowlevel
import os
import platform
import re
import recipe
import services
import sign
import sys


class Delegate:
	"""Delegate action (used specially for post-initialization actions)."""
	
	def perform(self, ctx):
		"""Called to perform the action."""
		pass

class FunDelegate(Delegate):
	"""Simple delegate calling a function."""
	fun = None
	
	def __init__(self, fun):
		self.fun = fun
	
	def perform(self, ctx):
		self.fun()


# global variables
version = "0.4"
topdir = env.topdir	# top directory
todo = []			# goals to do
verbose = False		# verbose mode
do_config = False	# configuration need to be done
do_list = False		# list the goals
do_print_db = False	# print the data base
post_inits = []		# Processing to call just before building
maat_dir = env.top.path / ".maat"
"""Temporary path for Maat files"""

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
	curdir = common.Path(e.path)
	e.path.set_cur()
	
def push_env(env):
	"""Push a new environment."""
	envstack.append(curenv)
	set_env(env)

def pop_env():
	"""Pop the top environment."""
	set_env(envstack.pop())

set_env(env.curenv)


# parse arguments
if not inspect.stack()[-1][1].endswith("pydoc"):

	# parse arguments
	parser = argparse.ArgumentParser(description = "Maat Builder")
	parser.add_argument('free', type=str, nargs='*', metavar="goal", help="goal or Definitions")
	parser.add_argument('-v',  '--verbose', action="store_true", default=False, help="verbose mode")
	parser.add_argument('-l', '--list', action="store_true", default=False, help="display available goals")
	parser.add_argument('-V', '--version', action="store_true", default=False, help="display the current version")
	parser.add_argument('-p', '--print-data-base', action="store_true", default=False, help="print the recipe database")

	# get arguments
	args = parser.parse_args()
	if args.version:
		print \
"""Maat V%s\nCopyright (c) 2016 H. Casse <hugues.casse@laposte.net>
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.""" % version
		exit(0)
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
			env.root.set(p[0], p[1])

	# load configuration
	config.load(do_config)
	
	# predefined variables
	d = datetime.date.today()
	env.root.TODAY = datetime.date.today().isoformat()
	env.root.SYSTEM = platform.system()
	env.root.MACHINE = platform.machine()
	env.root.PLATFORM = "%s-%s" % (env.root.PLATFORM, env.root.MACHINE)


# make process
def collect_todo(f, todo):
	"""Compute the list of goals to build."""
	cnt = 0
	if f.recipe:
		for d in f.recipe.deps:
			collect_todo(d, todo)
	update = f.is_goal
	if not update:
		if not f.actual().exists():
			if not f.recipe:
				common.error("file '%s' does not exist and no recipe is able to build it" % f.path)
			else:
				print "DEBUG: %s does not exist!" % f
				update = True
		else:
			if f.recipe:
				for d in f.recipe.deps:
					if not d.actual().exists() or f.younger_than(d):
						print "DEBUG: %s to do because of %s" % (f, d)
						update = True
						break
			if not update and not sign.test(f):
				update = True
				print "DEBUG: %s to do because of signature change!" % f
	if update and not f in todo:
		todo.append(f)


def make_todo(todo, ctx):
	cstat = 0
	tstat = len(todo)	
	for f in todo:
		
		# ensure the target directory exists
		for r in f.recipe.ress:
			ppath = r.actual().parent()
			if not ppath.exists():
				try:
					os.makedirs(str(ppath))
				except error, e:
					common.error(env.ElfError(str(e)))
		
		# perform the recipe action
		push_env(f.recipe.env)
		common.Path(f.recipe.cwd).set_cur()
		if f.is_goal or not f.is_phony:
			ctx.print_info("[%3d%%] Making %s" % (cstat * 100 / tstat, f.path.relative_to(env.top.path)))
		f.recipe.action(ctx)
		pop_env()
		sign.record(f)
		cstat = cstat + 1


def make(ctx = io.Context()):
	"""Do nothing: only kept for backward compatibility."""
	pass


def make_work(ctx = io.Context()):
	"""Perform the real build."""
	
	# are we at the top make.py?
	if env.cenv <> env.top:
		return

	# prepare context
	ctx = io.Context()
	if verbose:
		ctx.command_ena = True

	# post-initializations
	for post in post_inits:
		post.perform(ctx)
	
	# configuration action
	if do_config:
		config.make()
	
	# build action
	else:
		
		# command line services
		if do_list:
			services.list_goals(ctx)
		elif do_print_db:
			services.print_db()
		
		# do the build
		else:
			try:
				sign.load(ctx)
				global todo
				if not todo:
					todo = ["all"]
				targets = []
				for a in todo:
					collect_todo(recipe.get_file(a), targets)
					make_todo(targets, ctx)
				ctx.print_success("all is fine!");
				sign.save(ctx)
			except common.MaatError, e:
				ctx.print_error(e)
			except KeyboardInterrupt, e:
				sys.stderr.write("\n")
				ctx.print_error("action interrupted by user!")


def make_at_exit():
	if not common.script_failed:
		set_env(env.top)
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
		common.script_error("no 'make.py' in %s" % path)
		
	# push new environment
	name = (curenv.name + "_" + str(dir)).replace(".", "_")
	push_env(env.ScriptEnv(name, dpath, curenv, { }))
	
	# load make.py
	mod = imp.load_source(name, str(path))
	env.cenv.map = mod.__dict__
	
	# pop new environment
	pop_env()
	return mod



def concat(s1, s2):
	"""Join two values, using the best type: list if one is a least,
	string else.."""
	if not s1:
		return s2
	elif not s2:
		return s1
	elif isinstance(s1, list):
		if isinstance(s2, list):
			return s1 + s2
		else:
			return s1 + [s2]
	elif isinstance(s2, list):
		return [s1] + s2
	else:
		return str(s1) + " " + str(s2)


def list_of(args):
	"""Build a list from the given argument."""
	if not args:
		return []
	elif isinstance(args, list):
		return args
	else:
		return [args]


ESCAPE_RE = re.compile("[() \t$'\"\[\]]")
def escape(str):
	"""Escape of the given string to be passed in command line
	of the current shell."""
	global ESCAPE_RE
	return ESCAPE_RE.sub(lambda m: "\\" + m.group(), str)
		

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

def gen_action(res, dep, fun):
	"""Build a generator that call the given function to get the real
	action for the receipe. Function is called with results as first
	parameter and dependencies as second parameter."""
	recipe.ActionGen(res, dep, fun)

def gen_command(res, dep, fun):
	"""Build a generator invoking a command produced by the command function.
	The passed function must take as parameter the recipe this action is launched for.
	This recipe provides details of the implemented rule."""
	recipe.ActionGen(res, dep, lambda r, d: action.Invoke(fun(r, d)))


######## file system functions ##########

def join(a1, a2):
	"""Join two parts of a file path."""
	return common.Path(a1) / a2

def isdir(path):
	"""Test if the given path is a directory."""
	return common.Path(path).is_dir()

def listdir(path = None):
	"""List the content of a directory. If no argument is passed,
	the current directory is listed."""
	if not path:
		path = env.cenv.path
	return os.listdir(str(path))

def file(p):
	"""Convert a simple string to a Maat file."""
	return recipe.get_file(p)

def ext_of(p):
	"""Get extension of a path.
	Deprecated: use suffix()!"""
	return env.Path(p).get_ext()

def suffix(p):
	"""Get extension of a path or a list of paths."""
	if isinstance(p, list):
		return [common.Path(x).get_ext() for x in p]
	else:
		return common.Path(p).get_ext()

def path(p):
	"""Convert simple string to Maat path."""
	if p == None or p is common.Path:
		return p
	else:
		return common.Path(str(p))

def glob(re):
	"""Select content of a directory from a filesystem regular expression."""
	return pyglob.glob(re)

def temp(name = None):
	"""Obtain a temporary directory, usually in .maat  directory
	of building directory. If a name is given, a sub-directory from
	.maat is provided (and built if necessary)."""
	p = maat_dir
	if name:
		p = p / name
	if not p.exists():
		mkdir(str(p))
	return p


######## compatibility functions ##########

mkdir = lowlevel.makedir

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

def move(files, target):
	"""Create an action moving files to the given target."""
	return action.Move(files, target)

def hidden(actions):
	"""Create an action that perform the parameter action without
	displaying the command."""
	return action.Hidden(actions)

def show(msg):
	"""Print to the screen the given message."""
	return action.Print(msg)

def makedir(path):
	"""Build a directory."""
	return action.Makedir(path)

	
