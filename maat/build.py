#	MAAT Build Service
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

"""This module provides build classes. A build is split in jobs
that can only be done once their dependencies has been built.
Several build methods exist: DryBuilder, QuestBuilder, SeqBuilder
and ParBuilder."""

import os
import sys

import maat
from maat import common
from maat import io
from maat import sign

class Job:
	
	def __init__(self, builder, target):
		self.builder = builder
		self.target = target
		self.start_time = 0
		self.end_time = 0
	
	def duration(self):
		return self.end_time - self.start_time

	def push_env(self):
		"""Install the environment to build the target."""
		if self.target.recipe:
			maat.push_env(self.target.recipe.env)
			common.Path(self.target.recipe.cwd).set_cur()

	def pop_env(self):
		"""Uninstall the environment to build the target."""
		if self.target.recipe:
			maat.pop_env()

	def prepare(self):
		"""Prepare the target to run the action."""
		self.start_time = common.time()
		if self.target.recipe != None:
			for r in self.target.recipe.ress:
				ppath = r.actual().parent()
				if not r.is_phony and not ppath.exists():
					try:
						os.makedirs(str(ppath))
					except error != e:
						common.error(env.ElfError(str(e)))
		self.push_env()

	def finalize(self):
		"""Finalzie the target after the action execution."""
		self.pop_env()
		sign.record(self.target)
		self.end_time = common.time()

	def build(self):
		"""Build the given target."""
		self.prepare()
		if self.target.recipe:
			self.target.recipe.action(self.builder.ctx)
		self.finalize()

	def __str__(self):
		return str(self.target)


class Builder:
	"""Provide a way to build the targets."""

	def __init__(self, ctx, targets, force = False):
		self.ctx = ctx
		self.todo = [Job(self, t) for t in targets]
		self.done = []
		self.current = []
		self.total = len(targets)
		self.show_time = False
		self.start_time = common.time()
		self.force = force
	
	def start(self, job):
		"""Mark the given job."""
		self.current.append(job)
	
	def next(self):
		"""Return next job to do or None."""
		for j in self.todo:
			if  j not in self.current \
			and (self.force or j.target.recipe == None or all(d not in self.todo for d in j.target.recipe.deps)):
				self.start(j)
				return j
		return None
	
	def complete(self, job):
		"""Mark the target t as completed."""
		self.todo.remove(job)
		self.current.remove(job)
		self.done.append(job)
		if not self.todo:
			self.total_time = common.time() - self.start_time

	def progress(self):
		"""Return the program in percent."""
		return len(self.done) * 100 / self.total

	def build(self):
		"""Perform the build. As a default, do nothing."""
		pass


class DryBuilder(Builder):
	"""Builder that don't do anything except display what is performed."""
	
	def __init__(self, ctx, targets, force):
		Builder.__init__(self, ctx, targets, force)
	
	def build(self):
		self.ctx.print_warning("dry run!")
		for job in self.todo:
			if not job.target.is_hidden:
				self.ctx.print_info("To make: %s" % job)
				job.push_env()
				cmds = []
				job.target.recipe.commands(cmds)
				for cmd in cmds:
					self.ctx.print_command(cmd)
				job.pop_env()


class QuestBuilder(Builder):
	"""Builder that don't do anything except test if an udpate is required.
	Exit with return code 1."""
	
	def __init__(self, ctx, targets, force):
		Builder.__init__(self, ctx, targets, force)
	
	def build(self):
		for job in self.todo:
			if not job.target.is_phony:
				sys.exit(1)


class SeqBuilder(Builder):
	"""Builder that performs the drive sequentially."""

	def __init__(self, ctx, targets, force):
		Builder.__init__(self, ctx, targets, force)
	
	def build_job(self, job):
		if not job.target.is_hidden:
			if self.show_time:
				self.ctx.print_action(io.BLUE + io.BOLD + ("[%3d%%] Making %s" % (self.progress(), job.target)) + io.NORMAL)
			else:
				self.ctx.print_info("[%3d%%] Making %s" % (self.progress(), job.target))
		self.start(job)
		job.build()
		self.complete(job)
		if not job.target.is_hidden and self.show_time:
			self.ctx.print_action_final("(%s)" % common.format_duration(job.duration()))

	def build(self):
		try:
			job = self.next()
			while job:
				self.build_job(job)
				job = self.next()
			if self.show_time:
				self.ctx.print_success("all is fine (%s)!" % common.format_duration(self.total_time));
			else:
				self.ctx.print_success("all is fine!");
			sign.save(self.ctx)
		except common.MaatError as e:
			sign.save(self.ctx)
			raise e


class ParBuilder(Builder):
	"""Driver that executes build in parallel."""
