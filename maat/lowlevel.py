#	MAAT low-level module
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
"""These modules implements low-level and compatible operations performed
by the Maat build system."""

import common
import env
import io
import os

def makedir(path):
	"""Build a directory if not existing, building possibly intermediate
	directories."""
	path = str(path)
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except os.error, e:
			common.error("cannot create '%s': %s" % (path, e))
