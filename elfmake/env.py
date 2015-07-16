"""Implementation of environment in ElfMake."""
import glob
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
			self.path = str(path)
	
	def __div__(self, arg):
		return Path(os.path.join(self.path, str(arg)))
	
	def __add__(self, ext):
		return Path(self.path + ext)

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

	def append_rec(self, id, val):
		if self.is_def(id):
			self.append(id, val)
			return True
		else:
			return False
	
	def is_def(self, id):
		return os.getenv(id) <> None


class ParentEnv(Env):
	"""Environment with a parent environment."""
	parent = None
	
	def __init__(self, name, path, parent = None):
		Env.__init__(self, name, path)
		self.parent = parent
	
	def get(self, id):
		assert self <> self.parent
		return self.parent.get(id)
	
	def append(self, id, val):
		self.parent.append(id, val)

	def append_rec(self, id, val):
		return self.parent.append_rec(id, val)

	def is_def(self, id):
		return self.parent.is_def(id)


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

	def is_def(self, id):
		return self.map.has_key(id) or ParentEnv.is_def(self, id)

	def append(self, id, val):
		if not self.append_rec(id, val):
			self.set(id, val)
			#print "DEBUG: <%s> %s = %s" % (self, id, val)
	
	def append_rec(self, id, val):
		if self.map.has_key(id):
			old = self.get(id)
			if isinstance(old, list):
				old.append(val)
			else:
				self.set(id, old + val)
			return True
		else:
			return ParentEnv.append_rec(self, id, val)
	


# environment definitons
osenv = OSEnv()
elfenv = MapEnv("builtin", topdir, osenv, sys.modules["elfmake"].__dict__)
confenv = MapEnv("config", topdir, elfenv)
topenv = MapEnv("main", topdir, confenv, sys.modules['__main__'].__dict__)
cenv = topenv		# current environment
