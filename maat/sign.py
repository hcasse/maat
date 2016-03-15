#	MAAT sign module
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

"""this module handles signature of recipes. The signature of a recipe
is the trace of actions needed to realize the recipe. The signature is
used to detect cases when configuration changed and a recipe needs
to be rebuilt accordingly: the action used to build it are changed."""

import maat as m
from maat import io
import marshal


signs = None
"""Map of tiles and signatures."""
update = False
"""True if signatures need to be updated."""

def load(ctx = io.DEF):
	"""Load the signature file, from .maat/signatures."""
	global signs
	global update
	global maat_dir
	
	p = m.temp() / "signs"
	signs = { }
	if not p.exists():
		update = True
	else:
		try:
			f = open(str(p), "rb")
			v = marshal.load(f)
			if not isinstance(v, dict):
				raise IOError("bad file content")
			signs = v
		except IOError, e:
			ctx.print_warning("signature file cannot be open (%s). This may cause some unexpected recompilations." % e)
			update = True


def save(ctx = io.DEF):
	"""Save the signatures if needed."""
	global signs
	global update
	
	# nothing to do
	if not update:
		return
	
	# save the file
	p = m.temp() / "signs"
	try:
		f = open(str(p), "wb")
		marshal.dump(signs, f)
	except IOError, e:
		ctx.print_warning("cannot save signature file: %s." % e)
	

def test(file):
	"""Test if a signature is ok. Return true if it is ok, false else."""
	global signs
	global update

	# no recipe: no need for signature
	if not file.recipe:
		return True

	try:

		# test the signature
		s = file.recipe.signature()
		k = str(file)
		if signs[k] == s:
			return True

		# signature does not match
		else:
			signs[k] = s
			update = True
			return False
	
	# no signature available
	except KeyError, e:
		signs[k] = s
		update = True
		return False
