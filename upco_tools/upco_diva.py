# upco_diva
# A python client for the DivArchive API
# By Michael Jordan <michael@glowingpixel.com>

import subprocess, pathlib, enum, datetime

class DivaCodes(enum.IntEnum):
	"""Diva status codes based on executable return values"""
	OK = 0								 # Success
	MANAGER_NOT_FOUND 		= 1003		 # No manager at provided IP/Port
	ALREADY_CONNECTED		= 1006		 # Listener is already connected
	INVALID_PARAMETER		= 1008		 # Example: Invalid character in object name
	OBJECT_NOT_FOUND		= 1009		 # Object not found in given category (could also mean invalid category)
	REQUEST_NOT_FOUND		= 1011		 # Invalid job ID
	OBJECT_ALREADY_EXISTS	= 1016		 # Diva object already exists
	DESTINATION_NOT_FOUND	= 1018		 # Invalid src/destination
	OBJECT_OFFLINE			= 1023		 # Tape not loaded for object
	CRITICAL_ERROR			= 4294967295 # 32-bit unsigned int max value, probably meant to be -1

class DivaJobStatus(enum.Enum):
	"""Known job statuses based on outout from `reqinfo`"""

	# Archive object typically goes  ADDED -> QUEUED -> IN_PROGRESS -> COMPLETED

	ADDED		= "Running"
	QUEUED      = "Waiting for resources"
	IN_PROGRESS	= "Migrating"	# Possibly only used for Restore operations? Need to investigate during Archive operation
	COMPLETED	= "Completed"
	ABORTED		= "Aborted"


class TapeNotLoadedError(FileNotFoundError):
	"""Tape not loaded for request"""
	pass

