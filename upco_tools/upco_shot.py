class Shot:
	class Type(enum.Enum):
		DIR, FILE = ("Directory", "File")
		
	def __init__(self, shot, fromlist="Custom", alts=None):
		
		self.shot = shot
		self.alts = alts
		self.size = None
		self.tape = None
		self.from_list  = fromlist
		

	def getSize(self):
		return sum([x.get("size",0) for x in self.filelist])
	
	def getStartblock(self):
		if len(self.filelist):
			return min([x.get("startblock",0) for x in self.filelist])
		else:
			return 0

	def setPath(self, *args, **kwargs):

		try: self.basepath = pathlib.Path(kwargs.get("basepath", '/'))
		except Exception as e: raise Exception("Invalid path for shot {}: {}".format(kwargs.get("basepath",''), str(e)))
		
		try: self.tape = kwargs.get("tape")
		except Exception as e: raise Exception("No source schema specified for shot")
		
		self.shot = kwargs.get("shot", self.shot)
		self.type = kwargs.get("type", self.__class__.Type.DIR)
		self.filelist = kwargs.get("filelist",[])
		
		
		self.startblock = self.getStartblock()


	def __eq__(self, cmp):
		try: return str(cmp) == self.shot and cmp.getStartblock() == self.getStartblock()
		except Exception as e: return False
	
	def __str__(self):
		return self.shot
	
	def getShot(self):
		return self.shot if self.shot else "Unknown Shot"

	def getTape(self):
		return self.tape if self.tape else "Unknown"
	
	def getMediaType(self):
		#if self.type == self.__class__.Type.FILE:
		#	if self.path and self.path.suffix: return self.path.suffix
		#	else: return "Unknown (1)"
		
		#elif self.type == self.__class__.Type.DIR:
		if len(self.filelist):
			ext = ', '.join(set(x.get("path").suffix.lower() for x in self.filelist))
			if len(ext): return ext
			else: return "Unknown (2)"
		else:
			return "Unknown (3)"
	
	# Alias
	def getFormattedSize(self):
		return self.getSizeAsString()
	
	def getSizeAsString(self):

		size = self.getSize()

		if size is None:
			return "Unknown"
		elif size < (1024*1024):
			return "{:.2f} KB".format(size/(1024))
		elif size < (1024*1024*1024):
			return "{:.2f} MB".format(size/(1024*1024))
		else:
			return "{:.2f} GB".format(size/(1024*1024*1024))
