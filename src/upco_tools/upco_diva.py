import subprocess, pathlib

class Diva:

	def __init__(self, manager_ip, manager_port):
		
		self.man_ip = manager_ip
		self.man_port = manager_port
		self.divascript_exec = "divascript.exe"

		if not pathlib.Path(self.divascript_exec).is_file():
			raise RuntimeError(f"Cannot find divascript at {self.divascript_exec}")

		# Open connection to Diva manager via divascript
		self.diva_server = subprocess.Popen([
			self.divascript_exec, "connect",
			"-mi", manager_ip,
			"-mp", manager_port],
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE
		)

		if not self.isConnected():
			raise RuntimeError(f"Error starting Divascript server: {self.diva_server.returncode}")

		# TODO: Add more robust error reporting


	def isConnected(self):
		return self.diva_server.poll() is None


	def restoreObject(self, object_name, category, destination=None, path=None):
		
		if not any(destination, path):
			raise ValueError("A valid restore destination or path is required")
		elif all(destination, path):
			raise ValueError("Only one destination or path may be specified")

		diva_client = subprocess.Popen([
			self.divascript_exec, "restore",
			"-obj", object_name,
			"-cat", category,
			"-dest", destination],
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE
		)
		
		# TODO: Add Errors

	def archiveObject(self, path_source, category):
		# Validate category
		# Check for duplicate object names
		# Check for tapes belonging to category
		