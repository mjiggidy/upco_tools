import requests

class AmberfinClient:

	def __init__(self, server_ip="192.168.20.50", server_port="31013"):
		
		self.url_amberfin = f"http://{server_ip}:{server_port}"
	
	def _api_call(self, method, endpoint, params=None):
		
		url = f"{self.url_amberfin}/WorkflowManagerService/rest/{endpoint}"
		req = requests.request(method, url, json=params)

		if req.ok:
			return req.json()
	
	def getActiveJobList(self):
		return self._api_call("GET","monitor/instances")
	
	def getJobDetails(self, job_id):
		return self._api_call("GET",f"monitor/instances/{job_id}")
		
	
		