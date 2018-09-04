#	MAAT common facilities
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

"""This module provides several facilities useful for other modules."""

import fnmatch
import os
import sys
import time as pytime

import io
import sign

script_failed = False
topenv = None
root = sys.modules['__main__']

# Error Management

class MaatError(Exception):
	"""Exception when an error happen during building phase."""
	msg = None
	
	def __init__(self, msg):
		self.msg = msg
	
	def __repr__(self):
		return self.msg

	def __str__(self):
		return self.msg


def error(msg):
	"""Raise a Maat exception with the given error message."""
	raise MaatError(msg)


def script_error(msg):
	"""Exit and display script error."""
	global script_failed
	io.DEF.print_error(msg)
	script_failed = True
	exit(1)


# path mangement
class Path:
	"""Base class of objects representing files.
	Mainly defined by its path. Provide several facilities like "/"
	overload."""
	path = None
	
	def __init__(self, path):
		if isinstance(path, Path):
			self.path = path.path
		else:
			self.path = str(path)
	
	def __div__(self, arg):
		return Path(os.path.join(self.path, str(arg)))
	
	def __add__(self, ext):
		return Path(self.path + ext)

	def __str__(self):
		return self.path
	
	def is_empty(self):
		return self.path == ""
	
	def exists(self):
		"""Test if the file matching the path exists."""
		return os.path.exists(self.path)

	def get_mod_time(self):
		return os.path.getmtime(self.path)
		
	def prefixed_by(self, path):
		return self.path.startswith(str(path))

	def relative_to_cur(self):
		return Path(os.path.relpath(self.path))

	def relative_to_top(self):
		return Path(os.path.relpath(str(self.path), str(topenv.path)))

	def relative_to(self, path):
		return Path(os.path.relpath(self.path, path.path))

	def norm(self):
		"""Build a normalized of version of current path."""
		return Path(os.path.normpath(self.path))

	def set_cur(self):
		"""Set this directory as the current directory."""
		os.chdir(self.path)
	
	def is_dir(self):
		"""Test if the path is a directory."""
		return os.path.isdir(self.path)
	
	def can_read(self):
		"""Test if the path design a file/directory that can be read."""
		return os.access(self.path, os.R_OK)

	def parent(self):
		"""Get the parent directory of the current directory."""
		return Path(os.path.dirname(self.path))
	
	def glob(self, re = "*"):
		return glob.glob(os.path.join(self.path, re))

	def get_ext(self):
		"""Get extension of a path."""
		return os.path.splitext(self.path)[1]
	
	def get_base(self):
		"""Get the base of path, i.e., the path without extension."""
		return Path(os.path.splitext(self.path)[0])
	
	def get_file(self):
		"""Get file part of the path."""
		return os.path.split(self.path)[1]

	def make(self, pref = "", suff = ""):
		return self.parent() / (pref + self.get_base().get_file() + suff)

	def __iter__(self):
		if not self.is_dir():
			script_error("%s is not a directory" % self.path)
		else:
			return iter([Path(p) for p in os.listdir(self.path)])


# Filters
class Filter:
	"""A filter provide a way to test a path for a specific property."""

	def accept(self, path):
		"""Must test the given path and return True if accepted,
		False else."""
		return True

	def __str__(self):
		return "true"

class DenyFilter(Filter):
	"""Filter that refuse any input."""
	
	def accept(self, path):
		return False

	def __str__(self):
		return "false"

class ListFilter(Filter):
	"""Only accept paths in the given list."""
	
	def __init__(self, list):
		self.list = [str(i) for i in list]
	
	def accept(self, path):
		return str(path) in self.list

	def __str__(self):
		return "one of [" + ", ".join(self.list) + "]"

class FNFilter(Filter):
	"""Filter supporting Unix FileName matching."""
	
	def __init__(self, pattern):
		self.pattern = pattern
	
	def accept(self, path):
		return fnmatch.fnmatch(str(path), self.pattern)

	def __str__(self):
		return pattern

class REFilter(Filter):
	"""Filter based on regular expressions."""
	
	def __init__(self, re):
		self.re = re
	
	def accept(self, path):
		return self.re.match(str(path))

	def __str__(self):
		return str(self.re)

class FunFilter(Filter):
	"""Filter based on a function taking a path as parameter
	and returning True to accept, False to decline."""
	
	def __init__(self, fun):
		self.fun = fun
	
	def accept(self, path):
		return self.fun(path)

	def __str__(self):
		return "fun"

def filter(arg):
	"""Build a filter according to the type of the argument:
	* string to FNFilter,
	* list to ListFilter,
	* function to FunFilter
	* regular expression to REFilter,
	* None, True to Yes filter,
	* False to DenyFilter.
	"""
	
	if arg == None:
		return Filter()
	elif arg == True:
		return Filter()
	elif arg == False:
		return DenyFilter()
	elif isinstance(arg, Filter):
		return arg
	elif isinstance(arg, string):
		return FnFilter(arg)
	elif isinstance(arg, list):
		return ListFilter(arg)
	elif isinstance(arg, re.RegexObject):
		return REFilter(arg)
	elif hasattr(arg, "__call___"):
		return FunFilter(arg)
	else:
		script_error("cannot make a filter from %s" % arg)

class NotFilter(Filter):
	"""Filter reversing the result of a test. Filter is processed
	using filter() function."""
	
	def __init__(self, f):
		self.filter = filter(f)
	
	def accept(self, path):
		return not self.filter.accept(path)

	def __str__(self):
		return "not " + str(self.filter)

class AndFilter(Filter):
	"""Filter performing AND of all given filters.
	Notice that the arguments are passed to filter() call."""
	
	def __init__(self, *filters):
		self.filters = [filter(f) for f in filters]
	
	def accept(self, path):
		for f in self.filters:
			if not f.accept(path):
				return False
		return True

	def __str__(self):
		return "(" + " and ".join([str(f) for f in self.filters]) + ")"

class OrFilter(Filter):
	"""Filter performing OR of all given filters.
	Notice that the arguments are passed to filter() call."""
	
	def __init__(self, *filters):
		self.filters = [filter(f) for f in filters]
	
	def accept(self, path):
		for f in self.filters:
			if f.accept(path):
				return True
		return False

	def __str__(self):
		return "(" + " or ".join([str(f) for f in self.filters]) + ")"


def format_duration(d):
	"""Format a duration (in s) for user display."""
	if d >= 1:
		return "%10.2fs" % d
	else:
		return "%6.2fms" % (d * 1000)


def time():
	"""Get the current time (in s)."""
	return pytime.time()


def lookup_prog(progs, paths):
	"""Lookup for a program corresponding to one of the list
	in the given list of paths and return it. If the program cannot
	be found, return None."""
	for path in paths:
		for prog in progs:
			ppath = os.path.join(path, prog)
			if os.access(ppath, os.X_OK):
				return ppath
	return None
