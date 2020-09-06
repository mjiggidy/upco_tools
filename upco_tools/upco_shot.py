import pathlib, enum, re, csv
from io import StringIO
from . import upco_timecode, upco_edl

class Shotlist:
	"""Maintain a list of shots with support for common exchange formats"""

	class _AleParseModes(enum.Enum):
		START = enum.auto()
		HEADING = enum.auto()
		COLUMN = enum.auto()
		DATA = enum.auto()

	@classmethod
	def fromALE(cls, path_input):
		"""
		Build a Shotlist instance by parsing an ALE.

		Arguments:
			path_input {str|pathlib.Path} -- Path of file to parse

		Raises:
			FileNotFoundError: ALE not found
			SyntaxError: ALE invalid
		
		Returns:
			{Shotlist} -- Shotlist object from ALE
		"""
		
		path_input = pathlib.Path(path_input)
		if not path_input.is_file(): raise FileNotFoundError(f"{path_input} is not found")

		ale_heading = {}
		shotlist = cls()

		with path_input.open('r') as ale_input:

			parsed_columns = []
			parse_mode = cls._AleParseModes.START
			

			# Spin through ALE file line by line and parse ALE
			for line_num, line_data in enumerate(ale_input.read().splitlines()):
				
				# Skip empty lines
				if not line_data.strip():
					continue
				
				line_num += 1

				# Parse Data block (main thing) =====
				if parse_mode == cls._AleParseModes.DATA:
					
					shot_data = line_data.split('\t')
					
					# Freak out if column count doesn't match shot attribute count
					if len(shot_data) != len(parsed_columns):
						raise SyntaxError(f"Shot attribute count ({len(shot_data)}) does not match column count ({len(parsed_columns)}) on line {line_num}")

					# Prepare shot
					metadata = {parsed_columns[index]: shot_attrib for index,shot_attrib in enumerate(shot_data) if len(shot_attrib)}
					if metadata.get("Tape"):
						shot_name = metadata.get("Tape")
						shot_type = Shot.MediaType("Tape")
					elif metadata.get("Source File Name"):
						shot_name = metadata.get("Source File Name")
						shot_type = Shot.MediaType("File")
					else:
						raise ValueError(f"No Tape or Source File Name found for shot on line {line_num}")
					
					# Check for 24-hour rollover in tc_end if no tc duration
					if not metadata.get("Duration"):
						if not metadata.get("End"):
							raise ValueError(f"No end timecode specified for shot on line {line_num}")
						
						try:
							fps = ale_heading.get("FPS", 24000/1001)
							metadata["Start"] = upco_timecode.Timecode(metadata.get("Start"), fps)
							metadata["End"]   = upco_timecode.Timecode(metadata.get("End"), fps)
							while metadata.get("End") < metadata.get("Start"):
								metadata["End"] += upco_timecode.Timecode("24:00:00:00", fps)
						except Exception as e:
							raise ValueError(f"Invalid timecode for shot on line {line_num} ({e})")
						
					# Add shot to shotlist
					masterclip = Shot(
						shot_name,
						tc_start    = metadata.get("Start"),
						tc_duration = metadata.get("Duration"),
						tc_end      = metadata.get("End"),
						#metadata    = metadata,
						media       = shot_type,
						#source      = path_input,
						frm_rate    = ale_heading.get("FPS")
					)
					masterclip.addMetadata(metadata)
					shotlist.addShot(masterclip)

				# Parse Heading block =====
				elif parse_mode == cls._AleParseModes.HEADING:
					
					if line_data.lower() == "column":
						parse_mode = cls._AleParseModes.COLUMN
						continue
					
					header = line_data.split('\t')
					ale_heading.update({header[0]:header[1]})
				
				# Parse Column names ======
				elif parse_mode == cls._AleParseModes.COLUMN:
					
					if line_data.lower() == "data":
						parse_mode = cls._AleParseModes.DATA
						continue

					elif len(parsed_columns):
						raise SyntaxError(f"Unexpected data encounered on line {line_num}:\n{line_data}")
				
					else:
						parsed_columns = line_data.split('\t')
						
						# Check for duplicate column names
						dupes = {col for col in parsed_columns if parsed_columns.count(col) > 1}
						if dupes:
							raise SyntaxError(f"Found duplicate column names on line {line_num}:\n{','.join(dupes)}")

				# File parsing starts here =====
				elif parse_mode == cls._AleParseModes.START:
					if line_data.lower() == "heading":
						parse_mode = cls._AleParseModes.HEADING
						continue

					raise SyntaxError(f"Unexpected data before Heading on line {line_num}:\n{line_data}")
				
				# I don't think we'll ever get here but =====
				else:
					raise SyntaxError(f"Unexpected data on line {line_num}: {line_data}")
		
		return shotlist

	@classmethod
	def fromEDL(cls, path_input):
		
		shotlist = cls()
		
		edl = upco_edl.Edl.fromEdl(path_input)
		for shot in edl.getSubclips():
			shotlist.addShot(shot)
		
		return shotlist

	@classmethod
	def fromCSV(cls, path_input):

		shotlist = cls()

		path_input = pathlib.Path(path_input)
		if not path_input.is_file(): raise FileNotFoundError(f"{path_input} is not found")

		required_rows = ("Reel Name","Frame Rate","Start TC","Duration TC")

		# TODO: Verify file encoding before parsing
		with path_input.open('r', encoding="utf-16") as file_csv:
			for num_row, row in enumerate(csv.DictReader(file_csv)):
				if not all(required_rows):
					raise ValueError(f"Missing column data for {', '.join(x for x in required_rows if row.get(x) is None)} on line {num_row+2}")
				
				shot = Shot(
					shot = row.get("Reel Name"),
					tc_start = row.get("Start TC"),
					tc_duration = row.get("Duration TC"),
					frm_rate = row.get("Frame Rate")
				)

				shot.addMetadata({x:row.get(x) for x in row.keys() if x not in required_rows})

				shotlist.addShot(shot)
		
		return shotlist
	
	def __init__(self, shotlist=None):
		"""
		Create or parse an existing Avid Log Exchange (ALE).

		Keyword Arguments:
			path_input {str|pathlib.Path} -- A valid path to an existing ALE to parse.  A new ALE will be created if this is not provided. (default: {None})

		Raises:
			Exception: Exceptions encountered when parsing an existing ALE

		Returns:
			self -- An ALE object
		"""

		self.shots = []
		if shotlist: self.addShot(shotlist)


	def addShot(self, shot):

		self.shots.append(shot)
		
	
	def getClips(self):
		"""
		Gets all clips in ALE as a list of dictionaries.

		Recommended to use getShots() instead.  getClips() is maintained for backward compatibility.

		Returns:
			list -- Lists of clips defined as dictionaries
		"""
		return self.shots	


	def _buildAle(self, stream_output, preserveEmptyColumns=False, omitColumns=None, heading={"FIELD_DELIM":"TABS","VIDEO_FORMAT":1080,"FPS":23.98}, sourcecol="Tape"):
		"""
		Private method to write formatted ALE to output stream.

		Arguments:
			stream_output {iostream} -- Output stream (can be file or something like StringIO)

		Keyword Arguments:
			preserveEmptyColumns {bool} -- Include column names that are defined but not used by any shots (default: {False})
			omitColumns {iter} -- Provide a list of columns to leave out of the formatted ALE (default: {None})

		Raises:
			ValueError: Invalid options set

		Returns:
			iostream -- The stream that was being written
		"""
		used_columns = ["Name",sourcecol,"Start","Duration","End"]
		meta_columns = []
		pat_invalid  = re.compile("[\t\r\n]+")
		
		# Build case-insensitive list of unique metadata columns from all shots
		# Omit blank columns
		# TODO: Find a more elegant way to do this
		for shot in self.shots:
			for col in shot.metadata.keys():
				if col.lower() not in [x.lower() for x in meta_columns] and col.lower() not in [x.lower() for x in used_columns] and shot.metadata.get(col).strip() != "":
					meta_columns.append(col)
		
		used_columns.extend(sorted(meta_columns))

		#print(used_columns)

		if type(omitColumns) is list:
			{used_columns.remove(x) for x in omitColumns if x in used_columns}
		elif omitColumns:
			raise ValueError("omitColumns must be a list")

		# Build heading
		print("Heading", file=stream_output)
		{print(f"{key}\t{heading.get(key,'')}", file=stream_output) for key in heading.keys()}
		print("", file=stream_output)

		print("Column", file=stream_output)
		print('\t'.join(used_columns), file=stream_output)
		print("", file=stream_output)

		print("Data", file=stream_output)
		
		# TODO: Clean tabs or newlines from data
		for shot in self.shots:
		
			# TODO: Deep copy metadata dict? Or handle in shot.getMetadata()?
			metadata = shot.metadata
			metadata.update({sourcecol:shot.shot, "Start":shot.tc_start, "End":shot.tc_end, "Duration":shot.tc_duration})
			
			# Deal with special columns
			if "Name" in used_columns:									# Name is currently a default column but could be specified as an omitted_column
				metadata["Name"] = metadata.get("Name", shot.shot)		# Name gets tape name if none is specified
			
			if "Tracks" in used_columns:
				#print("Adding tracks to ", shot.shot)
				metadata["Tracks"] = metadata.get("Tracks","VA1A2")	# Tracks get default V1/A1A2 if none is specified

			# Convert keys to lower case for case-insensitive column header matching
			metadata = {x.lower(): metadata.get(x) for x in metadata.keys()}
			
			# Write to file
			print('\t'.join(pat_invalid.sub("  ", str(metadata.get(col.lower(),""))) for col in used_columns), file=stream_output)
		
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
		self._buildAle(string_output, preserveEmptyColumns, omitColumns)
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
		
		with path_output.open('w', encoding="utf-8") as file_output:
			self._buildAle(file_output, preserveEmptyColumns, omitColumns)

		return path_output