class Diva:
	"""Communicate with DivArchive Manager

	Issue commands and query job/object info over Divascript.
	Divascript Listener must be running locally on the client.
	"""

	def __init__(self, manager_ip, manager_port, divascript_path=pathlib.Path(__file__).parent/"bin"/"win32"/"divascript.exe"):
		"""Establish a connection to DivArchive Manager

		Arguments:
			manager_ip {str} -- IP address of Diva Manager
			manager_port {int|str} -- Listening port on Diva Manager

		Keyword Arguments:
			divascript_path {str|pathlib} -- Path to Divascript executable (default: "bin/win32/divascript.exe"})

		Raises:
			RuntimeError: Divascript was unable to connect to DivArchive Manager
		"""
		
		self.man_ip = manager_ip
		self.man_port = manager_port
		self.last_request_id = None

		if not pathlib.Path(divascript_path).is_file():
			raise RuntimeError(f"Cannot find divascript at {divascript_path}")
		else:
			self.divascript_exec = pathlib.Path(divascript_path)

		self.__connect(manager_ip, manager_port)
	
	def __connect(self, manager_ip, manager_port):
		
		diva_client = subprocess.run([
			str(self.divascript_exec), "connect",
			"-mi", str(manager_ip),
			"-mp", str(manager_port)],
			text = True,
			capture_output = True
		)

		if diva_client.returncode == DivaCodes.OK:
			print(f"Successfully connected to {manager_ip}:{manager_port}")
			
		elif diva_client.returncode == DivaCodes.ALREADY_CONNECTED:
			pass
			#print(f"Already connected: {diva_client.stdout}")
		
		elif diva_client.returncode == DivaCodes.CRITICAL_ERROR:
			raise RuntimeError(f"Divascript Listener service is not running")

		elif diva_client.returncode == DivaCodes.MANAGER_NOT_FOUND:
			raise ConnectionError(f"Diva Manager not found at {manager_ip}:{manager_port}")


	# TODO: Hangs and gives weird errors
	# Should this even be implemented?
	def __disconnect(self):
		 
		diva_client = subprocess.run(
			[str(self.divascript_exec), "disconnect"],
			capture_output = True
		)

		print("In __disconnect()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")

	def restoreObject(self, object_name, category, destination=None, path=None):
		"""Restore an object from Diva

		Arguments:
			object_name {str} -- Object name on Diva
			category {str} -- Diva category of object

		Keyword Arguments:
			destination {str} -- Diva restore destination (ie. "Archive-DataIO") (default: {None})
			path {str|pathlib} -- Custom restore path (experimental) (default: {None})

		Raises:
			ValueError: Invalid Diva object
			RuntimeWarning: Successful restore but unrecognized job ID returned
			FileNotFoundError: Diva object does not exist in category
			TapeNotLoadedError: Aequired tape is not inserted
			NotADirectoryError: Invalid restore destination specified
			RuntimeError: Critical errors during restore

		Returns:
			jobid {int} -- Job ID of successful restore request
		"""
		
		if not any((destination, path)):
			raise ValueError("A valid restore destination or path is required")
		
		if all((destination, path)):
			raise ValueError("Only one destination or path may be specified")

		diva_client = subprocess.run([
			str(self.divascript_exec), "restore",
			"-obj", object_name,
			"-cat", category,
			"-src", destination],
			text = True,
			capture_output = True
		)

		# Evaluate return code
		if diva_client.returncode == DivaCodes.OK:
			# If all is good, set last_request_id and return job ID
			if diva_client.stdout.strip().isnumeric():
				self.last_request_id = int(diva_client.stdout)
				return self.last_request_id
			else:
				raise RuntimeWarning(f"Diva returned OK, but no request ID in response: {diva_client.stdout}")
		
		# If Object not found in Diva category
		elif diva_client.returncode == DivaCodes.OBJECT_NOT_FOUND:
			raise FileNotFoundError(f"Object {object_name} not found in category {category}")

		# If tape or disk is offline
		elif diva_client.returncode == DivaCodes.OBJECT_OFFLINE:
			# Look up tape info.  Hopefully the tape is known but just not loaded
			# Or if there's a problem looking up the object info, just let the exception pass through
			info = self.getObjectInfo(object_name, category)
			if not info.online:
				offline = [tape.get("name") for tape in info.tapes if tape.get("inserted") is False]
				raise TapeNotLoadedError(f"Required tape(s) {', '.join(offline)} not loaded for object {object_name} in category {category}")
			else:
				raise RuntimeError(f"{object_name} in category {category} does not appear to be on tape, or tape not loaded.")

		# If destination is invalid
		elif diva_client.returncode == DivaCodes.DESTINATION_NOT_FOUND:
			raise NotADirectoryError(f"{destination} is not a valid restore destination")

		# Catchall errors.  Mainly for debugging
		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")
		
		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")


	def archiveObject(self, path_source, category, media_group):
		"""Archive a file to Diva

		The file provided must be on a network volume accessible to the Diva actors.
		Currently, only single-file backups are supported.

		Args:
			path_source (str|pathlib.Path): Path to file to archive
			category (str): Diva category for backup
			media_group (str): Tape group for backup

		Raises:
			RuntimeWarning: Archive request appears to have been submitted successfully, but response was not understood
			RuntimeError: Failed to submit archive request

		Returns:
			int: Diva archive request ID
		"""

		path_source = pathlib.PureWindowsPath(path_source)

		# TODO: Determine server source automatically; fail if invalid source for Diva
		server_source = "archive"

		diva_client = subprocess.run([
			str(self.divascript_exec), "archive",
			"-obj", str(path_source.stem),
			"-cat", str(category),
			"-grp", str(media_group),
			"-src", str(server_source),
			"-fpr", str(path_source.relative_to(path_source.drive).relative_to(path_source.root).parent),
			"-filelist", str(path_source.name)
			],
			text = True,
			capture_output = True
		)
		
		# Evaluate return code
		if diva_client.returncode == DivaCodes.OK:
			# If all is good, set last_request_id and return job ID
			if diva_client.stdout.strip().isnumeric():
				self.last_request_id = int(diva_client.stdout)
				return self.last_request_id
			else:
				raise RuntimeWarning(f"Diva returned OK, but no request ID in response: {diva_client.stdout}")
		
		# Catchall errors.  Mainly for debugging
		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")
		
		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")


	def getJobStatus(self, job_id):
		"""Query job status by job ID

		Arguments:
			job_id {int|str} -- Diva Job ID

		Raises:
			ValueError: Job ID not found or invalid
			RuntimeError: Critical errors during job query

		Returns:
			KnownJobStatus {DivaJobStatus} -- Current status of job
		"""

		diva_client = subprocess.run([
			str(self.divascript_exec), "reqinfo",
			"-req", str(job_id)],
			text = True,
			capture_output = True
		)

		# stdout returns "Migrating" or "Completed" with status 0
		if diva_client.returncode == DivaCodes.OK:
			try:
				return DivaJobStatus(diva_client.stdout.strip())
			except:
				return diva_client.stdout.strip()
		
		elif diva_client.returncode == DivaCodes.REQUEST_NOT_FOUND:
			raise ValueError(f"Job ID {job_id} was not found")
		
		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")

		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")

		print("In getStatus()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")

	def getObjectInfo(self, object_name, category):
		"""Get archive info for Diva object

		Arguments:
			object_name {str} -- Diva object name
			category {[type]} -- Diva category of object

		Raises:
			FileNotFoundError: Object name not found in category
			RuntimeError: Critical errors during info query

		Returns:
			object {DivaObject} -- Diva object info parsed as DivaObject
		"""
		diva_client = subprocess.run([
			str(self.divascript_exec), "objinfo",
			"-obj", str(object_name),
			"-cat", str(category)],
			text = True,
			capture_output = True
		)
		
		if diva_client.returncode == DivaCodes.OK:
			return _DivaObject(diva_client.stdout.strip())
		
		elif diva_client.returncode == DivaCodes.OBJECT_NOT_FOUND:
			raise FileNotFoundError(f"Object {object_name} not found in category {category}")

		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")

		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")
	
	def getObjectList(self, object_name, category="*", group="*"):
		"""Query Diva for object list"""
		
		diva_client = subprocess.run([
			str(self.divascript_exec), "objlist",
			"-obj", str(object_name),
			"-cat", str(category),
			"-grp", str(group)],
			text = True,
			capture_output = True
		)

		if diva_client.returncode == DivaCodes.OK:
			results = [x.split('@') for x in diva_client.stdout.strip().splitlines()]
			return [self.getObjectInfo(x[0], x[1]) for x in results]

		elif diva_client.returncode == DivaCodes.OBJECT_NOT_FOUND:
			raise FileNotFoundError(f"Object {object_name} not found in category {category}")

		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")

		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")

