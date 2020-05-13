import pathlib, enum
import upco_timecode

class Shot:

	class Media(enum.Enum):
		TAPE, FILE = ("Tape","File")

	SPECIAL_COLUMNS = ("Tape","Source File Name","Start","End","Duration")
		
	def __init__(self, shot, tc_start, tc_duration=None, tc_end=None, metadata=None, media=Media.TAPE, frm_rate=24000/1001):
		
		self.shot = shot
		self.frm_rate = frm_rate
		self.source = self.__class__.Media(media)
		self.metadata = {}
		self.tc_start = tc_start

		# Duration takes presidence over end TC if both are supplied
		if tc_duration is not None: self.tc_duration = tc_duration
		elif tc_end is not None: self.tc_end = tc_end
		else: raise ValueError("Either tc_duration or tc_end must be specified")

		if metadata: self.add_metadata(metadata)
	
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
	def add_metadata(self, metadata):	
		# Remove special columns
		self.metadata.update({key:val for key, val in metadata.items() if key not in self.__class__.SPECIAL_COLUMNS})
	
	def remove_metadata(self, metadata):
		if type(metadata) is dict:
			{self.metadata.pop(key) for key, val in metadata.items() if self.metadata.get(key) == val}
		else:
			self.metadata.pop(metadata, None)