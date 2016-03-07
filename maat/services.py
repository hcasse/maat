"""Implements command line services of ElfMake."""

import io
import recipe
import sys

def list_goals(ctx = io.Context()):
	"""List goals."""

	l = [f for f in recipe.file_db.values() if f.is_goal]
	l.sort()
	ll = max([len(f.name) for f in l])
	for f in l:
		desc = f.get_here("DESCRIPTION")
		if desc:
			ctx.print_info("%s %s" % (f.name + " " * (ll - len(f.name)), desc))
		else:
			ctx.print_info(f.name)


def print_db():
	"""Print the DB."""
	
	done = { }
	for f in recipe.file_db:
		r = recipe.file_db[f].recipe
		if r and r not in done:
			done[r] = True
			r.display(sys.stdout)
