"""Module providing standard services for ElfMake that includes automatic
goals:
  - all -- build all,
  - clean -- cleanup temporaries files,
  - distclean -- clean all what is built,
  - install -- install programs.

And some useful variables:
  - ALL -- list of files to build,
  - CLEAN -- list of files to clean,
  - DISTCLEAN -- list of files to clean for distribution.

In addition, it is using the following variables from the current environment:
  - INSTALLDIR -- installation directory (default to /usr).
  - PROJECT -- project name.
  - VERSION -- project version.
"""

import elfmake as elf
import elfmake.action as action
import elfmake.config as config
import elfmake.env as env
import elfmake.recipe as recipe
import os.path

ALL = []
CLEAN = []
DISTCLEAN = ["config.py", "config.pyc"]
INSTALL_PROGRAMS = []
INSTALL_LIBS = []
INSTALL_DATA = []

def install_default_goals():
	"""Install default goals."""
	
	# install all
	path = env.cenv.path / "all"
	if not recipe.file_db.has_key(path):
		elf.goal("all", ALL)

	# install clean
	path = env.cenv.path / "clean"
	if not recipe.file_db.has_key(path):
		elf.goal("clean", [], elf.remove(CLEAN, ignore_error = True))

	# install distclean
	path = env.cenv.path / "distclean"
	if not recipe.file_db.has_key(path):
		elf.goal("distclean", ["clean"], elf.remove(DISTCLEAN, ignore_error = True))


	# install config
	path = env.cenv.path / "config"
	if not recipe.file_db.has_key(path):
		elf.goal("config", [], action.FunAction(config.make))

elf.post_inits.append(install_default_goals)
