"""ElfMake module providing configuration classes."""
import env
import imp
import os.path


class Config:
	"""Interface of modules performing configuration."""
	
	def name(self):
		"""Used to get name of the configuration."""
		return ""
	
	def configure(self, map):
		"""Called to perform configuration.
		Should store result in map."""
		pass

config_list = []	# list of configuration modules

def register(config):
	"""Function used to register a configuration."""
	config_list.append(config)


def load():
	"""Called to load the configuration file."""
	cpath = os.path.join(env.top, "config.py")
	if os.path.exists(cpath):
		mod = imp.load_source('config.py', cpath)
		env.confenv.map = mod.__dict__
		

def make():
	"""Build a configuration."""
