"""Implementation of environment in ElfMake."""
import os
import os.path
import sys

top = os.getcwd()	# top directory

class OSEnv:
	"""Definition environment."""
	path = None
	
	def __init__(self, path = top):
		self.path = path

	def get(self, id):
		"""Get en identifier looking in the current environment
		or in the parent environment."""
		return os.getenv(id)
	
	def set(self, id, val):
		"""Set a value to an identifier in the current environment."""
		os.putenv(id, val)


class Env(OSEnv):
	"""Environment with a parent environment."""
	parent = None
	
	def __init__(self, path, parent = None):
		OSEnv.__init__(self, path)
		self.parent = parent
	
	def get(self, id):
		return self.parent.get(id)


class MapEnv(Env):
	"""Environment with its own map."""
	map = None
	
	def __init__(self, path, parent = None, map = None):
		Env.__init__(self, path, parent)
		if map:
			self.map = map
		else:
			self.map = { }
	
	def get(self, id):
		try:
			return self.map[id]
		except KeyError, e:
			return Env.get(self, id)
	
	def set(self, id, val):
		self.map[id] = val


# environment definitons
osenv = OSEnv()
elfenv = MapEnv(top, osenv, sys.modules[__name__].__dict__)
confenv = MapEnv(top, elfenv)
topenv = MapEnv(top, confenv, sys.modules['__main__'].__dict__)
cenv = topenv		# current environment
