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

"""Represents the action that may be performed to build
the recipes."""

import env
import os
import lowlevel
import re
import select
import shutil
import sys
import subprocess

def make_line(args):
	line = ""
	if isinstance(args, str):
		return args
	for a in args:
		if isinstance(a, list):
			line = line + make_line(a)
		else:
			line = line + " " + env.to_string(a)
	return line

def invoke(cmd, ctx):
	"""Launch the given command in the current shell."""

	# print command
	line = make_line(cmd)
	ctx.print_command(line)
	
	# prepare process
	proc = subprocess.Popen(line, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	
	# prepare handling if out, err
	map = { proc.stdout: ctx.out, proc.stderr: ctx.err }
	ins = [proc.stdout, proc.stderr]
	while ins:
		useds, x, y = select.select(ins, [], [])
		for used in useds:
			line = used.readline()
			if line:
				map[used].write(line)
			else:
				ins.remove(used)
	
	# wait end of called process
	r = proc.wait()
	if r <> 0:
		raise env.ElfError("build failed")


class Action:
	"""Base class of all actions."""
	recipe = None
	
	def execute(self, ctx):
		"""Perform the action. If an action fails, raise env.ElfError exception.
		It takes as parameter the IO context of execution."""
		pass
	
	def display(self, out):
		"""Display an action (one tab + one line)."""
		pass
	
	def clone(self):
		"""Clone the current action."""
		return Action()

	def set_recipe(self, recipe):
		"""Set the recipe implemented by the current action."""
		self.recipe = recipe

	def signature(self):
		"""compute the signature of the function as a string."""
		return ""
		

NULL = Action()
"""Null action."""

class ShellAction(Action):
	"""An action that invokes a shell command.
	Action starting with '@' will not be displayed."""
	cmd = None
	quiet = False
	
	def __init__(self, cmd, quiet = False):
		if cmd and cmd[0] == "@":
			quiet = True
			cmd = cmd[1:]
		self.cmd = cmd
		self.quiet = quiet

	def execute(self, ctx):
		if self.quiet:
			save = ctx.command_ena
			ctx.command_ena = False
		invoke(self.cmd, ctx)
		if self.quiet:
			ctx.command_ena = save

	def display(self, out):
		out.write("\t%s\n" % self.cmd)

	def clone(self):
		return ShellAction(self.cmd, self.quiet)

	def signature(self):
		return make_line(self.cmd)


class GroupAction(Action):
	"""Represent a group of actions."""
	actions = None
	
	def __init__(self, actions):
		self.actions = actions
	
	def execute(self, ctx):
		for action in self.actions:
			action.execute(ctx)

	def display(self, out):
		for a in self.actions:
			a.display(out)

	def clone(self):
		return GroupAction([a.clone() for a in self.actions])		

	def set_recipe(self, recipe):
		Action.set_recipe(self, recipe)
		for a in self.actions:
			a.set_recipe(recipe)
	
	def signature(self):
		return "\n".join([a.signature() for a in self.actions])


class FunAction(Action):
	"""An action that takes a function to execution the action."""
	fun = None
	
	def __init__(self, fun):
		self.fun = fun
	
	def execute(self, ctx):
		self.fun(self.recipe.ress, self.recipe.deps, ctx)

	def display(self, out):
		out.write("\tfunction\n")

	def clone(self):
		return FunAction(self.fun)


def make_actions(*actions):
	"""Build an action (group or single action) from various set of arguments:
	empty, simple string, lists, etc."""
	if not actions:
		return Action()
	result = []
	for action in actions:
		if isinstance(action, list) or isinstance(action, tuple):
			for subaction in action:
				result.append(make_actions(subaction))
		elif isinstance(action, Action):
			result.append(action)
		else:
			result.append(ShellAction(str(action)))
	if len(result) == 1:
		return result[0]
	else:
		return GroupAction(result)


class GrepStream:
	"""Stream that keeps only lines that match a regular expression."""
	exp = None
	out = None
	
	def __init__(self, exp, out):
		self.exp = re.compile(exp)
		self.out = out
	
	def write(self, line):
		if self.exp.search(line):
			self.out.write(line)
	

class Grep(Action):
	"""Action that performs a grep on command output."""
	exp = None
	cmd = None
	out = False
	err = False
	
	def __init__(self, exp, cmd, out = True, err = False):
		self.exp = exp
		self.cmd = make_actions(cmd)
		self.out = out
		self.err = err

	def execute(self, ctx):
		if self.out:
			old_out = ctx.out
			ctx.out = GrepStream(self.exp, old_out)
		if self.err:
			old_err = ctx.err
			ctx.err = GrepStream(self.exp, old_err)
		self.cmd.execute(self.recipe.ress, self.recipe.deps, ctx)
		if self.out:
			ctx.out = old_out
		if self.err:
			ctx.err = old_err

	def display(self, ress, deps, out):
		out.write("\t%s | grep %s" % (self.cmd, self.exp))

	def clone(self):
		return Grep(self.exp, self.cmd, self.out, self.err)


class Remove(Action):
	"""Action of remove."""
	paths = None
	ignore_error = None
	
	def __init__(self, args, ignore_error = False):
		self.paths = [env.Path(arg) for arg in args]
		self.ignore_error = ignore_error
	
	def execute(self, ctx):	
		for p in self.paths:
			try:
				ctx.print_command("remove %s" % p)
				if p.is_dir():
					shutil.rmtree(str(p))
				else:
					os.remove(str(p))	
			except OSError, e:
				if not self.ignore_error:
					raise env.ElfError(str(e))

	def display(self, out):
		for p in self.paths:
			out.write("\tremove %s\n" % p)

	def clone(self):
		return Remove(self.paths, ignore_error = self.ignore_error)

	def signature(self):
		return "\n".join(["remove %s" % p for p in self.paths])




class Move(Action):
	"""Action of a moving file or directories to a specific directory."""
	paths = None
	target = None
	
	def __init__(self, paths, target):
		self.paths = [env.Path(arg) for arg in args]
		self.target = env.Path(target)
	
	def execute(self, ctx):	
		# TODO
		try:
			pass
		except OSError, e:
			raise env.ElfError(str(e))
		
	def display(self, out):
		for p in self.paths:
			out.write("\tmove %s to %s\n" % (p, self.target))

	def clone(self):
		return Move(self.paths, self.target)
		
	def signature(self):
		return "\n".join(["move %s to %s" % (p, self.target) for p in self.target])


class Invoke(Action):
	"""Action that performs an invocation on the recipe components."""
	cmd = None

	def __init__(self, cmd):
		self.cmd = cmd

	def execute(self, ctx):	
		try:
			invoke(self.cmd, ctx)
		except OSError, e:
			raise env.ElfError(str(e))
		
	def display(self, out):
		out.write("\t%s\n" % make_line(self.cmd))

	def clone(self):
		return Invoke(self.cmd)

	def signature(self):
		return make_line(self.cmd)


class Hidden(Action):
	"""A hidden action performs the sub-action but does not display it
	and is not visible in the signature."""
	
	def __init__(self, action):
		self.action = action
	
	def execute(self, ctx):
		self.action.execute(ctx)
	
	def display(self, out):
		pass
	
	def clone(self):
		return Hidden(self.action.clone())
	
	def signature(self):
		return ""


class Print(Action):
	"""Action that prints a message."""
	
	def __init__(self, msg):
		self.msg = msg
	
	def execute(self, ctx):
		ctx.print_info(self.msg)

	def clone(self):
		return Print(self.msg)

	def display(self, out):
		out.write("\tprint(%s)\n" % self.msg)
	
	def signature(self):
		return "print(%s)" % self.msg


class MakeDir(Action):
	"""Action that build a directory or a chain of directories."""
	path = None
	
	def __init__(self, path):
		self.path = path
		
	def execute(self, ctx):
		lowlevel.makedir(self.path)
	
	def display(self, out):
		out.write("\tmakedir %s\n" % self.path)
	
	def signature(self):
		return "makedir(%s)" % self.path

	
