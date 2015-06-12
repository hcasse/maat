"""Implementation of environment in ElfMake."""
import os
import os.path
import sys

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
			self.path = path
	
	def __div__(self, arg):
		return Path(os.path.join(self.path, str(arg)))
	
	def __str__(self):
		return self.path
	
	def exists(self):
		"""Test if the file matching the path exists."""
		return os.path.exists(self.path)

	def get_mod_time(self):
		return os.path.getmtime(self.path)
		
	def prefixed_by(self, path):
		return self.path.startswith(str(path))

	def relative_to_cur(self):
		return Path(os.path.relpath(self.path))

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
		return os.path.dirname(self.path)

topdir = Path(os.getcwd())	# top directory

def curdir():
	"""Get the current working directory."""
	return Path(os.getcwd())


# environments
class Env:
	"""Base class of environments."""
	path = None
	name = None
	
	def __init__(self, name, path = topdir):
		self.name = name
		self.path = path

	def get(self, id):
		"""Get an identifier looking in the current environment
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
	
	def __init__(self, path = topdir):
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
elfenv = MapEnv("builtin", topdir, osenv, sys.modules["elfmake"].__dict__)
confenv = MapEnv("config", topdir, elfenv)
topenv = MapEnv("main", topdir, confenv, sys.modules['__main__'].__dict__)
cenv = topenv		# current environment
