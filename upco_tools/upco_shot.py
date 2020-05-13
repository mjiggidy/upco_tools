import pathlib, enum
import upco_timecode

class Shot:

	class Source(enum.Enum):
		TAPE, FILE = ("Tape","File")

	SPECIAL_COLUMNS = ("Tape","Source File Name","Start","End","Duration")
		
	def __init__(self, shot, tc_start, tc_duration=None, tc_end=None, metadata=None, source=Source.TAPE, frm_rate=24000/1001):
		
		self.shot = shot
		self.frm_rate = frm_rate
		self.source = self.__class__.Source(source)
		self.metadata = {}
		
		self.set_tc_start(tc_start)

		# Duration takes presidence over end TC if both are supplied
		self.set_tc_duration(tc_duration) if tc_duration else self.set_tc_end(tc_end)

		if metadata: self.add_metadata(metadata)


	def set_tc_start(self, tc_start):
		self.tc_start = upco_timecode.Timecode(tc_start, self.frm_rate)
	
	def set_tc_duration(self, tc_duration):
		self.tc_duration = upco_timecode.Timecode(tc_duration)
	
	def set_tc_end(self, tc_end):
		tc_end = upco_timecode.Timecode(tc_end, self.frm_rate)
		if self.tc_start < tc_end:
			self.set_tc_duration(tc_end - self.tc_start)
		else:
			raise ValueError(f"TC End {tc_end} must not preceed TC Start {self.tc_start}")

	def add_metadata(self, metadata):	
		# Remove special columns
		self.metadata.update({key:val for key, val in metadata.items() if key not in self.__class__.SPECIAL_COLUMNS})
	
	def remove_metadata(self, metadata):
		if type(metadata) is dict:
			{self.metadata.pop(key) for key, val in metadata.items() if self.metadata.get(key) == val}
		else:
			self.metadata.pop(metadata, None)