# upco_filesequence from upco_tools
# Library for grouping files by sequence (ie shot.[008600-008643].dpx)
# By Michael Jordan <michael.jordan@nbcuni.com>

import pathlib, re
#import upco_timecode

class Sequencer:

	pattern_sequence = re.compile(r"^(?P<basename>.*?)(?P<index>\d+)$")

	def __init__(self, pathlist):

		self.sequences = []

		for path in sorted(pathlib.Path(path) for path in pathlist):
			self.__addSequence(path)

	def __addSequence(self, path):

		match = self.__class__.pattern_sequence.match(path.stem)

		if not match:
			# TODO: Catalog non-sequenced files
			self.sequences.append(FileSequence(path.parent, path.stem, 0, 0, path.suffix))
		
		else:
			parent   = path.parent
			basename = match.group("basename")
			index    = int(match.group("index"))
			padding  = len(match.group("index"))
			ext      = path.suffix

			# Compare to previous sequence, if there is one
			seq = self.sequences[-1] if len(self.sequences) else None
			if seq and seq.parent == parent and seq.basename == basename and seq.max+1 == index and seq.padding == padding and seq.ext == ext:
				self.sequences[-1].max += 1

			else:
				self.sequences.append(FileSequence(parent, basename, index, padding, ext))

	def list(self, expanded=False):
		return [seq.grouped() for seq in self.sequences]

class FileSequence:

	def __init__(self, parent, basename, index, padding, ext):

		self.parent   = pathlib.Path(parent)
		self.basename = str(basename)
		self.padding  = int(padding)
		self.ext	  = str(ext)

		self.min = self.max = int(index)
	
	def __str__(self):
		return str(self.grouped())

	def grouped(self):
		if self.isSingle():
			return pathlib.Path(self.parent, f"{self.basename}{self.ext}")
		else:
			return pathlib.Path(self.parent, f"{self.basename}[{str(self.min).zfill(self.padding)}-{str(self.max).zfill(self.padding)}]{self.ext}")
	
	def expand(self):
		if self.isSingle() and self.padding == 0:
			expanded = [pathlib.Path(self.parent, f"{self.basename}{self.ext}")]

		else:
			expanded = []
			for idx in range(self.min, self.max):
				expanded.append(pathlib.Path(self.parent, f"{self.basename}{str(idx).zfill(self.padding)}{self.ext}"))
		
		return expanded

	def isSingle(self):
		return self.min == self.max


