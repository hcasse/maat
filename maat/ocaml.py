#	MAAT OCAML module
#	Copyright (C) 2018 H. Casse <hugues.casse@laposte.net>
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

# TODO
#	support dependencies
#	support libraries

import os.path
from maat import *
import maat as base

import common
import action
import install
import recipe
import std

# configuration
OCAMLC = config.FindProgram("OCAML batch compiler", "OCAMLC", ["ocamlc"])
OCAMLOPT = config.FindProgram("OCAML native compiler", "OCAMLOPT", ["ocamlopt"])

config.set_if("OCAMLCFLAGS_Debug", lambda: "-g")
config.set_if("OCAMLCFLAGS_Release", lambda: "")
config.set_if("OCAMLOPTFLAGS_Debug", lambda: "-g")
config.set_if("OCAMLOPTFLAGS_Release", lambda: "")


# system dependent configuration
if curenv.IS_WINDOWS:
	EXE_SUFFIX = ".exe"
else:
	EXE_SUFFIX = ""

# default configuration
env.root.OCAMLC = "ocamlc"
env.root.OCAMLOPT = "ocamlopt"


# commands
class Linker(action.Action):
	prog = None
	objs = None
	is_opt = None
	
	def __init__(self, prog, objs, libs, is_opt):
		self.prog = prog
		self.objs = objs
		self.libs = libs
		self.is_opt = is_opt
	
	def added(self):
		added = []
		if self.prog.ADDED_PATHS:
			added = ["-I %s" % p for p in self.prog.ADDED_PATHS]
		if self.prog.ADDED_LDFLAGS:
			added = added + [self.prog.ADDED_LDFLAGS]
		if self.prog.ADDED_LDFLAGS:
			added = added + [self.prog.ADDED_LDFLAGS]
		return added
	
	def command(self):
		# take into account the build mode
		if self.is_opt:
			cc = [self.prog.OCAMLOPT, self.prog.OCAMLOPTFLAGS]
		else:
			cc = [self.prog.OCAMLC, self.prog.OCAMLCFLAGS]
		return [cc, self.prog.CFLAGS, "-o", self.prog, self.libs, self.objs, self.added()]
	
	def execute(self, ctx):
		action.invoke(self.command(), ctx)
			
	def commands(self, cmds):
		cmds.append("%s" % action.make_line(self.command()))
	
def make_dep_dir(r):
	p = r.ress[0].path.parent()
	temp(maat_dir / p.relative_to_top())


# generic recipes
def comp_ml_to_cmo(ress, deps):
	return [ress[0].OCAMLC, ress[0].CFLAGS, "-o", ress[0], "-c", deps[0], ress[0].ADDED_FLAGS]
def comp_ml_to_cmx(ress, deps):
	return [ress[0].OCAMLOPT, ress[0].CFLAGS, "-o", ress[0], "-c", deps[0], ress[0].ADDED_FLAGS]

gen_command(".cmo", ".ml",  comp_ml_to_cmo)
gen_command(".cmx", ".ml", comp_ml_to_cmx)


# functions

def make_objects(dir, sources, opt, CFLAGS):
	"""Build the objects and their recipes and return the list of objects.
	".cmo/x" are automatically added to CLEAN list."""
	objs = []
	for s in sources:
		fs = recipe.gen(dir, ".cmx" if opt else ".cmo", s.path)
		std.CLEAN = std.CLEAN + fs
		o = file(fs[-1])
		objs.append(o)
		o.CFLAGS = CFLAGS
		added = ""
		if o.BUILD_MODE <> "":
			f = o["CFLAGS_%s" % o.BUILD_MODE]
			if f <> None:
				added = "%s %s" % (added, f)
		#d = file(maat_dir / o.path.parent().relative_to_top())
		#if not d.recipe:
		#	recipe.ActionRecipe([d], [], action.MakeDir(d.path))
		#	d.set_hidden()
		#o.recipe.deps.append(d)
		#df = (d.path / (o.path.get_base().get_file() + ".d"))
		#added = added + " -MMD -MF %s" % df.relative_to_cur()
		#if added:
		#	o.ADDED_FLAGS = added
		#parse_dep(df)	
	return objs


def program(name, sources, LDFLAGS = None, OCAMLCFLAGS = None, OCAMLOPTFLAGS = None,
LIBS = None, INSTALL_TO = "", opt = False):
	"""Called to build a C or C++ program."""
	sources = [file(s) for s in common.as_list(sources)]
	
	# take into account the build mode
	if opt:
		suff = ".cmxa"
		flags = OCAMLOPTFLAGS
	else:
		suff = ".cma"
		flags = OCAMLCFLAGS
	
	# record prog file
	prog = file(name + EXE_SUFFIX)
	recipe.add_alias(prog, name)

	# build objects
	objs = make_objects(prog.path.parent(), sources, opt, flags)

	# append the right suffix to library names
	libs = [l + suff for l in common.as_list(LIBS)]
	
	# build program
	recipe.ActionRecipe([prog], objs, Linker(prog, objs, libs, opt))
	if LDFLAGS:
		prog.LDFLAGS = LDFLAGS
	if prog.BUILD_MODE <> "":
		f = prog["LDFLAGS_%s" % prog.BUILD_MODE]
		if f <> None:
			prog.ADDED_LDFLAGS = "%s %s" % (prog.ADDED_LDFLAGS, f)
	#if LIBS:
	#	post_inits.append(LibSolver(prog, LIBS))
	
	# record it
	std.ALL.append(prog)
	std.DISTCLEAN.append(prog)
	if INSTALL_TO <> None:
		prog.INSTALL_TO = INSTALL_TO
		install.program(prog)