class _DivaObject:
	"""Archive information about a Diva object"""

	def __init__(self, infostring):

		# Preserve string as-is just 'cuz
		self.infostring = infostring

		self.name = str()
		self.category = str()
		self.archive_date = str()
		self.size = int()
		self.files = []
		self.tapes = []
		self.disks = []

		# Parse text returned from `objinfo` command
		for num, line in enumerate(self.infostring.splitlines()):
			# Skip empty lines
			if len(line.strip()) == 0:
				continue
			
			key, val = (x.strip() for x in line.split(':'))
			if not val: continue
			
			# Object name
			if key.lower() == "name":
				if len(self.name) and self.name != val:
					raise ValueError(f"Already encountered name: {self.name} (Now found {val} on line {num})")
				self.name = val
			
			# Object category
			elif key.lower() == "category":
				if len(self.category) and self.category != val:
					raise ValueError(f"Already encountered category: {self.category} (Now found {val} on line {num})")
				self.category = val
			
			# Object size in bytes
			elif key.lower() == "size":
				if self.size and self.size != val:
					raise ValueError(f"Already encountered size: {self.size} (Now found {val} on line {num})")
				self.size = int(val)
			
			# Object archived date
			elif key.lower() == "archivingdate":
				date = datetime.datetime.fromtimestamp(int(val))
				if self.archive_date and self.archive_date != date:
					raise ValueError(f"Already encountered archive date: {self.archive_date} (Now found {date} on line {num})")
				self.archive_date = date
			
			# Array of filenames for the object
			elif key.lower() == "file":
				if val in self.files:
					continue
				else:
					self.files.append({"filename":val})
			
			# Add new tape if new media instance ID (TODO: Think this through; media instance can refer to multiple tapes?)
			elif key.lower() == "mediainstanceid":
				self.tapes.append({})

			# Tape group
			elif key.lower() == "group":
				if not len(self.tapes) and self.tapes[-1].get("group") != val:
					raise ValueError(f"Encountered tape group {val} at an inopportune time")
				self.tapes[-1].update({"group":val})
			
			# Tape name
			elif key.lower() == "volume":
				if not len(self.tapes):
					raise ValueError(f"Encountered volume ID {val} at an inopportune time")
				
				# If we've hit an additional volume, append it and copy the group from the first one
				elif self.tapes[-1].get("name") is not None:
					self.tapes.append({"name": val, "group":self.tapes[-1].get("group")})
				
				# If we're working on our first tape, update it
				self.tapes[-1].update({"name":val})

			# Is tape inserted
			elif key.lower() == "isinserted":
				if not len(self.tapes) or self.tapes[-1].get("name") is None:
					continue
				elif self.tapes[-1].get("inserted") is not None:
					raise ValueError(f"Encountered tape inserted boolean at an inopportune time")

				self.tapes[-1].update({"inserted": True if val.lower() == 'y' else False})

			# Disk instances
			elif key.lower() == "diskinstanceid":
				if len(self.disks) and "name" not in self.disks[-1]:
					raise ValueError("Encountered disk instance and inopportune time")
				self.disks.append({})
			
			# Disk array
			elif key.lower() == "array":
				if not len(self.disks) or "name" in self.disks[-1]:
					raise ValueError("Encountered disk array name at inopportune time")
				self.disks[-1].update({"name":val})

		# With the info string parsed, make sure we have all expected values
		if any(val is None for val in (self.name, self.category, self.size, self.archive_date)):
			raise RuntimeError(f"Incomplete information provided for object")
		
		if not any(len(x) for x in (self.tapes, self.disks)):
			raise RuntimeError(f"No tape or media information provided for object")
		
		elif not all(tape.get(x) is not None for x in ("name","group","inserted") for tape in self.tapes):
			raise RuntimeError("Incomplete tape info for object")
		
	@property
	def online(self):
		"""Determine if the object can be restored without needing media loaded"""
		return all(tape.get("inserted") for tape in self.tapes) or len(self.disks)
