"""Module providing test services."""
import elfmake
from elfmake import action
from elfmake import env
from elfmake import io
from elfmake import recipe
import difflib
import os
import os.path
import shutil
import subprocess

TEST_CASES = []

class Case(recipe.Recipe):
	"""Recipe to implement test case."""
	name = None
	tests = None
	succeeded = 0
	longer = None
	
	def __init__(self, name, deps):
		recipe.Recipe.__init__(self, [name], deps)
		self.tests = []
		self.name = name
		recipe.get_file(name).is_goal = True
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
			raise env.ElfError("Test failed.")


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
		recipe.get_file(name).is_goal = True
		self.case = case
		case.add(self)

	def success(self, ctx):
		"""Record the current test as a success and display
		ok message."""
		if not self.displayed:
			self.perform(ctx)
		self.case.succeeded += 1
		ctx.out.write(io.GREEN + "[OK]" + io.NORMAL + "\n")
	
	def failure(self, ctx):
		"""Record the current test as a failure display message."""
		if not self.displayed:
			self.perform(ctx)
		ctx.out.write(io.RED + "[FAILED]" + io.NORMAL + "\n")
	
	def perform(self, ctx):
		"""Display message of a starting test."""
		ctx.out.write("\tTesting %s%s\t" % (self.name, ' ' * (self.case.longer - len(self.name))))
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
		self.out = out
		self.out_ref = out_ref
		self.err = err
		self.err_ref = err_ref
		self.input = input
	
	def test(self, ctx):
		self.perform(ctx)
		displayed = True
		
		# launch the command
		if self.out:
			out_stream = open(self.out, "w")
		else:
			out_stream = open(os.devnull, "w")
		if self.err:
			err_stream = open(self.err, "w")
		else:
			err_stream = open(os.devnull, "w")
		if self.input:
			in_stream = open(input, "r")
		else:
			in_stream = None
		rc = subprocess.call(action.make_line(self.cmd), stdin = in_stream, stdout = out_stream, stderr = err_stream, shell = True)
		if rc <> 0:
			self.failure(ctx)
			return
			
		# compare output if any
		if self.out:
			if not os.path.exists(self.out_ref):
				self.info(ctx, "no reference file for output, creating it!")
				shutil.copyfile(self.out, self.out_ref)
			else:
				c = 0
				for l in difflib.context_diff(open(self.out, "r").readlines(), open(self.out_ref, "r").readlines()):
					c += 1
				if c:
					self.failure(ctx)
					return
		
		# compare error if any
		if self.err:
			if not os.path.exists(self.err_ref):
				self.info(ctx, "no reference file for error, creating it!")
				shutil.copyfile(self.err, self.err_ref)
			else:
				c = 0
				for l in difflib.context_diff(open(self.err, "r").readlines(), open(self.err_ref, "r").readlines()):
					c += 1
				if c:
					self.failure(ctx)
					return
			
		# display result
		self.success(ctx)
			

def case(name, deps = []):
	"""Build a test a case, that is, an abstract goal
	with a recipe launching tests."""
	return Case(name, deps)


def output(case, name, cmd, out = None, out_ref = None, err = None, err_ref = None, input = None, deps = []):
	"""Build a test that launches a command compares output."""
	return OutputTest(case, name, cmd, out, out_ref, err, err_ref, input, deps)

def post_init():
	"""Initialize the test goal."""
	path = env.cenv.path / "test"
	if not recipe.file_db.has_key(path):
		elfmake.goal("test", TEST_CASES)


elfmake.post_inits.append(post_init)
