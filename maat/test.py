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
NULL = open(os.devnull, "w")

class Case(recipe.Recipe):
	"""Recipe to implement test case."""
	name = None
	tests = None
	succeeded = 0
	longer = None
	
	def __init__(self, name, deps):
		recipe.Recipe.__init__(self, [maat.path(name)], deps)
		self.tests = []
		self.name = name
		recipe.get_file(name).set_goal()
		global TEST_CASES
		TEST_CASES.append(self.ress[0])

	def add(self, test):
		self.tests.append(test)
		self.longer = max(self.longer, len(test.name))
	
	def action(self, ctx):
		#ctx.print_info("Testing %s" % self.ress[0])
		self.succeeded = 0
		for test in self.tests:
			test.test(ctx)
		if self.succeeded == len(self.tests):
			ctx.out.write(io.BOLD + io.GREEN + "\tSUCCESS: all tests passed!\n" + io.NORMAL)
		else:
			ctx.out.write(io.BOLD + io.RED + "\tFAILURE: %d tests failed on %d\n" % (len(self.tests) - self.succeeded, len(self.tests)) + io.NORMAL)
			common.error("Test failed.")


class Test(recipe.Recipe):
	"""Implements a simple test, that is, perform its action
	and depending on the result increment succeeded counter
	of test case."""
	case = None
	name = None
	displayed = False
	
	def __init__(self, case, name, deps):
		recipe.Recipe.__init__(self, [name], deps)
		self.name = name
		recipe.get_file(name).set_phony()
		self.case = case
		case.add(self)
		self.ress[0].set_goal()

	def success(self, ctx):
		"""Record the current test as a success and display
		ok message."""
		if not self.displayed:
			self.perform(ctx)
		self.case.succeeded += 1
		ctx.out.write(io.GREEN + "[OK]" + io.NORMAL + "\n")
	
	def failure(self, ctx, msg = ""):
		"""Record the current test as a failure display message."""
		if not self.displayed:
			self.perform(ctx)
		ctx.out.write(io.RED + "[FAILED]\n" + io.NORMAL)
		if msg:
			ctx.out.write(msg  + "\n")
	
	def perform(self, ctx):
		"""Display message of a starting test."""
		ctx.out.write("\tTesting %s%s\t" % (self.name, ' ' * (self.case.longer - len(self.name))))
		ctx.out.flush()
		self.displayed = True
	
	def info(self, ctx, msg):
		"""Display an information."""
		if self.displayed:
			ctx.out.write("\n")
			self.displayed = False
		ctx.out.write("\t%s\n" % msg)
	
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
		
		# launch the command
		if self.out:
			maat.mkdir(str(self.out.parent()))
			out_stream = open(str(self.out), "w")
		else:
			out_stream = NULL
		if self.err:
			maat.mkdir(str(self.err.parent()))
			err_stream = open(str(self.err), "w")
		else:
			err_stream = NULL
		if self.input:
			in_stream = open(str(self.input), "r")
		else:
			in_stream = NULL
		cmd = action.make_line(self.cmd)
		if maat.verbose:
			ctx.print_info("running %s" % cmd)
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
			if not os.path.exists(self.err_ref):
				self.info(ctx, "no reference file for error, creating it!")
				maat.mkdir(str(self.err_ref.parent()))
				shutil.copyfile(self.err, self.err_ref)
			else:
				c = 0
				for l in difflib.context_diff(open(self.err, "r").readlines(), open(self.err_ref, "r").readlines()):
					c += 1
				if c:
					self.failure(ctx, "different error stream")
					return
			
		# display result
		self.success(ctx)


class CommandTest(Test):
	"""A command test just run a command and examine the return code.
	If the return code is 0, the test is passed. Else the test is
	considered as failed."""
	
	def __init__(self, case, name, args, out = None, err = None, inp = None, deps = []):
		Test.__init__(self, case, name, deps)
		self.args = args
		self.inp = inp
		self.out = out
		self.err = err
	
	def check(self, rc):
		return rc == 0
	
	def test(self, ctx):
		self.perform(ctx)
		if self.out:
			maat.mkdir(str(self.out.parent()))
			out_stream = open(str(self.out), "w")
		else:
			out_stream = NULL
		if self.err:
			maat.mkdir(str(self.err.parent()))
			err_stream = open(str(self.err), "w")
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

class FailingCommandTest(CommandTest):
	"""Test launching a command and that succeed if the command fails."""

	def __init__(self, case, name, args, out = None, err = None, inp = None, deps = []):
		CommandTest.__init__(self, case, name, args, out, err, inp, deps)

	def check(self, rc):
		return rc <> 0


def case(name, deps = []):
	"""Build a test a case, that is, an abstract goal
	with a recipe launching tests."""
	return Case(name, deps)

def command(case, name, args, out = None, err = None, inp = None, deps = []):
	"""Build a command test that run the command and examine return code."""
	return CommandTest(case, name, args, out, err, inp, deps)

def failing_command(case, name, args, out = None, err = None, inp = None, deps = []):
	"""Build a command test that run the command and check from the return code if the command failed."""
	return FailingCommandTest(case, name, args, out, err, inp, deps)

def output(case, name, cmd, out = None, out_ref = None, err = None, err_ref = None, input = None, deps = []):
	"""Build a test that launches a command compares output."""
	return OutputTest(case, name, cmd, out, out_ref, err, err_ref, input, deps)

def post_init():
	"""Initialize the test goal."""
	path = env.cenv.path / "test"
	if not recipe.file_db.has_key(path):
		maat.goal("test", TEST_CASES)


maat.post_inits.append(maat.FunDelegate(post_init))
