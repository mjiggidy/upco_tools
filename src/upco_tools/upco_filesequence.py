# upco_filesequence from upco_tools
# Library for grouping files by sequence (ie shot.[008600-008643].dpx)
# By Michael Jordan <michael.jordan@nbcuni.com>

import pathlib, re
#import upco_timecode

class FileSequence:

	pattern_sequence = re.compile(r"^(?<basename>.*)(?<index>\d+)$")

	def __init__(self, pathlist):

		self.sequences = []

		for path in sorted(pathlib.Path(path) for path in pathlist):
			self.__addSequence(path)

	def __addSequence(self, path):

		match = self.__class__.pattern_sequence.match(path)

		if not match:
			# TODO: Catalog non-sequenced files
			#self.sequences.append(self.__class__.GroupedFiles(path))
			pass
		
		else:
			parent   = path.parent
			basename = match.get("basename")
			index    = int(match.get("index"))
			padding  = len(match.get("index"))
			ext      = path.suffix

			# Compare to previous sequence, if there is one
			seq = self.sequences[-1]
			if seq and seq.parent == parent and seq.basename == basename and seq.max+1 == index and seq.padding == padding and seq.ext == ext:
				self.sequences[-1].max += 1

			else:
				self.sequences.append(self.__class__.GroupedFiles(parent, basename, index, padding, ext))


	class GroupedFiles:

		def __init(self, parent, basename, index, padding, ext):

			self.parent   = pathlib.Path(parent)
			self.basename = str(basename)
			self.index    = int(index)
			self.padding  = int(padding)
			self.ext	  = str(ext)

			self.min = self.max = self.index
		
		def __str__(self):

			if self.isSingle():
				return str(self.parent, f"{self.basename}{self.ext}")
			else:
				return str(self.parent, f"{self.basename}[{str(self.min).zfill(self.padding)}-[{str(self.max).zfill(self.padding)}]{self.ext}")

		def isSingle(self):
			return self.min == self.max


