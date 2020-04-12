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
  - BUILD_MODE -- build mode (usual modes are Debug or Release, default Debug)
"""

import maat
import action
import common
import config
import env
import install
import recipe
import os.path
import shutil

ALL = []
"""List of targets to build."""
CLEAN = [maat.maat_dir]
"""List of files to clean to remove temporary files."""
DISTCLEAN = ["config.py", "config.pyc"]
"""List of files to clean to remove any generated file (including configuration)."""
INSTALL = []
"""List of installation actions."""

env.root.PREFIX = "/usr"

def install_default_goals():
	"""Install default goals."""
	
	# install all
	path = env.cenv.path / "all"
	if not recipe.file_db.has_key(path):
		g = maat.goal("all", ALL)
		g.DESCRIPTION = "build all"

	# install clean
	path = env.cenv.path / "clean"
	if not recipe.file_db.has_key(path):
		g = maat.goal("clean", [], maat.remove(CLEAN, ignore_error = True))
		g.DESCRIPTION = "remove produced files"

	# install distclean
	path = env.cenv.path / "distclean"
	if not recipe.file_db.has_key(path):
		g = maat.goal("distclean", ["clean"], maat.remove(DISTCLEAN, ignore_error = True))
		g.DESCRIPTION = "remove produced files and configuration files"

	# install install
	if not recipe.file_db.has_key(env.top.path / "install"):
		g = maat.goal("install", INSTALL)
		g.DESCRIPTION = "perform installation of the sofware"
	
	# dist install
	if not recipe.file_db.has_key(env.top.path / "dist"):
		recipe.hidden("setup-dist", [], install.SetupDist())
		g = maat.goal("dist", ["setup-dist", "install"])
		g.DESCRIPTION = "build a binary distribution"

	# set the default variable
	config.set_if("BUILD_MODE", lambda : "Debug")
	config.set_comment("BUILD_MODE", "one of Debug or Release")

common.post_inits.append(common.FunDelegate(install_default_goals))
