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

"""Module providing test services."""
import maat
import action
import common
import env
import io
import recipe

import difflib
import os
import os.path
import shutil
import subprocess
import sys

TEST_CASES = []
BEFORE_TEST = []
NULL = open(os.devnull, "w")

class Case(recipe.Recipe):
	"""Recipe to implement test case."""
	name = None
	tests = None
	succeeded = 0
	longer = None
	
	def __init__(self, name, deps, private):
		recipe.Recipe.__init__(self, [maat.path(name)], deps)
		self.tests = []
		self.name = name
		recipe.get_file(name).set_goal()
		if not private:
			global TEST_CASES
			TEST_CASES.append(self.ress[0])
		self.ress[0].DESCRIPTION = "test case"

	def add(self, test):
		self.tests.append(test)
		self.deps = self.deps + test.deps
		self.longer = max(self.longer, len(test.name))
	
	def action(self, ctx):
		#ctx.print_info("Testing %s" % self.ress[0])
		self.succeeded = 0
		for test in self.tests:
			test.test(ctx)
		if self.succeeded == len(self.tests):
			ctx.out.write(io.BOLD + io.GREEN + "\tSUCCESS: all tests passed!\n" + io.NORMAL)
		else:
			ctx.out.write(io.BOLD + io.RED + "\tFAILURE: %d test(s) failed on %d\n" % (len(self.tests) - self.succeeded, len(self.tests)) + io.NORMAL)
			common.error("Test failed.")


class Test(recipe.Recipe):
	"""Implements a simple test, that is, perform its action
	and depending on the result increment succeeded counter
	of test case."""
	case = None
	name = None
	
	def __init__(self, case, name, deps):
		recipe.Recipe.__init__(self, [name], deps)
		self.name = name
		recipe.get_file(name).set_phony()
		self.case = case
		case.add(self)
		self.ress[0].set_goal()
		self.ress[0].DESCRIPTION = "test"

	def success(self, ctx):
		"""Record the current test as a success and display
		ok message."""
		self.case.succeeded += 1
		ctx.print_action_success()
	
	def failure(self, ctx, msg = ""):
		"""Record the current test as a failure display message."""
		ctx.print_action_failure(msg)
	
	def perform(self, ctx):
		"""Display message of a starting test."""
		ctx.print_action("\tTesting %s%s " % (self.name, ' ' * (self.case.longer - len(self.name))))
	
	def info(self, ctx, msg):
		"""Display an information."""
		ctx.print_info("\t\t%s" % msg)
	
	def test(self, ctx):
		"""This method is called to perform the test."""
		pass
	
	def action(self, ctx):
		pass


class OutputTest(Test):
	"""Test launching a command, storing the output and/or error
	stream and comparing it to expected output. Fails if there
	is a difference.
	
	Constructor takes as parameter the file to compare output stream
	and the file to compare error stream with. Matching channels are
	ignored if they get a value of None.
	
	An input stream may also be passed and the matching file will
	dumped to input of launched command."""
	
	def __init__(self, case, name, cmd, out = None, out_ref = None, err = None, err_ref = None, input = None, deps = None):
		Test.__init__(self, case, name, deps)
		self.cmd = cmd
		self.out = maat.path(out)
		self.out_ref = maat.path(out_ref)
		self.err = maat.path(err)
		self.err_ref = maat.path(err_ref)
		self.input = input
	
	def test(self, ctx):
		self.perform(ctx)
		#displayed = True
		
		try:
			
			# launch the command
			if self.out:
				self.out.parent().makedir()
				out_stream = open(str(self.out), "w")
			else:
				out_stream = NULL
			if self.err:
				self.err.parent().makedir()
				err_stream = open(str(self.err), "w")
			else:
				err_stream = NULL
			if self.input:
				in_stream = open(str(self.input), "r")
			else:
				in_stream = NULL
			cmd = action.make_line(self.cmd)
			if maat.verbose:
				ctx.print_info("running '%s'" % cmd)
			rc = subprocess.call(cmd, stdin = in_stream, stdout = out_stream, stderr = err_stream, shell = True)
			if rc <> 0:
				self.failure(ctx, "return code = %d, command = %s" % (rc, cmd))
				return
				
			# compare output if any
			if self.out:
				if not self.out_ref.exists():
					self.info(ctx, "no reference file for output, creating it!")
					maat.mkdir(str(self.out_ref.parent()))
					shutil.copyfile(str(self.out), str(self.out_ref))
				else:
					c = 0
					for l in difflib.context_diff(open(str(self.out), "r").readlines(), open(str(self.out_ref), "r").readlines()):
						c += 1
					if c:
						self.failure(ctx, "different output stream")
						return
			
			# compare error if any
			if self.err:
				if not self.err_ref.exists():
					self.info(ctx, "no reference file for error, creating it!")
					maat.mkdir(str(self.err_ref.parent()))
					shutil.copyfile(str(self.err), str(self.err_ref))
				else:
					c = 0
					for l in difflib.context_diff(open(str(self.err), "r").readlines(), open(str(self.err_ref), "r").readlines()):
						c += 1
					if c:
						self.failure(ctx, "different error stream")
						return
				
			# display result
			self.success(ctx)
		
		except OSError as e:
			self.failure(ctx, "test error: %s" % e)
		except IOError as e:
			self.failure(ctx, "test error: %s" % e)


