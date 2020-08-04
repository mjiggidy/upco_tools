import pathlib, re
from . import upco_timecode, upco_shot


class Edl:
	
	class _Event:
		
		# Regex for parsing events
		pattern_cut    = re.compile(r"^(?P<event_number>\d+)\s+(?P<reel_name>[^\s]+)\s+(?P<track_type>A[%\s]*|B|V)\s+(?P<event_type>C|D|W\d+|K\s*[BO]?)\s+(?P<event_duration>\d*)\s+(?P<tc_src_in>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_src_out>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_rec_in>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_rec_out>\d{2}:\d{2}:\d{2}:\d{2})\s*$", re.I)
		pattern_motion = re.compile(r"^(?P<speed_type>M\d+)\s+(?P<reel_name>[^\s]+)\s+(?P<frame_rate>[+-]?(\d+)?\.?\d+)\s+(?P<tc_start>\d{2}:\d{2}:\d{2}:\d{2})")

		def __init__(self, event):

			self.edits = []
			self.motion = []
			self.comments = []

			# Try parsing this sucker again if it wasn't already
			# Really this shouldn't be allowed though.
			if type(event) != re.Match:
				try:
					self.event_match = self.__class__.pattern_cut.match(event)
				except Exception as e:
					raise e
			else:
				self.event_match = event
			
			# Set event number
			self.event_number = int(self.event_match.group("event_number"))
			self.addEdit(event)

		def addEdit(self, edit):
			self.edits.append({"source":edit.group("reel_name"), "track": edit.group("track_type"), "event_type": edit.group("event_type"), "event_duration": edit.group("event_duration"), "src_tc_in": upco_timecode.Timecode(edit.group("tc_src_in")), "src_tc_out":upco_timecode.Timecode(edit.group("tc_src_out")), "rec_tc_in":upco_timecode.Timecode(edit.group("tc_rec_in")), "rec_tc_out":upco_timecode.Timecode(edit.group("tc_rec_out"))})

		def addMotionEffect(self, effect):
			self.motion.append({"type": effect.group("speed_type"), "source": effect.group("reel_name"), "frame_rate": float(effect.group("frame_rate")), "tc_start": upco_timecode.Timecode(effect.group("tc_start"))})

		def addComment(self, comment):
			self.comments.append(comment)

			# Check for special comments if we have edits that they can apply to
			if len(self.edits):
				if "from clip name" in comment.lower():
					self.edits[0].update({"clip_name": comment.split(':',1)[1].strip()})
				elif "to clip name" in comment.lower() or "key clip name" in comment.lower():
					self.edits[-1].update({"clip_name": comment.split(':',1)[1].strip()})


		def getSources(self):
			return list(set([x.get("source") for x in self.edits if "source" in x.keys()]))
		
		def getSubclips(self):

			subclips = []

			for idx, edit in enumerate(self.edits):
				
				# If clip is first in a transition, calculate its end TC from the duration of the wipe on the next clip
				if edit.get("src_tc_in") == edit.get("src_tc_out"):
					if idx < len(self.edits)-1 and self.edits[idx+1].get("event_duration"):
						tc_out = edit.get("src_tc_in") + int(self.edits[idx+1].get("event_duration"))
					else:
						raise ValueError(f"Error parsing event #{self.event_number}: Source is zero frames in length")
				
				# Otherwise, keep as-is
				else:
					tc_out = edit.get("src_tc_out")

				metadata = {"Name":edit.get("clip_name")} if edit.get("clip_name") else {}

				
				subclips.append(upco_shot.Shot(shot=edit.get("source"), tc_start=edit.get("src_tc_in"), tc_end=tc_out, metadata=metadata))
			
			return subclips
			#return [{"shot":x.get("source"), "tc_in": x.get("src_tc_in"), "tc_out":x.get("src_tc_out"), "clip_name":x.get("clip_name",x.get("source"))} for x in self.edits]
		
		def getStartTC(self):
			return min(x.get("rec_tc_in") for x in self.edits)
		
		def getEndTC(self):
			return max(x.get("rec_tc_out") for x in self.edits)

		def getDuration(self):
			tc = upco_timecode.Timecode()
			for edit in self.edits:
				tc += (edit.get("src_tc_out") - edit.get("src_tc_in"))
			return tc
		
		# Event is defined by its event number
		def __eq__(self, cmp):
			return cmp == self.event_number

		def __str__(self):
			final = []
			for edit in self.edits:
				line =  f"{str(self.event_number).zfill(6)}  "
				line += f"{edit.get('source','').ljust(32)} "
				line += f"{edit.get('track_type','V').ljust(6)} "
				line += f"{edit.get('event_type','').ljust(6)} "
				line += f"{edit.get('event_duration','').ljust(3)} "
				line += f"{edit.get('src_tc_in')} {edit.get('src_tc_out')} "
				line += f"{edit.get('rec_tc_in')} {edit.get('rec_tc_out')} "
				final.append(line)
			
			for m in self.motion:
				line =  f"{m.get('type').ljust(7)} "
				line += f"{m.get('source').ljust(42)} "
				line += f"{m.get('frame_rate')} "
				line += f"{m.get('tc_start')} "
				final.append(line)
			
			for comment in self.comments:
				final.append(f"{comment}")
			
			return '\n'.join(final)

	# Load EDL from file if specified
	@classmethod
	def fromEdl(cls, path_edl):
		"""Parse an EDL file into an Edl object

		Args:
			path_edl (str|pathlib.Path): Valid path to an input EDL

		Raises:
			FileNotFoundError: Invalid or non-existent path to EDL
			RuntimeError: EDL contains syntax errors

		Returns:
			Edl: Edl object
		"""
		
		# Verify EDL path
		path_edl = pathlib.Path(path_edl)
		if not path_edl.exists(): raise FileNotFoundError("File does not exist")

		edl = cls()

		# Parse each line in the EDL and add to events list
		with path_edl.open("r", encoding="utf-8") as file_edl:

			last_event = None

			for linenum, line in enumerate(file_edl):
				line = line.rstrip('\n')

				try:
					# Line describes a standard edit
					if cls._Event.pattern_cut.match(line):
						last_event = edl.addEvent(cls._Event.pattern_cut.match(line))

					# Line describes a motion effect
					elif cls._Event.pattern_motion.match(line):
						last_event.addMotionEffect(cls._Event.pattern_motion.match(line))

					# Line is a comment
					elif line.strip().startswith('*') and last_event:
						last_event.addComment(line)
					
				#	else:
				#		print(f"Din match line {linenum}:\n{line}")
				
				except Exception as e:
					raise RuntimeError(f"Error parsing EDL on line {linenum}: {e}\nLine: {line}")

		if not len(edl.events):
			raise RuntimeError(f"{path_edl.name} does not appear to be a valid EDL file.")
			
		return edl

	def __init__(self):

		self.event_number_padding = 6
		self.tc_duration = upco_timecode.Timecode()
		self.edl_title = "Untitled EDL"
		self.edl_fcm = "NON-DROP FRAME"
		self.events = []
		self.path_edl = None
					
	def addEvent(self, event):

		event_index = int(event.group("event_number"))

		# If this is part of an existing event, check it in
		if event_index in self.events:
			self.events[self.events.index(event_index)].addEdit(event)
		
		# Otherwise add it as a new event
		else:
			self.events.append(self.__class__._Event(event))
		
		return self.events[self.events.index(event_index)] if event_index in self.events else None
	
	def getSources(self):
		sources = []
		for event in self.events:
			sources.extend(event.getSources())
		return list(set(sources))

	def getSubclips(self):
		clips = []
		for event in self.events:
			clips.extend(event.getSubclips())
		return clips
	
	def getStartTC(self):
		return min(x.getStartTC() for x in self.events)
	
	def getEndTC(self):
		return max(x.getEndTC() for x in self.events)
	
	def printEdl(self):
		#tc = upco_timecode.Timecode("01:00:00:00")

		for event in self.events:

			print(f"Event #{event.event_number} lasts {event.getStartTC()} - {event.getEndTC()}:")
			for edit in event.edits:
				print(edit)
			print("\n")
			#tc += event.getDuration()


	def writeEdl(self, path_output=None):

		if not path_output:
			path_output = pathlib.Path("out.edl")
		else:
			path_output = pathlib.Path(path_output)

		with path_output.open('w', encoding="utf-8") as edl_output:

			edl_output.write(f"TITLE: {self.edl_title}\n")
			edl_output.write(f"FCM: {self.edl_fcm}\n")

			edl_output.write("\n\n".join(str(event) for event in self.events))
		
		return path_output



if __name__ == "__main__":

	try:
		edl = Edl.fromEdl("test_edl.edl")
	except Exception as e:
		print(f"Havin problems: {e}")
	
	edl.printEdl()

	print(f"Sources: {edl.getSources()}")
	print(f"TC Bounds: {edl.getStartTC()} - {edl.getEndTC()}")
