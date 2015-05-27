"""Module providing standard services for ElfMake that includes automatic
goals:
  * all -- build all,
  * clean -- cleanup temporaries files,
  * distclean -- clean all what is built,
  * install -- install programs.

And some useful variables:
  * ALL -- list of files to build,
  * CLEAN -- list of files to clean,
  * DISTCLEAN -- list of files to clean for distribution.

In addition, it is using the following variables from the current environment:
  * INSTALLDIR -- installation directory (default to /usr).
  * PROJECT -- project name.
  * VERSION -- project version.
"""

ALL = []
CLEAN = []
DISTCLEAN = []
INSTALL_PROGRAMS = []
INSTALL_LIBS = []
INSTALL_DATA = []
