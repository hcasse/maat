#	MAAT environment module
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

"""Implementation of environment in Maat."""
import glob
import os
import os.path
import sys

import common



topdir = common.Path(os.getcwd())	# top directory

def curdir():
	"""Get the current working directory."""
	return common.Path(os.getcwd())


# environments
class Env:
	"""Base class of environments."""
	path = ""
	name = ""
	
	def __init__(self, name, path = topdir):
		self.name = name
		self.path = path

	def get(self, id, default = None):
		"""Get an identifier looking in the current environment
		or in the parent environment."""
		return default
	
	def set(self, id, val):
		"""Set a value to an identifier in the current environment."""
		pass
	
	def is_def(self, id):
		"""Test if the identifier is defined in the current environment
		or in one of its parents."""
		return False
	
	def append(self, id, val):
		"""Append the given value to an existing variable of the current environment
		or pass it back to the parent environment."""
		pass
	
	def append_rec(self, id, val):
		"""Perform appending of the given value to the given id if id
		is defined in the current environment. Pass back to parent else.
		Return if appending has been performed, False else."""
		pass
	
	def __getitem__(self, id):
		return self.get(id)
	
	def __setitem__(self, id, val):
		self.set(id, val)
	
	def get_here(self, id, default = None):
		"""Get a value uniquely from the current environment."""
		return default
	
	def __getattr__(self, name):
		#print "DEBUG: %s.getattr(%s)" % (self.name, name)
		return self.get(name)

	def __repr__(self):
		return "env(%s)" % self.name

	def __eq__(self, e):
		return id(self) == id(e)

	def __ne__(self, e):
		return id(self) <> id(e)

	def __lt__(self, e):
		return id(self) < id(e)
		
	def __le__(self, e):
		return id(self) <= id(e)
		
	def __gt__(self, e):
		return id(self) > id(e)
		
	def __ge__(self, e):
		return id(self) >= id(e)


OS_SPECS = {
	'HOME': (lambda v: common.Path(v)) 
}
class OSEnv(Env):
	"""OS environment."""
	
	def __init__(self, path = topdir):
		Env.__init__(self, "os", path)
		self.parent = None

	def get(self, id, default = None):
		v = os.getenv(id)
		if v and OS_SPECS.has_key(id):
			r = OS_SPECS[id](v)
		else:
			r = os.getenv(id)
		#print "DEBUG: return OS with %s = %s" % (id, r)
		return r
	
	def set(self, id, val):
		#os.putenv(id, to_string(val))
		os.environ[id] = to_string(val)
	
	def append(self, id, val):
		self.set(id, self.get(id) + to_string(val))

	def append_rec(self, id, val):
		if self.is_def(id):
			self.append(id, val)
			return True
		else:
			return False
	
	def is_def(self, id):
		return os.getenv(id) <> None

	def __str__(self):
		return "OS"

class ParentEnv(Env):
	"""Environment with a parent environment."""
	parent = None
	
	def __init__(self, name, path, parent = None):
		Env.__init__(self, name, path)
		self.parent = parent
	
	def get(self, id, default = None):
		#print "DEBUG: ParentEnv(%s).get(%s)" % (self.name, id)
		if self.parent == None:
			r = default
		else:
			r = self.parent.get(id, default)
		#print "DEBUG: ending %s" % self.name
		return r
	
	def append(self, id, val):
		self.parent.append(id, val)

	def append_rec(self, id, val):
		return self.parent.append_rec(id, val)

	def is_def(self, id):
		return self.parent.is_def(id)

	def dump(self):
		r = "%s" % self
		c = self.parent
		while c:
			r = "%s < %s" % (r, c)
			c = c.parent
		return r


class MapEnv(ParentEnv):
	"""Environment with its own map."""
	
	def __init__(self, name, path, parent = None):
		ParentEnv.__init__(self, name, path, parent)
	
	def get(self, id, default = None):
		try:
			r = self.__dict__[id]
			#print "DEBUG: %s: FOUND %s as %s" % (self.name, id, r)
			return r
		except KeyError, e:
			#print "DEBUG: %s: NOT_FOUND %s" % (self.name, id)
			return ParentEnv.get(self, id, default)
	
	def set(self, id, val):
		self.__dict__[id] = val

	def is_def(self, id):
		return self.__dict__.has_key(id) or ParentEnv.is_def(self, id)

	def __str__(self):
		return "%s (%s)" % (self.name, self.path)

	def get_here(self, id, default = None):
		try:
			return self.__dict__[id]
		except KeyError, e:
			return default


class ScriptEnv(ParentEnv):
	"""Environment reflecting a script make.py."""
	map = None
	
	def __init__(self, name, path, parent = None, map = None):
		#print "DEBUG: SCRIPT(%s, %s)" % (name, id(map))
		assert map <> None
		ParentEnv.__init__(self, name, path, parent)
		self.map = map
		#self.__setattr__ = self.my_setattr
	
	def get(self, id, default = None):
		try:
			r = self.map[id]
			#print "DEBUG: script %s: FOUND %s as %s" % (self.name, id, r)
			return r
		except KeyError, e:
			#print "DEBUG: script %s: NOT_FOUND %s" % (self.name, id)
			return ParentEnv.get(self, id, default)
	
	def set(self, id, val):
		#print "DEBUG: %s.set(%s, %s)" % (self.name, id, str(val)[:min(20, len(str(val)))])
		self.map[id] = val

	def is_def(self, id):
		return self.map.has_key(id) or ParentEnv.is_def(self, id)

	def __str__(self):
		return "%s (%s)" % (self.name, self.path)

	def get_here(self, id, default = None):
		try:
			return self.map[id]
		except KeyError, e:
			return default

	def __setattr__(self, id, val):
		#print "DEBUG: %s.setattr(%s, %s)" % (self.name, id, str(val)[:min(20, len(str(val)))])
		if not self.__dict__.has_key("done") or self.__dict__.has_key(id):
			self.__dict__[id] = val
		else:
			self.map[id] = val


class ConfigEnv(ScriptEnv):
	
	def __init__(self, name, path, parent = None, map = None):
		ScriptEnv.__init__(self, name, path, parent, map)
	
	def get(self, id, deft):
		return ScriptEnv.get(self, id, deft)
		
		
# environment definitons
osenv = OSEnv()
root = MapEnv("builtin", topdir, osenv)
conf = ConfigEnv("config", topdir, root, { })
top = ScriptEnv("main", topdir, conf, sys.modules['__main__'].__dict__)
curenv = top			# current environment
common.topenv = top		# to break depedency circularity

