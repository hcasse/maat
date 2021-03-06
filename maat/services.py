#	Service module
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

"""Implements command line services of ElfMake."""

import os.path
import sys

from maat import common
from maat import env
from maat import io
from maat import lowlevel
from maat import recipe

def list_goals(ctx = io.Context()):
	"""List goals."""

	l = [f for f in recipe.file_db.values() if f.is_goal and not f.is_hidden]
	if l:
		l.sort(key = lambda f: str(f))
		ll = max([len(str(f)) for f in l])
		for f in l:
			desc = f.get_here("DESCRIPTION")
			if desc:
				ctx.print_def(str(f) + " " * (ll - len(str(f)) + 1), desc)
			else:
				ctx.print_info(str(f))


def print_db():
	"""Print the DB."""
	
	# print simple rules
	done = { }
	for f in recipe.file_db:
		r = recipe.file_db[f].recipe
		if r and r not in done:
			done[r] = True
			r.display(sys.stdout)

	# print generic rules
	for ext in recipe.ext_db.values():
		for (rext, gen) in ext.gens.items():
			if gen.res.ext == rext:
				sys.stdout.write("*%s: *%s\n" % (gen.res.ext, ext.ext))
			else:
				sys.stdout.write("[%s] *%s: *%s\n" % (rext, gen.res.ext, ext.ext))
			gen.write(sys.stdout)
			sys.stdout.write("\n")


def embed():
	"""Embed the required modules in the current project."""
	
	# select the libraries
	tm = None
	ms = []
	for m in sys.modules.values():
		try:
			if m != None:
				if m.__name__ == "maat":
					tm = m
					ms.append(m)
				elif m.__name__.startswith("maat."):
					ms.append(m) 
		except AttributeError:
			pass

	# get maat directory
	mpath = common.Path(env.top.path) / "maat"

	# copy the modules
	for m in ms:
		p = m.__file__
		if p.endswith(".pyc"):
			p = p[:-1]
		lowlevel.copy(common.Path(p), mpath)

