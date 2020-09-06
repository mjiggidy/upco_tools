# upco_ltfs.py from upco_tools
# Library for managing LTFS tapes, and the shots on them
# By Michael Jordan <michael@glowingpixel.com>

from xml.etree import cElementTree as ElementTree
from . import upco_shot
import enum, operator, subprocess, time, pathlib, sqlite3
import signal

# CLASS: Tape ================================================================
# A Tape object represents an LTFS-formatted LTO tape and its list of Shots
# With minimal functionality to mount an unmount, very much a work in progress
class Tape:
	class Density(enum.Enum):
		LTO6, LTO7, LTO8 = range(6,9)
		
		def __str__(self):
			return "LTO-{}".format(self.value)
	
	class Status(enum.Enum):
		LTFS_INACTIVE, LTFS_INIT, LTFS_ACTIVE, INSERT_TAPE, MOUNTED, TAPE_EJECTED, EJECT_ERROR = range(0,7)
		
	def __init__(self, name, density=6, dev_name=None, mount_point=None):
		self.name = name
		
		self.dev_name = dev_name
		self.mount_point = mount_point
		
		self.ltfs_status = self.Status.LTFS_INACTIVE
		self.shotlist = []
		
		self.density = self.__class__.Density(density)
	
	def __str__(self):
		return self.name
	
	def __eq__(self, cmp):
		try:
			return str(cmp) == self.name
			
		except Exception:
			return False
	
	def __lt__(self, cmp):
		if type(cmp) == self.__class__:
			return len(self.shotlist) < len(cmp.shotlist)
		else:
			raise TypeError
	
	def __gt__(self,cmp):
		if type(cmp) == self.__class__:
			return len(self.shotlist) > len(cmp.shotlist)
		else:
			raise TypeError
	
	def setMountPoint(self, mount_point):
		try:
			self.mount_point = pathlib.Path(mount_point)
		except Exception as e:
			self.mount_point = None
		
	def setDevice(self, dev_name):
		self.dev_name = dev_name
	
	def mount(self, mount_point=None, dev_name=None):
	
		if mount_point is not None: self.setMountPoint(mount_point)
		if dev_name is not None: self.setDevice(dev_name)
		
		if not self.mount_point or not self.dev_name:
			raise Exception("No mount point or device name specified.")
		
		path_ltfsbin = pathlib.Path(r"C:\Program Files\HPE\LTFS\ltfs.exe")
		if not path_ltfsbin.exists(): raise Exception(f"LTFS binary not found at {path_ltfsbin}")
		
		self.ltfs_exec = subprocess.Popen([
			str(path_ltfsbin), str(self.mount_point),		# ltfs.exe G:
			"-o","devname={}".format(self.dev_name),		# machine name; ex TAPE0
			"-o","ro",										# mount as read-only
			"-o","eject",									# eject after process is terminated
			"-o","show_offline",							# mark files offline in explorer (prevents thumbnailing)
			"-d"],											# run in debug mode
			creationflags = subprocess.CREATE_NEW_PROCESS_GROUP,	# allows sending signal to child process tree
			universal_newlines = True,						# PIPEs running in text mode
			bufsize = 1, 									# line buffering
			shell = True,									# probably unnecessary
			stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			
		if self.ltfs_exec.poll() is None:
			self.ltfs_status = self.Status.LTFS_INIT
		else:
			raise Exception("LTFS driver could not not be loaded: {}".format(self.ltfs_exec.poll()))
		
		return self.ltfs_status
		
		
	def mount_status(self):
		
		# LTFS hasn't started yet
		if self.ltfs_status == self.Status.LTFS_INACTIVE:
			return self.ltfs_status
		
		# LTFS has exited
		elif self.ltfs_exec.poll() is not None:
			self.ltfs_status = self.Status.LTFS_INACTIVE
			return self.ltfs_status
			
		# LTFS has just started
		if self.ltfs_status == self.Status.LTFS_INIT:

			# Wait for final line of LTFS startup messages
			while "LTFS14113I" not in self.ltfs_exec.stderr.readline():
				continue

			self.ltfs_status = self.Status.LTFS_ACTIVE
			return self.ltfs_status
		
		# If OS has access to the tape (might not be the best thing here...)
		try:
			print("In mountpoint check")

			if self.mount_point.exists():
				print("Found it")
				self.ltfs_status = self.Status.MOUNTED

				print("Reading line...")
				print(self.ltfs_exec.stderr.readline())

				return self.ltfs_status

		except Exception as e:
			print(f"Passing on OS error: {e}... ehhhh...")
			pass
		
		print("Didn't find it")
		time.sleep(5)
			
		self.ltfs_status = self.Status.INSERT_TAPE
		return self.ltfs_status
		
	
	def unmount(self):
		try:
			if self.mount_status() == self.Status.LTFS_INACTIVE:
				print("LTFS is not started")
				return self.Status.LTFS_INACTIVE
		except Exception as e:
			if self.ltfs_status == self.Status.LTFS_INACTIVE:
				return self.ltfs_status
			else:
				pass
		
		
		print("Now unmounting {}".format(self.mount_point))
		
		try:
#			Here's where it goes to shit
#			os.kill(self.ltfs_exec.pid, signal.CTRL_C_EVENT)
			# Wait 30 sec and get stderr output
			stat = self.ltfs_exec.communicate(timeout=30)[1]
		#except TimeoutExpired:
		#	print("Timed out waiting for ltfs to clean up...")
		
		except KeyboardInterrupt:
			print("Caught interrupt")
			
		except Exception as e:
			print("Exception: {}".format(e))
			subprocess.call(["taskkill","/f","/t","/pid",str(self.ltfs_exec.pid)])
			self.ltfs_status = self.Status.EJECT_ERROR
			return self.ltfs_status


		self.ltfs_status = self.Status.TAPE_EJECTED
		return self.ltfs_status
		#self.ltfs_status = self.Status.LTFS_INACTIVE
		
		
		
		
		
		#print("Killed with code {}".self.ltfs_exec.returncode)
		#print(self.ltfs_exec.stdout.read())
		
		
		
# CLASS: Shot =============================================================
# A Shot object represents a full camera raw shot on a Tape
# Not much going on here now, but I'll want to flesh this out in the future
class CameraRawPull:
	class Type(enum.Enum):
		DIR, FILE = ("Directory", "File")
		
	def __init__(self, shot, fromlist="Custom", alts=None):
		
		self.shot = shot
		self.alts = alts or []
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
		try:
			return str(cmp) == self.shot and cmp.getStartblock() == self.getStartblock()
		except Exception:
			return False
	
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
			
# CLASS: Schema ================================================
# Parses the schema representation of a Tape from a .schema file
# Also contains functions for indexing Shots
class Schema:
	LTFS_BASE_DIR	= "LTFS VOLUME"
	LTFS_NODE_ROOT = "ltfsindex"

	def __init__(self, path_schema, debug=False):
		self.debug = debug
		# For now let's assume this baby already exists and we're reading it in
		if not isinstance(path_schema, pathlib.Path):
			try:
				path_schema = pathlib.Path(path_schema)
			except Exception as e:
				raise Exception(f"Problem with schema path: {e}")
		self.path_schema = path_schema
		
		# Attempt to parse this succuh
		try:
			self.parseSchema()
		except Exception as e:
			raise Exception(f"Problem parsing schema: {e}")
		
	# FUNC: parseSchema - Parses XML, validates as LTFS schema, and grabs the root node
	# Called by constructor.  Maybe grab more properties in the future (LTO flavor, which we'll need to do now that I'm thinking about it)
	def parseSchema(self):
		try:
			with open(self.path_schema, 'r') as xml_file:
				self.schema_parsed = ElementTree.parse(xml_file)
		except Exception as e:
			raise Exception("This does not appear to be a valid XML file: {}".format(e))

		# Validate schema
		if self.schema_parsed.getroot().tag != self.__class__.LTFS_NODE_ROOT:
			raise Exception("This XML file does not appear to be a valid LTFS schema: Expected root node \"{}\", found \"{}\" instead.".format(self.__class__.LTFS_NODE_ROOT, self.schema_parsed.getroot().tag))
		
		# Get initial info about this schema: LTO Volume Label and a handle into its root directory
		self.schema_volume = self.schema_parsed.getroot().tag
		self.schema_root = self.schema_parsed.getroot().find("directory/contents")
	
	def getSchemaName(self):
		return self.path_schema.stem
	
	# FUNC: walkSchema
	# Prints a directory listing to std out.  Intended mainly for debugging purposes.
	def walkSchema(self, current_node=None, path=pathlib.Path("/")):
		
		filelist = []

		# TODO: Might need that "Skip over volume name" section up here to modify path
		# I think I messed it up, I dunno.  Look in to it some time.

		# If no node was given, start at the root of the tape
		if not current_node:
			if self.debug: print("Resetting node root")
			current_node = self.schema_root
		
		# Get files in current directory
		for file in current_node.findall("file"):
			if self.debug: print(path, file.find("name").text)
			try:
				filename = file.find("name").text
				filelist.append({
					"path": path/filename,
					"size": int(file.find("length").text),
					"startblock": int(file.find("extentinfo/extent/startblock").text)
				})
			except Exception as e:
				print(f"Omitting file {filename}: Incomplete file entry in schema ({e})")
				continue

			if self.debug: print(f"Added {filelist[-1].get('path')}")

		# Get list of subdirectories and recursively walk those files as well
		for directory in current_node.findall("directory"):
			dirname = directory.find("name").text
			
			if self.debug: print(path / dirname)
			
			# Skip over volume name
			if dirname == self.__class__.LTFS_BASE_DIR:
				path = pathlib.Path('/')	# Start building pull path with the root directory (/)
				
			# Enter subdirectory if it isn't empty
			subdir = directory.find("contents")
			if subdir:
				filelist.extend(self.walkSchema(subdir, path/dirname))
			else:
				if self.debug: print("Empty directory encountered; backing out.")
	
		# Sort file list by startblock
		if len(filelist):
			filelist = sorted(filelist, key=lambda x: x.get("startblock",0))

		return filelist
	
	def findAllShots(self, shot_name=None, tape_patterns=None, current_node=None, path=pathlib.Path(), file_extensions=(".ari",".r3d",".dpx",".dng",".cine",".braw", ".mov",".mxf",".mp4")):
		
		import re

		shots = []
		
		templates_tape = tape_patterns or (
				r"[a-z][0-9]{3}c[0-9]{3}_[0-9]{6}_[a-z][a-z0-9]{3}",	# ArriRAW
				r"[a-z][0-9]{3}_[c,l,r][0-9]{3}_[0-9]{4}[a-z0-9]{2}",	# Redcode
				r"[a-z][0-9]{3}[c,l,r][0-9]{3}_[0-9]{6}[a-z0-9]{2}",	# Sony Raw
				r"[a-z][0-9]{3}_[0-9]{8}_C[0-9]{3}",					# Black Magic Cinema Camera
				r"IMG_[0-9]+",											# iPhone/DSLR
				r"DJI_[0-9]+",											# DJI Drones
				r"MVI_[0-9]+",											# Consumer cameras
				r"[A-Z]\d{3}G[A-Z]\d{3,}",								# GoPro Footage (Nobody)
				r"[A-Z]\d{3}_P\d{3,}",									# Panasonic Lumix (Nobody)
				r"LR\d{8}",												# Fast 9 35mm
				r"CA35_\d{3}",											# Fast 9 35mm
				r"D[A-Z]\d{3}_S\d{3}_S\d{3}_T\d{3}",					# Fast 9 Drone
				r"[A-Z]\d{3}_DPX"										# Fast 9 Crash Cam
			)

		patterns_tape = {re.compile(pat, re.I) for pat in templates_tape}

		#for pattern in patterns_tape: print(pattern)

		if not isinstance(path, pathlib.Path):
			try: path = pathlib.Path(path)
			except Exception as e: raise Exception(f"Invalid LTO search path: {e}")

		if not current_node: current_node = self.schema_root
		
		# Get all subdirectories
		nodes = current_node.findall("directory")
		
		# Loop through each directory
		for node in nodes:
			
			
			dirname = node.find("name").text
			
	
			# Skip over volume name
			if dirname == self.__class__.LTFS_BASE_DIR:
				path = pathlib.Path('/')	# Start building pull path with the root directory (/)
			
			match = False
			
			# If this directory's name matches tape name, assume it's an image sequence and restore the full directory
			if shot_name is not None:
				match = dirname.lower().startswith(shot_name.lower())
			else:
				for pat in patterns_tape:
					match = pat.match(dirname)
					if match:
						match_name = match.group(0)
						break

			# If pattern matched directory name
			if match:
			
				# Gather file listing
				filelist = self.walkSchema(node.find("contents"), pathlib.Path('.'))
				#print(filelist)

				# Walk file tree to get stats
				#print(f"Found {len(filelist)} files in {pathlib.Path(path, dirname)}: {[x.get('size') for x in filelist]}")
				#size = sum([x.get("size") for x in filelist])
				
				try: startblock = min([x.get("startblock") for x in filelist])
				except Exception as e:
					print(f"Freaked the fuck out at {pathlib.Path(path,dirname)}")
					print(f"Found files:")
					print(filelist)
					exit()
				
				
				shot = CameraRawPull(shot_name)
				shot.setPath(basepath=pathlib.Path(path, dirname), type=CameraRawPull.Type.DIR, filelist=filelist, tape=Tape(self.getSchemaName()))
				
				shots.append(shot)
				continue
			
			# Otherwise, loop through each file in directory
			for file in node.findall("contents/file"):
				filestring = file.find("name").text
				
				if shot_name is not None:
					match = filestring.lower().startswith(shot_name.lower())
					match_name = shot_name
				else:
					for pat in patterns_tape:
						match = pat.match(filestring)
						if match:
							match_name = match.group(0)
							break
					

				if match and filestring.lower().endswith(file_extensions):
				
					try:
						startblock = int(file.find("extentinfo/extent/startblock").text)
						bytecount  = int(file.find("length").text)
					except:
						# If file lacks startblock or bytecount info, set it to 0 just to avoid errors down the road
						# I don't think a file would even be visible on LTFS without this info, but who knows 
						if self.debug: print("Shot found in schema, but has missing extentinfo.  Restore may have difficulties.", shot.shot, "warning")
						startblock = 0
						bytecount = 0
					
					shot = CameraRawPull(match_name)
					shot.setPath(basepath=pathlib.Path(path,dirname), type=CameraRawPull.Type.FILE, filelist=[{"path": pathlib.Path(filestring) ,"size": int(bytecount), "startblock": startblock}], tape=Tape(self.getSchemaName()))
					shots.append(shot)
			
			# Search subdirectories.  If it's found in there, break out of the loop to return the result
			dircontents = node.find("contents")
			if dircontents:
				shots.extend(self.findAllShots(shot_name=shot_name, current_node=dircontents, tape_patterns=templates_tape, path=path/dirname))
			
			# Break out after first match
			# Commented out so we can find a larger filesize later on in the schema
			# if result: break

		return shots

	# UPDATE: Once shot is found, the active schema will continue to be searched for more matches with larger file sizes.  Largest will be returned.
	# With shows like "You Should Have Left," I've been seeing DNX115 MXFs found before camera raw MXFs, and this is the best fix I can think of.
	# Better could be to add support for Yoyotta xattrib tags (com.yoyotta.ch.codec), but that wouldn't be a universal solution.
	def findShot(self, shot, current_node=None, path=pathlib.Path(), file_extensions=(".ari",".r3d",".dpx",".dng",".cine",".braw",".mov",".mxf"), bestmatch=None):
		
		if not isinstance(path, pathlib.Path):
			try: path = pathlib.Path(path)
			except Exception as e: raise Exception(f"Invalid LTO search path: {e}")

		if not current_node: current_node = self.schema_root
		
		# Get all subdirectories
		nodes = current_node.findall("directory")
		
		# Loop through each directory
		for node in nodes:
			dirname = node.find("name").text
			
			if self.debug: print("Lookin' at {}".format(dirname))
			# Skip over volume name
			if dirname == self.__class__.LTFS_BASE_DIR:
				path = pathlib.Path('/')	# Start building pull path with the root directory (/)
			
			# If this directory's name matches tape name, assume it's an image sequence and restore the full directory
			if dirname.lower().startswith(shot.shot.lower()):
				
				# Gather file listing
				filelist = self.walkSchema(node.find("contents"), pathlib.Path('.'))
				#print(filelist)

				# Walk file tree to get stats
				#print(f"Found {len(filelist)} files in {pathlib.Path(path, dirname)}: {[x.get('size') for x in filelist]}")
				size = sum([x.get("size") for x in filelist])
				startblock = min([x.get("startblock") for x in filelist])
				
				# If we have a previous match, and the previous match has a larger filesize, stick with it
				if bestmatch is not None and bestmatch.getSize() > size:
					return bestmatch
								
				shot.setPath(basepath=pathlib.Path(path, dirname), type=CameraRawPull.Type.DIR, filelist=filelist, tape=Tape(self.getSchemaName()))
				return shot
			
			# Otherwise, loop through each file in directory
			for file in node.findall("contents/file"):

				try:
					filename = pathlib.Path(file.find("name").text)
				except Exception as e:
					raise Exception(f"Error parsing filename on LTO: {e}")

				# If filename is a match and has acceptable file extension
				if filename.stem.lower() == shot.shot.lower() and filename.suffix.lower() in file_extensions:
					try:
						startblock = int(file.find("extentinfo/extent/startblock").text)
						bytecount  = int(file.find("length").text)
					except:
						# If file lacks startblock or bytecount info, set it to 0 just to avoid errors down the road
						# I don't think a file would even be visible on LTFS without this info, but who knows 
						if self.debug: print("Shot found in schema, but has missing extentinfo.  Restore may have difficulties.", shot.shot, "warning")
						startblock = 0
						bytecount = 0
						
					# If a previous match has a larger filesize, stick with the larger one
					if bestmatch is not None and bestmatch.getSize() > int(bytecount):
						return bestmatch

					shot.setPath(basepath=pathlib.Path(path,dirname), type=CameraRawPull.Type.FILE, filelist=[{"path": pathlib.Path(filename) ,"size": int(bytecount), "startblock": startblock}], tape=Tape(self.getSchemaName()))
					return shot
			
			# Search subdirectories.  If it's found in there, break out of the loop to return the result
			dircontents = node.find("contents")
			if dircontents:
				bestmatch = self.findShot(shot, dircontents, path/dirname, bestmatch=bestmatch)
			
			# Break out after first match
			# Commented out so we can find a larger filesize later on in the schema
			# if result: break

		return bestmatch

# CLASS: ShotsDB =============================================================
# sqlite3 database containing shots per LTO per show
# In progress; not to be used quite yet

class ShotDB:

	def __init__(self, path_db):
		
		# Validate path
		try:
			self.path_db = pathlib.Path(path_db)
			if self.path_db.is_dir(): raise Exception("Path is a directory")
		except Exception as e:
			raise Exception(f"Invalid path: {path_db} - {e}")
		
		# Estabish connection to sqlite3 db
		try:
			self.db_con = sqlite3.connect(pathlib.Path(self.path_db))
			self.db_cur = self.db_con.cursor()
		except Exception as e:
			raise Exception(f"Error loading database at {self.path_db}: {e}")

		# Check DB for all applicable tables, or set up new
		self.db_setup()

	def db_setup(self):
		
		# Verify tapes, shots,and files tables are present
		try:
			tables = [table[0] for table in self.db_cur.execute("SELECT name from sqlite_master").fetchall()]
		except Exception as e:
			raise Exception(f"Error parsing database at {self.path_db}: {e}")

		if all([table in tables for table in ["tapes","shots","files"]]):
			return

		sql_create = [
			"""CREATE TABLE IF NOT EXISTS tapes (
				guid_tape INTEGER PRIMARY KEY,
				name TEXT NOT NULL UNIQUE,
				density INTEGER NOT NULL,
				date_added INTEGER DEFAULT CURRENT_TIMESTAMP NOT NULL
			);""",

			"""CREATE TABLE IF NOT EXISTS shots (
				guid_shot INTEGER PRIMARY KEY,
				guid_tape INTEGER REFERENCES tapes(guid_tape) ON UPDATE CASCADE ON DELETE CASCADE,
				name TEXT NOT NULL,
				size INTEGER DEFAULT 0 NOT NULL,
				base_path TEXT NOT NULL
			);""",

			"""CREATE TABLE IF NOT EXISTS files (
				guid_shot INTEGER REFERENCES shots(guid_shot) ON UPDATE CASCADE ON DELETE CASCADE,
				rel_path TEXT NOT NULL,
				startblock INTEGER DEFAULT 0 NOT NULL,
				size INTEGER DEFAULT 0 NOT NULL
			);""",
			
			"""CREATE INDEX IF NOT EXISTS idx_shots on shots(name);""",

			"""CREATE INDEX IF NOT EXISTS idx_shots_unique on shots(name,size);""",
			
			"""CREATE INDEX IF NOT EXISTS idx_files on files(guid_shot);"""]

		{self.db_cur.execute(sql_statement) for sql_statement in sql_create}


	def findShot(self, shot, ignoreproxies=True):

		results = []
		db_shot_found = self.db_cur.execute("SELECT shots.name, shots.size, shots.guid_shot, shots.guid_tape, tapes.name, tapes.density, shots.base_path FROM shots INNER JOIN tapes ON tapes.guid_tape = shots.guid_tape WHERE shots.name=? ORDER BY shots.size DESC",(shot,))

		# For each shot found, create Shot object and add to results[] list
		for shot_name, shot_size, shot_guid, shot_tape_guid, shot_tape_name, shot_tape_density, shot_basepath in db_shot_found.fetchall():
			
			db_files = self.db_cur.execute("SELECT rel_path, startblock, size FROM files WHERE guid_shot = ? ORDER BY startblock ASC",(shot_guid,))
			files = []
			for rel_path, startblock, filesize in db_files.fetchall():
				files.append({"path":pathlib.Path(rel_path), "startblock":startblock, "size": filesize})
			
			if not len(files):
#				sys.stderr.write(f"No files found for shot {shot_name}\n")
				continue

			shot_found = CameraRawPull(shot_name)
			shot_found.setPath(size=shot_size, basepath=pathlib.Path(shot_basepath), tape=Tape(shot_tape_name, density=shot_tape_density), filelist=files)
			results.append(shot_found)

		results = sorted(results, reverse=True, key=lambda x: x.getSize())

		# Remove paths that look like they could be proxies
		if ignoreproxies:
			for result in results:
				
				# remove proxy from results lit
				if any(x in str(result.basepath).lower() for x in ("dnx","conv","editorial")):
						
						# Is a proxy better than nothing?
						if len(results) < 2:
#							sys.stderr.write(f"Shot {result.shot} appears to be proxy only!\n")
							break

						#sys.stderr.write(f"Ignoring proxy for {shot}\n")
						del results[results.index(result)]
		
		return results[0] if len(results) else None
