"""Input/output management module for ElfMake tool."""
import sys

# ANSI coloration
NORMAL = "\033[0m"
BOLD = "\033[1m"
FAINT = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BACK_BLACK = "\033[40m"
BACK_RED = "\033[41m"
BACK_GREEN = "\033[42m"
BACK_YELLOW = "\033[43m"
BACK_BLUE = "\033[44m"
BACK_MAGENTA = "\033[45m"
BACK_CYAN = "\033[46m"
BACK_WHITE = "\033[47m"


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
			sys.stdout.write(CYAN + "> " + cmd + NORMAL + "\n")
	
	def print_info(self, info):
		"""Print information line about built target."""
		if not self.quiet and self.info_ena:
			sys.stdout.write(BOLD + BLUE + info + NORMAL + "\n")

	def print_error(self, msg):
		"""Print an error message."""
		sys.stderr.write(BOLD + RED + "ERROR: " + msg + NORMAL + "\n")
	
	def print_warning(self, msg):
		"""Print a warning message."""
		sys.stderr.write(BOLD + YELLOW + "WARNING: " + msg + NORMAL + "\n")

	def print_success(self, msg):
		"""Print a success message."""
		sys.stderr.write(BOLD + GREEN + "SUCCESS: " + msg + NORMAL + "\n")