class CommandTest(Test):
	"""A command test just run a command and examine the return code.
	If the return code is 0, the test is passed. Else the test is
	considered as failed."""
	
	def __init__(self, case, name, args, out = None, err = None, inp = None, deps = None, dir = None):
		if dir <> None:
			deps = common.as_list(deps) + [ dir ]
		Test.__init__(self, case, name, deps)
		self.args = args
		self.inp = inp
		self.out = out
		self.err = err
		self.dir = dir
	
	def check(self, rc):
		return rc == 0
	
	def test(self, ctx):
		self.perform(ctx)
		if self.dir <> None:
			old_dir = os.getcwd()
			try:
				os.chdir(self.dir)
			except OSError as e:
				raise common.MaatError("cannot change to '%s': %s" % (self.dir, e))
		if self.out:
			out = common.Path(self.out)
			maat.mkdir(str(out.parent()))
			out_stream = open(str(out), "w")
		else:
			out_stream = NULL
		if self.err:
			err = common.Path(self.err)
			maat.mkdir(str(err.parent()))
			err_stream = open(str(err), "w")
		else:
			err_stream = NULL
		if self.inp:
			in_stream = open(str(self.input), "r")
		else:
			in_stream = NULL
		cmd = action.make_line(self.args)
		if maat.verbose:
			ctx.print_info("running %s" % cmd)
		rc = subprocess.call(cmd, stdin = in_stream, stdout = out_stream, stderr = err_stream, shell = True)
		if self.check(rc):
			self.success(ctx)
		else:
			self.failure(ctx, "return code = %d, command = %s" % (rc, cmd))
		if self.dir <> None:
			os.chdir(old_dir)

class FailingCommandTest(CommandTest):
	"""Test launching a command and that succeed if the command fails."""

	def __init__(self, case, name, args, out = None, err = None, inp = None, deps = None, dir = None):
		CommandTest.__init__(self, case, name, args, out, err, inp, deps, dir)

	def check(self, rc):
		return rc <> 0


def case(name, deps = None, private = False):
	"""Build a test a case, that is, an abstract goal
	with a recipe launching tests. If private is to True, the case
	is not added to the global list of test cases."""
	return Case(name, deps, private)

def command(case, name, args, out = None, err = None, inp = None, deps = None, dir = None):
	"""Build a command test that run the command and examine return code."""
	return CommandTest(case, name, args, out, err, inp, deps, dir)

def failing_command(case, name, args, out = None, err = None, inp = None, deps = None, dir = None):
	"""Build a command test that run the command and check from the return code if the command failed."""
	return FailingCommandTest(case, name, args, out, err, inp, deps)

def output(case, name, cmd, out = None, out_ref = None, err = None, err_ref = None, input = None, deps = []):
	"""Build a test that launches a command compares output."""
	return OutputTest(case, name, cmd, out, out_ref, err, err_ref, input, deps)

def before(*actions):
	"""Add an action to actions performed before test."""
	BEFORE_TEST.append(action.make_actions(*actions))

def post_init():
	"""Initialize the test goal."""
	path = env.cenv.path / "test"
	if not recipe.file_db.has_key(path):
		before_test = recipe.phony("before-test", [], action.make_actions(BEFORE_TEST))
		test = maat.goal("test", [before_test] + TEST_CASES)
		test.DESCRIPTION = "run tests"

maat.post_inits.append(maat.FunDelegate(post_init))
