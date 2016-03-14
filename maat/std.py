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

"""Module providing standard services for Maat that includes automatic
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

import maat as elf
import maat.action as action
import maat.config as config
import maat.env as env
import maat.recipe as recipe
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
		elf.file("all")["DESCRIPTION"] = "build all"

	# install clean
	path = env.cenv.path / "clean"
	if not recipe.file_db.has_key(path):
		elf.goal("clean", [], elf.remove(CLEAN, ignore_error = True))
		elf.file("clean")["DESCRIPTION"] = "remove produced files"

	# install distclean
	path = env.cenv.path / "distclean"
	if not recipe.file_db.has_key(path):
		elf.goal("distclean", ["clean"], elf.remove(DISTCLEAN, ignore_error = True))
		elf.file("distclean")["DESCRIPTION"] = "remove produced files and configuration files"

	# install config
	path = env.cenv.path / "config"
	if not recipe.file_db.has_key(path):
		elf.goal("config", [], action.FunAction(config.make))
		elf.file("config")["DESCRIPTION"] = "build configuration"

elf.post_inits.append(elf.FunDelegate(install_default_goals))
