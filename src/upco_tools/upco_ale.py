# upco_timecode.py from upco_tools
# Library for creating, parsing, manipulating and writing Avid Log Exchange (ALE) files
# v2.0
# By Michael Jordan <michael.jordan@nbcuni.com>

import pathlib
from io import StringIO
from enum import Enum, auto

class ParseModes(Enum):
	START = auto()
	HEADING = auto()
	COLUMN = auto()
	DATA = auto()

class Ale:
	
	def __init__(self, path_input=None):
		"""
		Create or parse an existing Avid Log Exchange (ALE).

		Keyword Arguments:
			path_input {str|pathlib.Path} -- A valid path to an existing ALE to parse.  A new ALE will be created if this is not provided. (default: {None})

		Raises:
			Exception: Exceptions encountered when parsing an existing ALE

		Returns:
			self -- An ALE object
		"""
		
		self.path_input = None
		self.heading = {}
		self.columns = []
		self.shots = []

		# Parse existing ALE if provided
		if path_input:
			self.__parseAleFromFile(path_input)

		# Otherwise start with some basic columns
		else:
			self.heading.update({"FIELD_DELIM":"TABS", "VIDEO_FORMAT":"1080","AUDIO_FORMAT":"48khz","FPS":"23.976"})
			self.columns.extend(["Name","Tape","Start","Duration"])
	
	def addClips(self, *args, **kwargs):
		"""
		Add clips to ALE (legacy support).

		Recommended to use addShots() instead.
		addClips() is maintained for backward compatibility.  Clips can be supplied
		as one dictionary, a list of clips as dictionaries, or by supplying keyword
		arguments to define a clip.

		Raises:
			RuntimeError: Clip(s) supplied as an unknown format
		"""
		
		shots = [kwargs] if kwargs.keys() else []
		for arg in args:
			if type(arg) is list:
				shots.extend(arg)
			elif type(arg) is dict:
				shots.append(arg)
			else:
				raise RuntimeError(f"Invalid shot: {arg}")
		
		for shot in shots:
			{shot.update({x:str(shot.get(x))}) for x in shot.keys()}
			self.shots.append(shot)
			{self.columns.append(x) for x in shot.keys() if x not in self.columns}
	
	def getClips(self):
		"""
		Gets all clips in ALE as a list of dictionaries.

		Recommended to use getShots() instead.  getClips() is maintained for backward compatibility.

		Returns:
			list -- Lists of clips defined as dictionaries
		"""
		return self.shots	


	def __parseAleFromFile(self, path_input):
		"""
		Parse ALE from file.

		This should only be called from __init__().

		Arguments:
			path_input {str|pathlib.Path} -- Path of file to parse

		Raises:
			FileNotFoundError: ALE not found
			RuntimeError: ALE invalid
		"""
		
		self.path_input = pathlib.Path(path_input)
		if not self.path_input.is_file(): raise FileNotFoundError(f"{path_input} is not found")

		with self.path_input.open('r') as ale_input:

			parse_mode = ParseModes.START

			# Spin through ALE file line by line and parse ALE
			for line_num, line_data in enumerate(ale_input.read().splitlines()):
				
				# Skip empty lines
				if not line_data.strip():
					continue
				
				line_num += 1

				# Parse Data block (main thing) =====
				if parse_mode == ParseModes.DATA:
					
					shot_data = line_data.split('\t')
					
					# Freak out if column count doesn't match shot attribute count
					if len(shot_data) != len(self.columns):
						raise RuntimeError(f"Shot attribute count ({len(shot_data)}) does not match column count ({len(self.columns)}) on line {line_num}")

					# Add attributes that aren't empty
					self.addClips({self.columns[index]: shot_attrib for index,shot_attrib in enumerate(shot_data) if len(shot_attrib)})

				# Parse Heading block =====
				elif parse_mode == ParseModes.HEADING:
					
					if line_data.lower() == "column":
						parse_mode = ParseModes.COLUMN
						continue
					
					header = line_data.split('\t')
					self.heading.update({header[0]:header[1]})					
				
				# Parse Column names ======
				elif parse_mode == ParseModes.COLUMN:
					
					if line_data.lower() == "data":
						parse_mode = ParseModes.DATA
						continue

				#	Disabled existing column check due to default columns set
				# 	
				#	elif len(self.columns):
				#		raise RuntimeError(f"Unexpected column data on line {line_num}")
				
					else:
						self.columns = line_data.split('\t')

				# File parsing starts here =====
				elif parse_mode == ParseModes.START:
					if line_data.lower() == "heading":
						parse_mode = ParseModes.HEADING
						continue

					raise RuntimeError(f"Unexpected data before Heading on line {line_num}: {line_data}")
				
				# I don't think we'll ever get here but =====
				else:
					raise RuntimeError(f"Unexpected data on line {line_num}: {line_data}")

	# Remove empty columns while preserving column order
	def getPopulatedColumns(self):
		"""
		Get a list of column headings, excluding those which are defined but not used by any shots.

		Column order is preserved to maintain any structure that may have been preferred.

		Returns:
			list -- List of column headings
		"""

		# TODO: I feel like there's a more efficient way to do this
		
		# First build set of unique keys from all shots...
		used_columns = set()
		for shot in self.shots:
			{used_columns.add(x) for x in shot.keys()}
			
		# ...then return them in the correct order
		return [x for x in self.columns if x in used_columns]

	def __buildAle(self, stream_output, preserveEmptyColumns=False, omitColumns=None):
		"""
		Private method to write formatted ALE to output stream.

		Arguments:
			stream_output {iostream} -- Output stream (can be file or something like StringIO)

		Keyword Arguments:
			preserveEmptyColumns {bool} -- Include column names that are defined but not used by any shots (default: {False})
			omitColumns {iter} -- Provide a list of columns to leave out of the formatted ALE (default: {None})

		Raises:
			RuntimeError: Invalid options set

		Returns:
			iostream -- The stream that was being written
		"""

		# Remove empty or omitted columns
		used_columns = self.columns if preserveEmptyColumns else self.getPopulatedColumns()

		if type(omitColumns) is list:
			{used_columns.remove(x) for x in omitColumns if x in used_columns}
		elif omitColumns:
			raise RuntimeError("omitColumns must be a list")

		# Build heading
		print("Heading", file=stream_output)
		{print(f"{key}\t{self.heading.get(key,'')}", file=stream_output) for key in self.heading.keys()}
		print("", file=stream_output)

		print("Column", file=stream_output)
		print('\t'.join(used_columns), file=stream_output)
		print("", file=stream_output)

		print("Data", file=stream_output)
		for shot in self.shots: print('\t'.join(str(shot.get(col,"")) for col in used_columns), file=stream_output)
		print("", file=stream_output)

		return stream_output

	def getAle(self, preserveEmptyColumns=False, omitColumns=None) -> str:
		"""
		Format and build the ALE as a string.

		Keyword Arguments:
			preserveEmptyColumns {bool} -- Preserve column headers that are empty for all shots (default: {False})
			omitColumns {list} -- Omit specified column headers and data (default: {None})

		Returns:
			str -- Formatted ALE
		"""

		string_output = StringIO()
		self.__buildAle(string_output, preserveEmptyColumns, omitColumns)
		return string_output.getvalue()
		
	def writeAle(self, path_output, preserveEmptyColumns=False, omitColumns=None):
		"""
		Format and write the ALE to disk

		Arguments:
			path_output {str|pathlib.Path} -- Path of file to output

		Keyword Arguments:
			preserveEmptyColumns {bool} -- Preserve column headers that are empty for all shots (default: {False})
			omitColumns {list} -- Omit specified column headers and data (default: {None})

		Raises:
			Exception: Any exceptions related to file output

		Returns:
			pathlib.Path -- Path of the written file
		"""

		path_output = pathlib.Path(path_output)
		
		with path_output.open('w') as file_output:
			self.__buildAle(file_output, preserveEmptyColumns, omitColumns)

		return path_output
