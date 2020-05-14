import subprocess, pathlib, enum

class Diva:

	class DivaCodes(enum.Enum):
		OK = 0
		ALREADY_CONNECTED = 1006
		OBJECT_NOT_FOUND = 1009
		DESTINATION_NOT_FOUND = 1018
		MANAGER_NOT_FOUND = 1003
		LISTENER_NOT_FOUND = 4294967295

	def __init__(self, manager_ip, manager_port):
		
		self.man_ip = manager_ip
		self.man_port = manager_port
		self.divascript_exec = pathlib.Path(__file__).parent/"bin"/"win32"/"divascript.exe"

		if not self.divascript_exec.is_file():
			raise RuntimeError(f"Cannot find divascript at {self.divascript_exec}")

		# Open connection to Diva manager via divascript
		self.diva_server = subprocess.Popen([
			str(self.divascript_exec), "listen"],
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE,
			text = True
		)

		if self.diva_server.poll() is not None:
			self.diva_server.communicate()
			raise RuntimeError(f"Error starting Divascript listener: {self.diva_server.stdout.readlines()}\nCode: {self.diva_server.returncode}\nCode Enum: {self.__class__.DivaCodes(self.diva_server.returncode)}")

		#{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		#{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}

		
		print(f"Connecting to {manager_ip}:{manager_port}...")
		self.__connect(manager_ip, manager_port)

		#{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		#{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}

		if not self.isConnected():
			print(self.diva_server.communicate())
			raise RuntimeError(f"Error starting Divascript server: {self.diva_server.returncode}")

		# TODO: Add more robust error reporting
	
	def __del__(self):
		
		#if self.isConnected():
		#	self.__disconnect()

		print("In __del__()")
		# TODO: Hangs; In text mode: NoneType has no attribute utf8_mode
		diva_client = subprocess.run(
			[str(self.divascript_exec), "stopserver"],
			capture_output = True
		)

		print(f"Listener still running? {self.isConnected()}")


	
	def __connect(self, manager_ip, manager_port):
		
		diva_client = subprocess.run([
			str(self.divascript_exec), "connect",
			"-mi", manager_ip,
			"-mp", manager_port],
			text = True,
			capture_output = True
		)

		print("In __connect()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")


	# TODO: Hangs and gives weird errors
	def __disconnect(self):
		 
		diva_client = subprocess.run(
			[str(self.divascript_exec), "disconnect"],
			capture_output = True
		)

		print("In __disconnect()")
		print(f"client.returncode: {diva_client.returncode}")
		print(f"client.stdout: {diva_client.stdout}")
		print(f"client.stderr: {diva_client.stderr}")


	# TODO: Need to differentiate between listener running/notrunning and listener connected/disconnected to manager
	def isConnected(self):
		return self.diva_server.poll() is None


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

	def getStatus(self, job_id):

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