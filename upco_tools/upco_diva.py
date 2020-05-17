import subprocess, pathlib, enum

class DivaCodes(enum.IntEnum):
	OK = 0
	MANAGER_NOT_FOUND = 1003
	ALREADY_CONNECTED = 1006
	OBJECT_NOT_FOUND  = 1009
	DESTINATION_NOT_FOUND = 1018
	LISTENER_NOT_FOUND = 4294967295

class Diva:

	def __init__(self, manager_ip, manager_port):
		
		self.man_ip = manager_ip
		self.man_port = manager_port
		self.divascript_exec = pathlib.Path(__file__).parent/"bin"/"win32"/"divascript.exe"

		if not self.divascript_exec.is_file():
			raise RuntimeError(f"Cannot find divascript at {self.divascript_exec}")

		self.__connect(manager_ip, manager_port)
	
	def __connect(self, manager_ip, manager_port):
		
		diva_client = subprocess.run([
			str(self.divascript_exec), "connect",
			"-mi", manager_ip,
			"-mp", manager_port],
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

		print("In restoreObject()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")

		#{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		#{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}


		
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