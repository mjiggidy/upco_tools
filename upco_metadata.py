# upco_metadata.py
# Parse embedded metadata from media files, such as tape name, timecode, and framerate
# By Michael Jordan <michael.jordan@nbcuni.com>

from upco_tools import upco_timecode
import subprocess, json, pathlib

# On import, find ffprobe
def find_ffprobe(input_path=None):

	if input_path:
		searchpaths = [input_path]
	else:
		searchpaths = ["/usr/local/bin/ffprobe", r"C:\ffmpeg\bin\ffprobe.exe"]

	for searchpath in searchpaths:
		try:
			searchpath = pathlib.Path(searchpath)
		except: pass
		
		if searchpath.exists() and searchpath.is_file():
			return searchpath
	
	raise Exception("Could not find ffprobe on this system.")

path_ffprobe = find_ffprobe()

# ------
# CLASS: Metadata
# Parses ffprobe output
# ------

class Metadata:
	
	def __init__(self, path_input):

		self.path_ffprobe = path_ffprobe
		self.path = None
		
		self.hasvideo	 = False
		self.hasaudio	 = False
		self.hastimecode = False
		self.hastapename = False
		
		self.video = {}
		self.audio = {}
		self.timecode = {}
		self.ffprobe = {}
		
		# Verify input path is valid and exists
		try:
			path_input = pathlib.Path(path_input)
		except Exception as e:
			raise e

		if not path_input.exists():
			raise Exception("File does not exist or is inaccessible")

		self.path = path_input
		
		# Run ffprobe and retrieve output as JSON
		try:
			ffprobe_json = subprocess.Popen([str(self.path_ffprobe), "-v","quiet", "-print_format","json", "-show_format", "-show_streams", str(path_input)], stdout=subprocess.PIPE)
		except Exception as e:
			raise Exception(f"Error launching ffprobe: {e}")
		
		# Parse JSON into dict
		try:
			ffprobe_parsed = json.loads(ffprobe_json.communicate()[0])
		except Exception as e:
			raise Exception(f"Error parsing metadata: {e}")
		
		self.ffprobe = ffprobe_parsed
		
		# Pull info from streams
		if not len(ffprobe_parsed.get("streams",'')):
			raise Exception("No video, audio, or data streams were found in this file.")
		
		for stream in ffprobe_parsed.get("streams"):
			
			if "codec_type" not in stream.keys():
				continue
			
			# Process video properties (and skip if a video track has already been parsed)
			if stream.get("codec_type").lower() == "video" and not self.hasvideo:
				
				self.hasvideo = True
				self.video.update({"width":int(stream.get("width",'')), "height":int(stream.get("height",''))})
				
				if "r_frame_rate" in stream.keys() and '/' in stream.get("r_frame_rate"):
					fps_split = stream.get("r_frame_rate").split('/')
					self.video.update({"framerate":float(fps_split[0])/int(fps_split[1])})
				
				if "nb_frames" in stream.keys():
					self.video.update({"framecount": int(stream.get("nb_frames",''))})
					
				if "bits_per_raw_sample" in stream.keys():
					self.video.update({"bitdepth": float(stream.get("bits_per_raw_sample",''))})
			
			# Process metadata (Tape name, timecode, etc)
			elif stream.get("codec_type").lower() == "data" and "tags" in stream.keys():

				if stream.get("tags").get("reel_name",'') and not self.video.get("tape",''):
					self.video.update({"tape":str(stream.get("tags").get("reel_name"))})
				
				if stream.get("tags").get("timecode",'') and not self.hastimecode:
					
					self.hastimecode = True
					self.video.update({"tc_start":str(stream.get("tags").get("timecode"))})
		
		# Figure out what's here
		self.hastapename = ("tape" in self.video.keys() and len(self.video.get("tape").strip()))
		self.hastimecode = all(x in self.video.keys() for x in ["tc_start","framecount","framerate"])
		
		# Process end timecode from parsed metadata
		if not self.hastimecode and "framecount" in self.video.keys() and "framerate" in self.video.keys():
			self.video.update({"tc_start":"00:00:00:00"})
		
		try:
			tc_start = upco_timecode.Timecode(self.video.get("tc_start"), self.video.get("framerate", 23.976))
			tc_end = tc_start + upco_timecode.Timecode(self.video.get("framecount",0), self.video.get("framerate",23.976))
			self.video.update({"tc_start":tc_start, "tc_end":tc_end})
		except Exception as e:
			# Deal with invalid timecodes here
			raise Exception(f"Error parsing timecode: {e}")