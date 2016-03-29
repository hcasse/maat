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

import os
import os.path
import shutil

from maat import *
import action
import common
import env
import std


class Install(action.Action):
	"""Build a simple file installer. Arguments are:
	* file -- file to install,
	* dir -- directory path,
	* name -- name for user display."""
	
	def __init__(self, file, dir, name):
		self.file = file
		self.dir = dir
		self.name = name
	
	def install_path(self):
		to = self.file.INSTALL_TO
		if not to:
			to = self.dir
		return (env.topenv.path / self.file.PREFIX / to)
	
	def execute(self, ctx):
		try:
			ctx.print_action(self.signature())
			path = self.install_path()
			lowlevel.makedir(path)
			shutil.copyfile(str(self.file), str(path / self.file.path.get_file()))
			ctx.print_action_success()
		except IOError,e :
			msg = str(e)
			ctx.print_action_failure(msg)
			common.error("installation failed")

	def display(self, out):
		out.write("\t%s\n" % self.signature())
	
	def signature(self):
		return "install %s %s to %s" % (self.name, self.file.path.relative_to_top(), self.install_path().relative_to_top())


class InstallData(action.Action):
	"""Install data files."""
	
	def __init__(self, data, discard = None):
		self.data = data
		self.discard = discard
	
	def display(self, out):
		out.write("\t%s\n" % self.signature())
	
	def install_path(self):
		"""Compute install path."""
		to = self.data.INSTALL_TO
		if to:
			to = path(to)
		else:
			PROJECT = self.data.PROJECT
			to = path(self.data.PREFIX) / "share" / PROJECT
		return to
	
	def signature(self):
		return "install data %s to %s discarding %s" % (self.data, self.install_path(), self.discard)

	def execute(self, ctx):
		to = self.install_path()
		lowlevel.makedir(to)
		try:
			ctx.print_action(self.signature())
			if not self.data.path.is_dir():
				shutil.copyfile(str(self.data), str(to / self.data.path.get_file()))
			else:
				for dir, dirs, files in os.walk(str(self.data)):
					
					# create directory
					org_dpath = path(dir)
					tgt_dpath = to / dir
					if not tgt_dpath.exists():
						os.mkdir(str(tgt_dpath))
					
					# copy files
					for file in files:
						org_fpath = org_dpath / file
						tgt_fpath = to / dir / file
						if not self.discard.accept(org_fpath):
							shutil.copyfile(str(org_fpath), str(tgt_fpath))
					
					# copy directories
					for d in dirs:
						org_path = org_dpath / d
						if self.discard.accept(org_path):
							dirs.remove(d)
					
			ctx.print_action_success()
		except (IOError, OSError) as e:
			msg = str(e)
			ctx.print_action_failure(msg)
			env.error("installation failed")


def dist_name():
	"""Build the name of the directory to build a distribution."""
	DIST = env.topenv.DIST
	if not DIST:
		PROJECT = env.topenv.PROJECT
		if not PROJECT:
			common.script_error("no project name defined!")
		DIST = PROJECT
		VERSION = env.topenv.VERSION
		if VERSION:
			DIST = DIST + "-" + VERSION
		else:
			DIST = DIST + "-" + env.topenv.TODAY
		DIST = DIST + "-" + env.topenv.PLATFORM
	return DIST
	

class SetupDist(action.Action):
	"""Action called to setup the distribution building."""

	def __init__(self):
		pass

	def execute(self, ctx):
		p = temp(dist_name())
		env.topenv.PREFIX = p
		lowlevel.makedir(p)
	
	def display(self, out):
		out.write("\t%s\n" % self.signature)
	
	def signature(self):
		return "setup dist"
	

def program(prog):
	"""Install a program in, if provided,  the to directory."""
	target = file(prog.path.make("install-"))
	recipe.phony([target], [prog], Install(prog, "bin", "program"))
	std.INSTALL.append(target)


def lib(lib):
	"""Install a static library."""
	target = file(lib.path.make("install-lib-"))
	recipe.phony([target], [lib], Install(lib, "lib", "library"))
	std.INSTALL.append(target)


def dlib(lib):
	"""Install a dynamic library."""
	target = file(lib.path.make("install-dlib-"))
	recipe.phony([target], [lib], Install(lib, "lib", "dynamic libary"))
	std.INSTALL.append(target)


def data(data, to = "", discard = None):
	"""Install data: performs just a copy for a plain file, performs
	a recursive copy for a directory. If discard is given, it contains
	files to discard from the installation.
	
	Discard may a string (a file system regular expression), a list
	of paths or a function that must takes as parameter a path and
	return true (keep) or false (discard)."""

	# check if the path can be computed
	data = recipe.get_file(data)
	if not data.INSTALL_TO and not data.PROJECT:
		common.script_error("to install data, one of PROJECT or INSTALL_TO is required!")

	# build the rule
	data = recipe.get_file(data)
	target = file(data.path.make("install-data-"))
	action = InstallData(data, common.filter(discard, True))
	recipe.phony([target], [data], action)
	std.INSTALL.append(target)


