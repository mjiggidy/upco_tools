import subprocess, pathlib

class Diva:

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
			stderr = subprocess.PIPE
		)

		#{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		#{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}

		
		print(f"Connecting to {manager_ip}:{manager_port}...")
		self.__connect(manager_ip, manager_port)

		#{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		#{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}

		if not self.isConnected():
			raise RuntimeError(f"Error starting Divascript server: {self.diva_server.returncode}")

		# TODO: Add more robust error reporting
	
	def __connect(self, manager_ip, manager_port):
		
		diva_client = subprocess.Popen([
			str(self.divascript_exec), "connect",
			"-mi", manager_ip,
			"-mp", manager_port],
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE
		)

		#{print(f"client.stdout: {str(x)}") for x in diva_client.stdout.readlines()}
		#{print(f"client.stderr: {str(x)}") for x in diva_client.stderr.readlines()}


	def isConnected(self):
		return self.diva_server.poll() is None


	def restoreObject(self, object_name, category, destination=None, path=None):
		
		if not any((destination, path)):
			raise ValueError("A valid restore destination or path is required")
		
		if all((destination, path)):
			raise ValueError("Only one destination or path may be specified")

		diva_client = subprocess.Popen([
			str(self.divascript_exec), "restore",
			"-obj", object_name,
			"-cat", category,
			"-src", destination],
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE
		)

		{print(f"client.stdout: {str(x)}") for x in diva_client.stdout.readlines()}
		{print(f"client.stderr: {str(x)}") for x in diva_client.stderr.readlines()}

		{print(f"server.stdout: {str(x)}") for x in self.diva_server.stdout.readlines()}
		{print(f"server.stderr: {str(x)}") for x in self.diva_server.stderr.readlines()}


		
		# TODO: Add Errors

	def archiveObject(self, path_source, category):
		# Validate category
		# Check for duplicate object names
		# Check for tapes belonging to category
		pass

	def checkStatus(self, job_id):
		# Check status for job_id
		# Return state; possibly as Enum
		pass