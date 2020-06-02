import subprocess, pathlib, enum, datetime

class DivaCodes(enum.IntEnum):
	OK = 0								 # Success
	MANAGER_NOT_FOUND 		= 1003		 # No manager at provided IP/Port
	ALREADY_CONNECTED		= 1006		 # Listener is already connected
	INVALID_PARAMETER		= 1008		 # Example: Invalid character in object name
	OBJECT_NOT_FOUND		= 1009		 # Object not found in given category (could also mean invalid category)
	REQUEST_NOT_FOUND		= 1011		 # Invalid job ID
	DESTINATION_NOT_FOUND	= 1018		 # Invalid src/destination
	OBJECT_OFFLINE			= 1023		 # Tape not loaded for object
	LISTENER_NOT_FOUND		= 4294967295 # 32-bit unsigned int max value, probably meant to be -1

class DivaJobStatus(enum.Enum):
	IN_PROGRESS	= "Migrating"	# Possibly only used for Restore operations? Need to investigate during Archive operation
	COMPLETED	= "Completed"
	ABORTED		= "Aborted"


class TapeNotLoadedError(FileNotFoundError):
	pass

class Diva:

	def __init__(self, manager_ip, manager_port, divascript_path=pathlib.Path(__file__).parent/"bin"/"win32"/"divascript.exe"):
		
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
			print(f"Already connected: {diva_client.stdout}")
		
		elif diva_client.returncode == DivaCodes.LISTENER_NOT_FOUND:
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
			if not info.isOnline():
				offline = [tape.get("name") for tape in media.tapes for media in info.media]
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


	def archiveObject(self, path_source, category):
		# Validate category
		# Check for duplicate object names
		# Check for tapes belonging to category
		pass

	def getJobStatus(self, job_id):

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
			raise RuntimeError(f"Job ID {job_id} was not found")
		
		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")

		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")

		print("In getStatus()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")

	def getObjectInfo(self, object_name, category):
		diva_client = subprocess.run([
			str(self.divascript_exec), "objinfo",
			"-obj", str(object_name),
			"-cat", str(category)],
			text = True,
			capture_output = True
		)
		
		if diva_client.returncode == DivaCodes.OK:
			return DivaObject(diva_client.stdout.strip())
		
		elif diva_client.returncode == DivaCodes.OBJECT_NOT_FOUND:
			raise FileNotFoundError(f"Object {object_name} not found in category {category}")

		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")

		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")

class DivaObject:

	def __init__(self, infostring):

		# Preserve string as-is just 'cuz
		self.infostring = infostring

		self.name = str()
		self.category = str()
		self.archive_date = str()
		self.size = int()
		self.files = []
		self.media = []

		# Parse text returned from `objinfo`
		for line in self.infostring.splitlines():
			# Skip empty lines
			if len(line.strip()) == 0:
				continue
			
			key, val = [x.strip() for x in line.split(':')]
			if not val: continue
			
			if key.lower() == "name":
				if len(self.name) and self.name != val:
					raise ValueError(f"Already encountered name: {self.name} (Now found {val})")
				self.name = val
			
			elif key.lower() == "category":
				if len(self.category) and self.category != val:
					raise ValueError(f"Already encountered category: {self.category} (Now found {val})")
				self.category = val
			
			elif key.lower() == "size":
				if self.size and self.size != val:
					raise ValueError(f"Already encountered size: {self.size} (Now found {val})")
				self.size = int(val)
			
			elif key.lower() == "archivingdate":
				date = datetime.datetime.fromtimestamp(int(val))
				if self.archive_date and self.archive_date != date:
					raise ValueError(f"Already encountered archive date: {self.archive_date} (Now found {date})")
				self.archive_date = date
			
			elif key.lower() == "file":
				if val in self.files:
					continue
				else:
					self.files.append({"filename":val})
			
			elif key.lower() == "mediainstanceid":
				self.media.append({"tapes":[]})
			
			elif key.lower() == "group":
				if not len(self.media) or (len(self.media[-1].get("group")) and self.media[1].get("group") != val):
					raise ValueError(f"Encountered tape group {val} at an inopportune time")
				self.media[-1].update({"group":val})
			
			# TODO: Look at this closer when I'm not sleepy
			elif key.lower() == "isinserted":
				if not len(self.media):
					continue
				elif self.media[-1].get("inserted") is None:
					self.media[-1].update({"inserted": True if val.lower == 'y' else 'n'})
				elif len(self.media[-1].tapes) and self.media[-1].tapes[-1].get("inserted") is None:
					self.media[-1].tapes[-1].update({"inserted": True if val.lower == 'y' else 'n'})
				else:
					raise ValueError(f"Encountered 'IsInserted' {val} at an inopportune time")

			elif key.lower() == "volume":
				if not len(self.media) or not len(self.media[-1].tapes):
					raise ValueError(f"Encountered volume ID {val} at an inpoortune time")
				elif val not in self.media[-1].tapes:
					self.media[-1].tapes.append({"name":val})
	
	def isOnline(self):
		if not len(self.media):
			return ValueError(f"No media found")
		
		# Return tape list for now; investigate disks later
		return all(tape.get("inserted") for tape in media for media in self.media)
