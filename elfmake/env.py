"""Implementation of environment in ElfMake."""
import os
import os.path
import sys

top = os.getcwd()	# top directory

class ElfError(Exception):
	"""Exception when a Make error happens."""
	msg = None
	
	def __init__(self, msg):
		self.msg = msg
	
	def __repr__(self):
		return self.msg

	def __str__(self):
		return self.msg


def to_string(v):
	"""Convert a value to string."""
	if v == None:
		return ""
	elif isinstance(v, list):
		return " ".join(v)
	else:
		return str(v)

class Env:
	"""Base class of environments."""
	path = None
	name = None
	
	def __init__(self, name, path = top):
		self.name = name
		self.path = path

	def get(self, id):
		"""Get en identifier looking in the current environment
		or in the parent environment."""
		return None
	
	def set(self, id, val):
		"""Set a value to an identifier in the current environment."""
		pass
	
	def append(self, id, val):
		"""Append the given value to an existing variable of the current environment
		or pass it back to the parent environment."""
		pass


class OSEnv(Env):
	"""OS environment."""
	
	def __init__(self, path = top):
		Env.__init__(self, "os", path)

	def get(self, id):
		return os.getenv(id)
	
	def set(self, id, val):
		os.putenv(id, to_string(val))

	def append(self, id, val):
		self.set(id, self.get(id) + to_string(val))


class ParentEnv(Env):
	"""Environment with a parent environment."""
	parent = None
	
	def __init__(self, name, path, parent = None):
		Env.__init__(self, name, path)
		self.parent = parent
	
	def get(self, id):
		return self.parent.get(id)
	
	def append(self, id, val):
		self.parent.append(id, val)


class MapEnv(ParentEnv):
	"""Environment with its own map."""
	map = None
	
	def __init__(self, name, path, parent = None, map = None):
		ParentEnv.__init__(self, name, path, parent)
		if map:
			self.map = map
		else:
			self.map = { }
	
	def get(self, id):
		try:
			return self.map[id]
		except KeyError, e:
			return ParentEnv.get(self, id)
	
	def set(self, id, val):
		self.map[id] = val

	def append(self, id, val):
		try:
			old = self.get(id)
			if isinstance(old, list):
				old.append(val)
			else:
				self.set(id, old + val)
		except KeyError, e:
			ParentEnv.append(self, id, val)


# environment definitons
osenv = OSEnv()
elfenv = MapEnv("builtin", top, osenv, sys.modules["elfmake"].__dict__)
confenv = MapEnv("config", top, elfenv)
topenv = MapEnv("main", top, confenv, sys.modules['__main__'].__dict__)
cenv = topenv		# current environment
