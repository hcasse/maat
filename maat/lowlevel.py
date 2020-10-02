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

import os
import shutil

import maat.common as common
import maat.env as env
import maat.io as io

def makedir(path):
	"""Build a directory if not existing, building possibly intermediate
	directories."""
	path = str(path)
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except os.error as e:
			common.error("cannot create '%s': %s" % (path, e))


def copy(frm, to, filter = common.Filter()):
	"""Perform a copy of a file or a recursive copy of a directory."""
	makedir(to)
	try:
		if not frm.is_dir():
			shutil.copyfile(str(frm), str(to / frm.get_file()))
		else:
			parent = frm.parent()
			for dir, dirs, files in os.walk(str(frm)):
					
				# create directory
				org_dpath = common.Path(dir)
				tgt_dpath = to / common.Path(dir).relative_to(parent)
				if not tgt_dpath.exists():
					os.mkdir(str(tgt_dpath))
					
				# copy files
				for file in files:
					org_fpath = org_dpath / file
					tgt_fpath = to / common.Path(dir).relative_to(parent) / file
					if filter.accept(org_fpath):
						shutil.copyfile(str(org_fpath), str(tgt_fpath))
					
				# copy directories
				for d in dirs:
					org_path = org_dpath / d
					if not filter.accept(org_path):
						dirs.remove(d)
	except (IOError, OSError) as e:
			env.error(str(e))
