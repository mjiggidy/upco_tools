# upco_timecode.py from upco_tools
# Library for manipulating, calculating,  makin' love to, and slappin' around timecode
# By Michael Jordan <michael.jordan@nbcuni.com>

import math, re

class Timecode:
	
	# CONSTRUCTOR =========================================
	# Build new Timecode object from timecode or framecount
	# Assumes a default framerate of 23.976 if not given
	# =====================================================
	
	def __init__(self, timecode=0, framerate=23.976):
		
		self.setFramerate(framerate)
		self.framecount   = 0
		
		if re.match(r"^[\+\-]?(\d+[:;]){0,3}\d+$", str(timecode)):
			# Deal with signed inputs
			timecode = str(timecode)
			neg = False
			if timecode.startswith('-'):
				neg = True
				timecode = timecode[1:]
			elif timecode.startswith('+'):
				timecode = timecode[1:]
			
			try:
				tc_split = tuple(int(x) for x in timecode.replace(';',':').split(':'))
				tc_split = (0,)*(4-len(tc_split)) + tuple(tc_split)
				assert len(tc_split) == 4
			except Exception as e: raise Exception("Invalid timecode input: {}".format(timecode))
					
			# Calculate framecount
			self.setFramecount(tc_split[3] + tc_split[2] * self.framerate_tc + tc_split[1] * self.framerate_tc * 60 + tc_split[0] * self.framerate_tc * 60 * 60)
			if neg: self.setFramecount(-self.getFramecount())
		
		else:
			raise Exception("No valid timecode or framecount provided.")
	
	# METHOD: Return formatted timecode when object is requested as string
	def __str__(self):
		return self.getTimecode()
		
	def __repr__(self):
		return self.getTimecode()
		

	# MATH OPERATIONS ================================
	# Overloading arithmetic and comparison operations
	# ================================================

	# METHOD: Add two timecodes
	def __add__(self, newtc):
		tc_add = self.validate(newtc)
		return self.__class__((self.getFramecount() + tc_add.getFramecount()), framerate=self.getFramerate())
	
	# METHOD: Subtract two timecocdes
	def __sub__(self, newtc):
		tc_sub = self.validate(newtc)
		return self.__class__((self.getFramecount() - tc_sub.getFramecount()), framerate=self.getFramerate())
	
	# METHODs: Comparisons (<, >, ==, etc)
	def __lt__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() < tc_cmp.getFramecount()
	
	def __le__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() <= tc_cmp.getFramecount()

	def __eq__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() == tc_cmp.getFramecount()

	def __ne__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() != tc_cmp.getFramecount()

	def __ge__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() >= tc_cmp.getFramecount()

	def __gt__(self, newtc):
		tc_cmp = self.validate(newtc)
		return self.getFramecount() > tc_cmp.getFramecount()
	
	# METHOD: Compare second TC object to ensure we can do math operations with it
	def validate(self, newtc):
		# Check if it's another timecode object
		if isinstance(newtc, self.__class__):
			tc_comp = newtc
		
		# Otherwise try parsing as a string, assuming matching framerate
		else:
			try: tc_comp = self.__class__(str(newtc), framerate=self.getFramerate())
			except Exception as e: raise Exception("Invalid timecode: Cannot operate on {}".format(newtc))
		
		# For now, only add common framerates.  Not sure how I want to handle conversions yet.
		if self.getFramerate() != tc_comp.getFramerate():
			raise Exception("Cannot operate on timecodes with mismatched framerates ({} fps vs {} fps)".format(self.getFramerate(), tc_comp.getFramerate()))
		
		return tc_comp
	
	# GETTERS & SETTERS ========
	
	# METHOD: Set framerate and "tc framerate" (rounded up from fractional framerate)
	def setFramerate(self, framerate):
		try:
			self.framerate = float(framerate)
			self.framerate_tc = int(math.ceil(self.framerate))
			if not self.framerate > 0: raise ValueError(f"Framerate must be greater than zero")
		except Exception as e: raise Exception(f"Invalid framerate input: {framerate} {e}")
	
	def setFramecount(self, framecount):
		try: self.framecount = int(round(framecount))
		except Exception as e: raise Exception("Invalid frame count: {}" .format(framecount))

	# METHOD: Return formatted timecode, with optional rollover at 24 hours
	def getTimecode(self, rollover=False, signed=True):
		
		# If we need to rollover timecode when it hits the 24-hour mark
		if rollover:
			framecount = abs(self.framecount) % (self.framerate_tc * 60 * 60 * 24)
		else:
			framecount = abs(self.framecount)
			
		# Show negative timecode unless we don't want it
		sign = '-' if self.framecount<0 and signed else ''
		
		tc_frames	= str(framecount % self.framerate_tc).zfill(2)
		tc_secs		= str(int(math.floor(framecount / self.framerate_tc)) % 60).zfill(2)
		tc_min		= str(int(math.floor(framecount / self.framerate_tc / 60) % 60)).zfill(2)
		tc_hour		= str(int(math.floor(framecount / self.framerate_tc / 60 / 60))).zfill(2)
		
		return sign + ':'.join((tc_hour,tc_min,tc_secs,tc_frames,))
		
	def getFramecount(self):
		return self.framecount
	
	def getFramerate(self, tc_rate=True):
		return self.framerate_tc if tc_rate else self.framerate
		
	# METHOD: Convert timecode to new framerate
	# Note that this returns a new object!
	def convertToFramerate(self, framerate):
		# Create copy of TC object
		tc_conv = self.__class__(self.getFramecount(), framerate=framerate)

		# Calculate conversion rate
		rate_conv = float(tc_conv.getFramerate(tc_rate=True)) / self.getFramerate(tc_rate=True)

		# Multiply frame count by the conversion rate
		tc_conv.setFramecount(tc_conv.getFramecount() * rate_conv)
		
		return tc_conv
