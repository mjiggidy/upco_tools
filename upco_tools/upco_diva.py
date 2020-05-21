import subprocess, pathlib, enum

class DivaCodes(enum.IntEnum):
	OK = 0								 # Success
	MANAGER_NOT_FOUND 		= 1003		 # No manager at provided IP/Port
	ALREADY_CONNECTED		= 1006		 # Listener is already connected
	INVALID_PARAMETER		= 1008		 # Example: Invalid character in object name
	OBJECT_NOT_FOUND		= 1009		 # Object not found in given category (could also mean invalid category)
	DESTINATION_NOT_FOUND	= 1018		 # Invalid src/destination
	LISTENER_NOT_FOUND		= 4294967295 #32-bit unsigned int max value, probably meant to be -1

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

		# If destination is invalid
		elif diva_client.returncode == DivaCodes.DESTINATION_NOT_FOUND:
			raise NotADirectoryError(f"{destination} is not a valid restore destination")

		# Catchall errors.  Mainly for debugging
		elif diva_client.returncode in (code for code in DivaCodes):
			raise RuntimeError(f"Error code {DivaCodes(diva_client.returncode).name}: {diva_client.stdout.strip()}")
		
		else:
			raise RuntimeError(f"Unknown error code {diva_client.returncode}: {diva_client.stdout.strip()}")


		
		# TODO: Add Errors

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

		print("In getStatus()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")