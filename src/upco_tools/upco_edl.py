import pathlib, re
import upco_timecode


class Edl:
	
	class Event:
		
		# Regex for parsing events
		pattern_cut = re.compile(r"^(?P<event_number>\d+)\s+(?P<reel_name>[^\s]+)\s+(?P<track_type>A[%\s]*|B|V)\s+(?P<event_type>C|D|W\d+|K\s*[BO])\s+(?P<event_duration>\d*)\s+(?P<tc_src_in>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_src_out>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_rec_in>\d{2}:\d{2}:\d{2}:\d{2})\s+(?P<tc_rec_out>\d{2}:\d{2}:\d{2}:\d{2})\s*$", re.I)
		
		def __init__(self, event):

			self.edits = []
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

		def addComment(self, comment):
			self.comments.append(comment)

			# Check for special comments if we have edits that they can apply to
			if len(self.edits):
				if "from clip name" in comment.lower():
					self.edits[0].update({"clip_name": comment.split(':')[1].strip()})
				elif "to clip name" in comment.lower():
					self.edits[-1].update({"clip_name": comment.split(':')[1].strip()})


		def getSources(self):
			return list(set([x.get("source") for x in self.edits if "source" in x.keys()]))
		
		def getSubclips(self):
			return [{"shot":x.get("source"), "tc_in": x.get("src_tc_in"), "tc_out":x.get("src_tc_out"), "clip_name":x.get("clip_name",x.get("source"))} for x in self.edits]
		
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

	def __init__(self, path_edl=None):

		self.event_number_padding = 6
		#self.tc_start = upco_timecode.Timecode("23:00:00:00")
		self.tc_duration = upco_timecode.Timecode()
		self.edl_title = "Untitled EDL"
		self.edl_fcm = "NON-DROP FRAME"
		self.events = []
		self.path_edl = None

		if path_edl:
			self.parseEdlFile(path_edl)
		
	# Load EDL from file if specified
	def parseEdlFile(self, path_edl):
		
		# Verify EDL path
		try:
			self.path_edl = pathlib.Path(path_edl)
			if not self.path_edl.exists(): raise FileNotFoundError("File does not exist")
		except Exception as e:
			raise e

		# Parse each line in the EDL and add to events list
		with self.path_edl.open("r") as file_edl:

			last_event = None

			for line in file_edl.read().splitlines():

				if self.__class__.Event.pattern_cut.match(line):
					last_event = self.addEvent(self.__class__.Event.pattern_cut.match(line))

				elif line.strip().startswith('*') and last_event:
					last_event.addComment(line)
					
					
	def addEvent(self, event):

		event_index = int(event.group("event_number"))

		# If this is part of an existing event, check it in
		if event_index in self.events:
			self.events[self.events.index(event_index)].addEdit(event)
		
		# Otherwise add it as a new event
		else:
			self.events.append(self.__class__.Event(event))
		
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

		with path_output.open('w') as edl_output:

			edl_output.write(f"TITLE: {self.edl_title}\n")
			edl_output.write(f"FCM: {self.edl_fcm}\n")

			for event in self.events:
				
				for edit in event.edits:
					edl_output.write(f"{str(event.event_number).zfill(3)}  ")
					edl_output.write(f"{edit.get('source','').ljust(32)} ")
					edl_output.write(f"{edit.get('track_type','V').ljust(6)} ")
					edl_output.write(f"{edit.get('event_type','').ljust(6)} ")
					edl_output.write(f"{edit.get('event_duration','').ljust(3)} ")
					edl_output.write(f"{edit.get('src_tc_in')} {edit.get('src_tc_out')} ")
					edl_output.write(f"{edit.get('rec_tc_in')} {edit.get('rec_tc_out')} ")
					edl_output.write('\n')
				
				for comment in event.comments:
					edl_output.write(f"{comment}\n")
			
				edl_output.write("\n")



if __name__ == "__main__":

	try:
		edl = Edl("test_edl.edl")
	except Exception as e:
		print(f"Havin problems: {e}")
	
	edl.printEdl()

	print(f"Sources: {edl.getSources()}")
	print(f"TC Bounds: {edl.getStartTC()} - {edl.getEndTC()}")