class Shot:
	"""Defines a shot"""

	class MediaType(enum.Enum):
		"""Indicates legacy Avid Tape-based workflow vs File-based with Source File Name"""
		TAPE, FILE = ("Tape","File")

	# Meaningful columns to be omitted from generic metadata dict
	SPECIAL_COLUMNS = ("Tape","Source File Name","Start","End","Duration")

	# Common OCN naming conventions
	# TODO: May want to expand this into a dictionary eg. {Camera.ARRI, matchPattern} so a Shot can have a cameraType property
	# TODO: May remove this for now
	NAMING_PATTERNS = (re.compile(x, re.I) for x in (
		r"(?P<camroll>[a-z][0-9]{3})(?P<clipindex>c[0-9]{3})_(?P<year>[0-9]{2})(?P<month>[0-9]{2})(?P<day>[0-9]{2})_(?P<camindex>[a-z])(?P<camid>[a-z0-9]{3})",	# Arri
		r"(?P<camroll>[a-z][0-9]{3})_(?P<clipindex>[c,l,r][0-9]{3})_(?P<month>[0-9]{2})(?P<day>[0-9]{2})(?P<camid>[a-z0-9]{2})",								# Redcode/Venice
		r"(?P<camroll>[a-z][0-9]{3})(?P<clipindex>[c,l,r][0-9]{3})_(?P<year>[0-9]{2})(?P<month>[0-9]{2})(?P<day>[0-9]{2})(?P<camid>[a-z0-9]{2})",				# Sony Raw
		r"(?P<camroll>[a-z][0-9]{3})_(?P<month>[0-9]{2})(?P<day>[0-9]{2})(?P<hour>[0-9]{2})(?P<minute>[0-9]{2})_(?P<clipindex>C[0-9]{3})",						# Black Magic Cinema Camera
		r"(?P<camroll>[A-Z]{1,3}\d{3})_S\d{3}_S\d{3}_(?P<clipindex>T\d{3})",	# Drone/Helicopter
		r"(?P<camroll>[A-Z]\d{3})(?P<clipindex>(G[A-Z]\d{3,})",					# GoPro Footage
		r"(?P<camroll>[A-Z]\d{3})_(?P<clipindex>P\d{3,})",						# Panasonic Lumix
		r"IMG_(?P<clipindex>[0-9]+)",											# iPhone/DSLR
		r"DJI_(?P<clipindex>[0-9]+)",											# DJI Drones
		r"MVI_(?P<clipindex>[0-9]+)",											# Consumer cameras
		r"(?P<labroll>CA35_\d{3})",												# 35mm Labroll (Company 3 UK)
		r"(?P<labroll>[A-Z]\d{3})_DPX",											# 35mm Labroll (Generic)
		r"(?P<labroll>LR\d{8})"													# 35mm Labroll (Efilm)
	))
		
	def __init__(self, shot, tc_start, tc_duration=None, tc_end=None, media=MediaType.TAPE, frm_rate=24000/1001, metadata=None):
		
		self.shot       = str(shot)							# Shot name (ex A001C003_200711_R1CB)
		self.frm_rate   = float(frm_rate)					# Video frame rate
		self.media_type = self.__class__.MediaType(media)	# Avid Tape or Source File Name column.  May need some rethinking
		self.metadata   = {}								# Non-critical metadata (Processed below)
		self.tc_start   = tc_start							# Timecode start (accompanied by Timecode duration/end below)

		# Duration takes presidence over end TC if both are supplied
		if tc_duration is not None: self.tc_duration = tc_duration
		elif tc_end is not None: self.tc_end = tc_end
		else: raise ValueError("Either tc_duration or tc_end must be specified")

		# Validate and add metadata
		if metadata is not None: self.addMetadata(metadata)
	
	# Timecode properties
	@property
	def tc_start(self):
		return self._tc_start	
	@tc_start.setter
	def tc_start(self, tc_start):
		self._tc_start = upco_timecode.Timecode(tc_start, self.frm_rate)

	@property
	def tc_duration(self):
		return self._tc_duration
	@tc_duration.setter
	def tc_duration(self, tc_duration):
		self._tc_duration = upco_timecode.Timecode(tc_duration, self.frm_rate)
	
	@property
	def tc_end(self):
		return self.tc_start + self.tc_duration
	@tc_end.setter
	def tc_end(self, tc_end):
		tc_end = upco_timecode.Timecode(tc_end, self.frm_rate)
		if self.tc_start < tc_end:
			self.tc_duration = tc_end - self.tc_start
		else:
			raise ValueError(f"TC End {tc_end} must not precede TC Start {self.tc_start}")

	# TODO: Look in to making these @properties as well
	def addMetadata(self, metadata):	
		# Remove special columns
		self.metadata.update({key:val for key, val in metadata.items() if key not in self.__class__.SPECIAL_COLUMNS})
	
	def removeMetadata(self, metadata):
		if type(metadata) is dict:
			{self.metadata.pop(key) for key, val in metadata.items() if self.metadata.get(key) == val}
		else:
			self.metadata.pop(metadata, None)
	
	def __eq__(self, cmp):
		
		try:
			return all((cmp.shot == self.shot, cmp.tc_start == self.tc_start, cmp.tc_duration == self.tc_duration))
		except Exception:
		#	print(e)
			return False