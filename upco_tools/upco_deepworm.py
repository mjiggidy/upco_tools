# Deepworm client
# Python client for Deepworm API
# Rudimentary for now

from . import upco_shot
import requests, json

class DeepwormClient:

	def __init__(self, host="127.0.0.1", port="5000", version="v1"):
		"""Construct a connection to the Deepworm REST API.

		Args:
			host (str, optional): Host name or IP. Defaults to "127.0.0.1".
			port (str, optional): Port number. Defaults to "5000".
			version (str, optional): API version. Defaults to "v1".
		"""
		self.api_url = f"http://{host}:{port}/dailies/{version}"

		# TODO: Check connection, throw exceptions


	def getShowList(self):
		""" Get a list of shows and GUIDs """
		r = requests.get(f"{self.api_url}/shows")
		
		if not r.ok:
			raise ConnectionError(f"({r.status_code}) Error connecting to API")

		return [_Show(self, show) for show in r.json()]
	
	def getShow(self, title=None, guid=None):
		# TODO: Get show from name or GUID?
		pass
	
	def getShotList(self, guid_show):
		r = requests.get(f"{self.api_url}/shots/{guid_show}")

		if r.status_code != 200:
			raise FileNotFoundError(f"({r.status_code}) Invalid show guid: {guid_show}")

		shotlist = upco_shot.Shotlist()
		for shot in r.json():
			shotlist.addShot(upco_shot.Shot(shot.get("shot"), shot.get("frm_start"), tc_end=shot.get("frm_end"), metadata=json.loads(shot.get("extended_info","{}"))))

		return shotlist

class _Show:

	def __init__(self, client, show):
		self.title = show.get("title")
		self.guid  = show.get("guid_show")
		self._client = client

	def getShotList(self):
		return self._client.getShotList(self.guid)