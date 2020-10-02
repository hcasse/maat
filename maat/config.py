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

"""Maat module providing configuration classes."""
import imp
import os.path
import sys

import maat
from maat import common
from maat import env
from maat import io
from maat import action
from maat import recipe

# public variables
GOAL = None
"""Goal corresponding to the configuration"""

# configuration state
config_list = []	# list of configuration modules
updated = False
loaded = False
configured = False
win_list = ['win32', 'win64', 'cygwin']
comments = { }


# convenient functions
def host():
	"""Return a string identifying the host platform.""" 
	info = os.uname()
	return "%s %s %s %s" % (info[0], info[1], info[2], info[4])


def register(config):
	"""Function used to register a configuration."""
	if config not in config_list:
		config_list.append((config))


def set(id, val):
	"""Set the value to the given identifier in the configuration environment."""
	env.conf.map[id] = val


def set_if(id, fun):
	"""Set a configuration item if it is not set. To obtain the value, call the function fun."""
	if not is_set(id):
		env.conf.set(id, fun())
		global updated
		updated = True


def set_comment(id, com):
	"""Set a comment associated with a configuration variable."""
	comments[id] = com


def setup():
	"""Set up the configuration from scratch."""

	# look for a build path
	bpath = env.root["BPATH"]
	if bpath:
		env.conf["BPATH"] = bpath

	# builtin configuration
	global win_list
	set_if("IS_WINDOWS", lambda : sys.platform in win_list)
	set_if("IS_UNIX", lambda : sys.platform not in win_list)


def load(do_config):
	"""Called to load the configuration file.
	
	do_config informs it is a load for configuration and
	therefore do not alert user for incompatibility."""
	global loaded
	
	if loaded:
		return
	
	cpath = env.topdir / "config.py"
	if not cpath.exists():
		setup()
	else:
		
		# load the configuration
		mod = imp.load_source('config.py', str(cpath))
		env.conf.map = mod.__dict__
		
		# check host compatibility
		try:
			h = env.conf.map['ELF_HOST']
			if h != None and h != host():
				
				# warn if we are not in configuration
				if not do_config:
					print("WARNING: config.py for a different host found!\nReconfigure it with ./make.py config")
					
				# reset configuration else
				else:
					env.conf.map = { }

		except KeyError as e:
			pass
	
	loaded = True


def save():
	"""Save the configuration to the disk."""
	env.conf.set("ELF_HOST", host())
	f = open(str(env.topdir / 'config.py'), "w")
	f.write("# generated by Maat\n")
	f.write("# You're ALLOWED modifying this file to tune or complete your configuration\n")
	for k in env.conf.map:
		if not k.startswith("__"):
			com = None
			if comments.has_key(k):
				com = comments[k]
			if com != None and "\n" in com:
				f.write("# %s\n" % com.replace("\n", "\n# "))
			f.write("%s = %s" % (k, repr(env.conf.map[k])))
			if com != None and "\n" not in com:
				f.write("\t# %s" % com)
			f.write("\n")
	f.close()
	
	
def is_set(id):
	"""Test if a configuration item is set (exists, not None, not empty string, not 0)."""
	try:
		return env.conf.map[id]
	except KeyError as e:
		return False 


def begin():
	"""Begin the configuration."""
	if configured:
		return
	if not loaded:
		load(False)
	configured = True

	
def make(ctx = io.Context()):
	"""Build a configuration."""
	
	# set up basis
	setup()

	# launch module configuration
	todo = list(config_list)
	for conf in config_list:
		conf.result = None
	while todo:
		conf = todo.pop()
		if conf.result == None:
			if conf.done():
				conf.result = True
			else:
				conf.perform(ctx)
	
	# if needed, output the configuration file
	if updated:
		save()


# install config goal
GOAL = recipe.goal("config", [], action.FunAction(make))
GOAL.DESCRIPTION = "build configuration"


# Config class
class Config(recipe.File):
	"""Configuration node: it is responsible for performing a configuration
	step and, if successful, chain with sub-configuration items."""
	name = None
	blocking = False
	deps = None
	result = None
	
	def __init__(self, name, blocking = False, deps = []):
		recipe.File.__init__(self, common.Path("config/%s" % name))
		self.name = name
		self.blocking = blocking
		self.deps = []
		self.result = None

	def succeed(self, msg = None):
		"""Call to record success of the configuration."""
		self.result = True
		self.ctx.print_action_success(msg)
		global updated
		updated = True

	def fail(self, msg = None):
		"""Called to record a failed configuration."""
		self.result = False
		if self.blocking:
			common.error("cannot configure %s: %s" % self.name, msg)
		else:
			self.ctx.print_action_failure(msg)

	def perform(self, ctx):
		"""Call to perform the configuration of this item and of its
		dependent configuration item."""
		self.ctx = ctx
		
		# look in dependencies
		for dep in self.deps:
			if dep.result == None:
				dep.perform(ctx)
			if not dep.result:
				fail("missing dependency on %s" % dep.name)
		
		# perform self configuration
		self.configure(ctx)
			
	def configure(self, ctx):
		"""Perform configuration for this item. Must call one of fail()
		or succeed() to record configuration result."""
		self.fail()
	
	def done(self):
		"""Test if the configuration is already available."""
		return False


class VarConfig(Config):
	
	def __init__(self, name, var, blocking = False, deps = []):
		Config.__init__(self, name, blocking, deps)
		self.var = var

	def done(self):
		return env.conf.is_configured(self.var)
	
	def needs_update(self):
		return not self.done()


class FindProgram(VarConfig):
	"""Find the path of a program and display associated message.
	
	The label is displayed during the look-up, one of progs
	is look in the given paths including system path if syspath is True.
	If sysfirst is true, look system paths first.
	
	If the variable var already exists and is set, do nothing.
	Else store the result in configuration environment."""

	def __init__(self, label, var, progs, paths = [], syspath = True, sysfirst = True):
		VarConfig.__init__(self, label, var)
		self.progs = maat.list_of(progs)
		self.paths = paths
		self.syspath = syspath
		self.sysfirst = sysfirst

	def configure(self, ctx):

		# include system paths
		if self.syspath:
			spaths = os.getenv("PATH").split(os.pathsep)
			if self.sysfirst:
				lpaths = spaths + self.paths
			else:
				lpaths = self.paths + spaths
		else:
			lpaths = self.paths
		
		# lookup
		ctx.print_action(self.name)
		fpath = None
		for path in lpaths:
			for prog in self.progs:
				ppath = os.path.join(path, prog)
				if os.access(ppath, os.X_OK):
					if path in self.paths:
						fpath = ppath
					else:
						fpath = prog
					break
		
		# process result
		env.conf.set(self.var, fpath)
		if fpath:
			self.succeed("found: %s" % fpath)
		else:
			self.fail("not found")


def find_program(label, var, progs, paths = [], syspath = True, sysfirst = True):
	"""Add a configuration node looking for a program with the given label,
	setting the variable var, looking for program in progs and in the given
	paths. If syspath is set to False, do not look in system path. If sysfirst
	is set to False, do not first look in system paths."""
	register(FindProgram(label, var, progs, paths, syspath, sysfirst))
