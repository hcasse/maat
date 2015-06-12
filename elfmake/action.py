"""Represents the action that may be performed to build
the recipes."""

import env
import os
import re
import recipe
import select
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
			line = used.read()
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
	
	def execute(self, ress, deps, ctx):
		"""Perform the action. If an action fails, raise env.ElfError exception.
		It takes as parameter the list of results and the list of dependencies."""
		pass


class ShellAction(Action):
	"""An action that invokes a shell command.
	Action starting with '@' will not be displayed."""
	cmd = None
	quiet = False
	
	def __init__(self, cmd):
		self.cmd = cmd
		if cmd and cmd[0] == "@":
			self.quiet = True
			self.cmd = cmd[1:]

	def execute(self, ress, deps, ctx):
		if self.quiet:
			save = ctx.command_ena
			ctx.command_ena = False
		invoke(self.cmd, ctx)
		if self.quiet:
			ctx.command_ena = save


class GroupAction(Action):
	"""Represent a group of actions."""
	actions = None
	
	def __init__(self, actions):
		self.actions = actions
	
	def execute(self, ress, deps, ctx):
		for action in self.actions:
			action.execute(ress, deps, ctx)


class FunAction(Action):
	"""An action that takes a function to execution the action."""
	fun = None
	
	def __init__(self, fun):
		self.fun = fun
	
	def execute(self, ress, deps, ctx):
		fun(ress, deps, ctx)


def make_actions(*actions):
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
		

class GrepAction(Action):
	"""Action that performs a grep on command output."""
	exp = None
	cmd = None
	
	def __init__(self, exp, cmd):
		self.exp = exp
		self.cmd = make_actions(cmd)

	def execute(self, ress, deps, ctx):
		save = ctx.out
		ctx.out = GrepStream(self.exp, save)
		self.cmd.execute(ress, deps, ctx)
		ctx.out = save


class ActionRecipe(recipe.Recipe):
	"""A recipe that supports an action. object for generation."""
	act = None
	
	def __init__(self, ress, deps, action):
		recipe.Recipe.__init__(self, ress, deps)
		self.act = make_actions(action)
	
	def action(self, ctx):
		if self.act:
			self.act.execute(self.ress, self.deps, ctx)


def rule(ress, deps, *actions):
	"""Build a rule with actions."""
	ActionRecipe(ress, deps, make_actions(actions))


def goal(goal, deps, actions = Action()):
	"""Build a goal with the following dependencies."""

	# look for an existing goal
	path = env.Path(env.cenv.path) / goal
	file = recipe.get_file(str(path))
	if file.recipe:
		raise env.ElfError("a goal already named '%s' already exist!" % goal)
	else:
		file.is_goal = True
		file.recipe = ActionRecipe(goal, deps, actions)
		return

