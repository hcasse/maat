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

import os
import re
import select
import shutil
import subprocess
import sys

from maat import common
from maat import env
from maat import io
from maat import lowlevel
from maat import recipe


def make_line(args):
	line = ""
	if isinstance(args, str):
		return args
	for a in args:
		if a == None:
			continue
		elif isinstance(a, list):
			line = line + make_line(a)
		else:
			line = line + " " + str(a)
	return line

def invoke(cmd, ctx, out = None, err = None):
	"""Launch the given command in the current shell."""
	if  cmd == "None":
		cmd()

	# print command
	line = make_line(cmd)
	ctx.print_command(line)
	
	# prepare streams
	ins = []
	if out == False:
		out_arg = subprocess.DEVNULL
	elif out == None:
		out_arg = subprocess.PIPE
	else:
		out_arg = out
	if err == False:
		err_arg = subprocess.DEVNULL
	elif err == None:
		err_arg = subprocess.PIPE
	else:
		err_arg = err

	# run the process
	proc = subprocess.Popen(line, shell=True, stdout = out_arg, stderr = err_arg)
	
	# manage outputs
	map = { }
	if out == None:
		map[proc.stdout] = ctx.out
	if err == None:
		map[proc.stderr] = ctx.err
	ins = list(map.keys())
	while ins:
		useds, x, y = select.select(ins, [], [])
		for used in useds:
			line = used.readline()
			if line:
				map[used].write(line.decode(sys.getdefaultencoding()))
			else:
				ins.remove(used)
	
	# wait end of called process
	r = proc.wait()
	if r != 0:
		common.error("build failed")

class StreamCollector:
	
	def __init__(self):
		self.buf = ""
	
	def write(self, txt):
		if txt and txt[-1] == '\n':
			self.buf = self.buf + txt[:-1] + " "
		else:
			self.buf = self.buf + " "


def output(*cmd):
	"""Collect the output of a command call."""
	io.DEF.quiet = True
	out = StreamCollector()
	invoke(cmd, io.DEF, out)
	io.DEF.quiet = False
	return out.buf
	

class Action:
	"""Base class of all actions."""
	recipe = None
	
	def execute(self, ctx):
		"""Perform the action. If an action fails, raise env.MaatError exception.
		It takes as parameter the IO context of execution."""
		pass
		
	def commands(self, cmds):
		"""Store in cmds the commands composing the action."""
		pass
	
	def display(self, out):
		"""Display an action (one tab + one line)."""
		cmds = []
		self.commands(cmds)
		for cmd in cmds:
			out.write("\t%s\n" % cmd)
	
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
	
	def __init__(self, cmd, quiet = False, no_out = False, no_err = False):
		if cmd and cmd[0] == "@":
			quiet = True
			cmd = cmd[1:]
		self.cmd = cmd
		self.quiet = quiet
		self.no_out = no_out
		self.no_err = no_err

	def execute(self, ctx):
		if self.quiet:
			save = ctx.command_ena
			ctx.command_ena = False
		if self.no_out:
			out = False
		else:
			out = None
		if self.no_err:
			err = False
		else:
			err = None
		invoke(self.cmd, ctx, out = out, err = err)
		if self.quiet:
			ctx.command_ena = save

	def commands(self, cmds):
		cmds.append(self.cmd)

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

	def commands(self, cmds):
		for a in self.actions:
			a.commands(cmds)

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
		self.fun(ctx)

	def commands(self, cmds):
		cmds.append("<function>")

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

	def commands(self, cmds):
		cmds.append("%s | grep %s" % (self.cmd, self.exp))

	def clone(self):
		return Grep(self.exp, self.cmd, self.out, self.err)


class Remove(Action):
	"""Action of remove."""
	paths = None
	ignore_error = None
	
	def __init__(self, args, ignore_error = False):
		self.paths = recipe.get_files(args)
		self.ignore_error = ignore_error
	
	def execute(self, ctx):	
		for p in self.paths:
			try:
				ctx.print_command("remove '%s'" % p)
				if p.actual().is_dir():
					shutil.rmtree(str(p))
				else:
					os.remove(str(p))	
			except OSError as e:
				if not self.ignore_error:
					common.error(str(e))

	def commands(self, cmds):
		for p in self.paths:
			cmds.append("remove %s" % p)

	def clone(self):
		return Remove(self.paths, ignore_error = self.ignore_error)

	def signature(self):
		return "\n".join(["remove %s" % p for p in self.paths])




class Move(Action):
	"""Action of a moving file or directories to a specific directory."""
	paths = None
	target = None
	
	def __init__(self, paths, target):
		self.paths = [common.Path(arg) for arg in args]
		self.target = common.Path(target)
	
	def execute(self, ctx):	
		# TODO
		try:
			pass
		except OSError as e:
			common.error(str(e))
		
	def commands(self, cmds):
		for p in self.paths:
			cmds.append("move %s to %s" % (p, self.target))

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
		except OSError as e:
			common.error(str(e))
		
	def commands(self, cmds):
		cmds.append(make_line(self.cmd))

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
		old_quiet = ctx.quiet
		ctx.quiet = True
		self.action.execute(ctx)
		ctx.quiet = old_quiet
	
	def commands(self, cmds):
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

	def commands(self, cmds):
		cmds.append("print(%s)" % self.msg)
	
	def signature(self):
		return "print(%s)" % self.msg


class MakeDir(Action):
	"""Action that build a directory or a chain of directories."""
	path = None
	
	def __init__(self, path):
		self.path = path
		
	def execute(self, ctx):
		ctx.print_command("makedir '%s'" % self.path)
		lowlevel.makedir(self.path)
	
	def commands(self, cmds):
		cmds.append("makedir %s" % self.path)
	
	def signature(self):
		return "makedir(%s)" % self.path
	

class MakeFile(Action):
	"""Build a file with the given content."""
	path = None
	content = None
	
	def __init__(self, path, content):
		self.path = common.Path(path)
		self.content = str(content)
	
	def execute(self, ctx):
		ppath = self.path.parent()
		if not ppath.is_empty():
			lowlevel.makedir()
		f = open(str(self.path), "w")
		f.write(self.content)
		f.close()

	def commands(self, cmds):
		cmds.append("makefile(%s, %s)" % (self.path, self.content))
	
	def signature(self):
		return "makefile(%s, %s)" % (self.path, self.content)


class Rename(Action):
	"""Rename a file to a different name."""
	src = None
	tgt = None
	
	def __init__(self, src, tgt):
		self.src = common.Path(src)
		self.tgt = common.Path(tgt)
	
	def execute(self, ctx):
		try:
			os.rename(self.src.path, self.tgt.path)
		except OSError as e:
			raise MaatError(str(e))
	
	def signature(self):
		return "rename(%s, %s)" % (self.src.path, self.tgt.path)
	
	def commands(self, cmds):
		cmds.append(self.signature())

			
