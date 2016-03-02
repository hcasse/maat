"""Input/output management module for ElfMake tool."""
import sys

# ANSI coloration
NORMAL = "\033[0m"
"""Switch back console display to normal mode."""
BOLD = "\033[1m"
"""Switch console display to bold."""
FAINT = "\033[2m"
"""Switch console display to faint."""
ITALIC = "\033[3m"
"""Switch console display to italic."""
UNDERLINE = "\033[4m"
"""Switch console display to underline."""
BLACK = "\033[30m"
"""Switch console display to foreground black."""
RED = "\033[31m"
"""Switch console display to foreground red."""
GREEN = "\033[32m"
"""Switch console display to foreground green."""
YELLOW = "\033[33m"
"""Switch console display to foreground yellow."""
BLUE = "\033[34m"
"""Switch console display to foreground blue."""
MAGENTA = "\033[35m"
"""Switch console display to foreground magenta."""
CYAN = "\033[36m"
"""Switch console display to foreground cyan."""
WHITE = "\033[37m"
"""Switch console display to foreground white."""
BACK_BLACK = "\033[40m"
"""Switch console display to background black."""
BACK_RED = "\033[41m"
"""Switch console display to background red."""
BACK_GREEN = "\033[42m"
"""Switch console display to background green."""
BACK_YELLOW = "\033[43m"
"""Switch console display to background yellow."""
BACK_BLUE = "\033[44m"
"""Switch console display to background blue."""
BACK_MAGENTA = "\033[45m"
"""Switch console display to background magenta."""
BACK_CYAN = "\033[46m"
"""Switch console display to background cyan."""
BACK_WHITE = "\033[47m"
"""Switch console display to background white."""


# execution context
class NullStream:
	"""Stream that prints nothings."""
	
	def write(self, line):
		pass


null_stream = NullStream()

class Context:
	"""A context is used to configure the execution of an action."""
	out = sys.stdout
	err = sys.stderr
	command_ena = False
	info_ena = True
	quiet = False
	
	def print_command(self, cmd):
		"""Print a command before running it."""
		if not self.quiet and self.command_ena:
			sys.stdout.write(CYAN + "> " + str(cmd) + NORMAL + "\n")
	
	def print_info(self, info):
		"""Print information line about built target."""
		if not self.quiet and self.info_ena:
			sys.stdout.write(BOLD + BLUE + str(info) + NORMAL + "\n")

	def print_error(self, msg):
		"""Print an error message."""
		sys.stderr.write(BOLD + RED + "ERROR: " + str(msg) + NORMAL + "\n")
	
	def print_warning(self, msg):
		"""Print a warning message."""
		sys.stderr.write(BOLD + YELLOW + "WARNING: " + str(msg) + NORMAL + "\n")

	def print_success(self, msg):
		"""Print a success message."""
		sys.stderr.write(BOLD + GREEN + "SUCCESS: " + msg + str(NORMAL) + "\n")

	def print_action(self, msg):
		"""Print a beginning action."""
		if not self.quiet:
			sys.stdout.write("%s ... " % msg)
			sys.stdout.flush()
	
	def print_action_success(self, msg):
		"""End an action with success."""
		if not self.quiet:
			if msg:
				sys.stdout.write("(%s) " % msg)
			sys.stdout.write(GREEN + BOLD + "[0K]" + NORMAL)
			sys.stdout.write("\n");

	def print_action_failure(self, msg):
		"""End an action with failure."""
		if not self.quiet:
			if msg:
				sys.stdout.write("(%s) " % msg)
			sys.stdout.write(RED + BOLD + "[FAILED]" + NORMAL)
			sys.stdout.write("\n");

DEF = Context()
