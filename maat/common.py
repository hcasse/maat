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
from maat import io

script_failed = False

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
	raise ElfError(msg)


def script_error(msg):
	"""Exit and display script error."""
	global script_failed
	io.DEF.print_error(msg)
	script_failed = True
	exit(1)


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

def filter(arg, neg = False):
	"""Build a filter according to the type of the argument:
	* string to FNFilter,
	* list to ListFilter,
	* function to FunFilter
	* regular expression to REFilter,
	* None to Yes filter.
	"""
	
	if arg == None:
		if not neg:
			return Filter()
		else:
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
