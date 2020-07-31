# Deepworm client
# Python client for Deepworm API
# Rudimentary for now

from . import upco_shot, upco_timecode
import requests, json

class DeepwormClient:
	"""
	Python client for interacting with the Deepworm dailies API.
	"""

	def __init__(self, host="127.0.0.1", port="5000", version="v1"):
		"""Construct a connection to the Deepworm REST API.

		Args:
			host (str, optional): Host name or IP. Defaults to "127.0.0.1".
			port (str, optional): Port number. Defaults to "5000".
			version (str, optional): API version. Defaults to "v1".
		"""
		self.api_url = f"http://{host}:{port}/dailies/{version}"

		# TODO: Check connection, throw exceptions


	# Show-based operations
	
	def getShowList(self)->list:
		"""Request a list of all shows in Deepworm

		Raises:
			ConnectionError: Problem communicating with the API

		Returns:
			list: A list of _Show objects
		"""
		r = requests.get(f"{self.api_url}/shows")
		
		if not r.ok:
			raise ConnectionError(f"({r.status_code}) Error connecting to API")

		return [_Show(self, show) for show in r.json()]
	
	def getShow(self, guid:str=None, title:str=None):
		"""Request a show based on its guid or title

		Args must be one of:
			guid (str): Show GUID (ex: "9779e860-533d-11ea-b1c6-20677cdf2060")
			title (str): Show title (case-insensitive)

		Raises:
			ValueError: No GUID or title specified
			RuntimeError: Unexpected problem with API request
			FileNotFoundError: No shows match the criteria

		Returns:
			_Show: Show object for matched show
		"""

		if not any((title, guid)):
			raise ValueError("No GUID or title specified.")

		r = requests.post(f"{self.api_url}/shows/", data={"title":title, "guid_show":guid})

		if not r.ok:
			raise RuntimeError(f"({r.status_code}) Problem querying shows for {guid or title}")
		elif not r.json():
			raise FileNotFoundError(f"No shows match {guid or title}")
		
		return _Show(self, r.json())
	
	def searchShows(self, title_search:str)->list:
		"""Search for shows which contain a specified string in their titles

		Args:
			title_search (str): Show must contain this string (case-insensitive)

		Raises:
			ValueError: Invalid search string

		Returns:
			list: List of _Show objects which match the criteria
		"""

		r = requests.post(f"{self.api_url}/shows/", data={"title_search":title_search})

		if not r.ok:
			raise ValueError(f"({r.status_code}) Invalid search: {title_search}")

		return [_Show(self, x) for x in r.json()]
	
	
# Shot-based operations
	def getShotList(self, guid_show:str)->upco_shot.Shotlist:
		"""Request a list of all shots for a given show GUID

		Args:
			guid_show (str): Show GUID (ex: "9779e860-533d-11ea-b1c6-20677cdf2060")

		Raises:
			FileNotFoundError: Problem during API call

		Returns:
			upco_shot.Shotlist: A Shotlist containing all shots for the show
		"""
		r = requests.get(f"{self.api_url}/shows/{guid_show}/shots/")

		if not r.ok:
			raise RuntimeError(f"({r.status_code}) Invalid show guid: {guid_show}")

		shotlist = upco_shot.Shotlist()
		for shot in r.json():
			shotlist.addShot(upco_shot.Shot(shot.get("shot"), shot.get("frm_start"), tc_duration=shot.get("frm_duration"), metadata=json.loads(shot.get("metadata"))))

		return shotlist

	def getShot(self, guid:str)->upco_shot.Shot:
		r = requests.get(f"{self.api_url}/shots/{guid}/")

		if not r.ok:
			raise RuntimeError(f"({r.status_code}) Invalid shot guid: {guid}")
		elif not r.json():
			raise FileNotFoundError(f"No shot found with GUID {guid}")

		shot = r.json()
		return upco_shot.Shot(shot.get("shot"), shot.get("frm_start"), tc_end=shot.get("frm_end"), metadata=json.loads(shot.get("metadata")))

	def findShot(self, guid_show=None, shot:str=None, tc_start:upco_timecode.Timecode=None, tc_duration:upco_timecode.Timecode=None, tc_end:upco_timecode.Timecode=None, fps=24000/1001, subclip:bool=False):
		
		metadata = {}

		if shot is not None:
			metadata["shot"] = str(shot)
		if tc_start is not None:
			metadata["frm_start"] = upco_timecode.Timecode(tc_start, fps).framecount
		if tc_duration is not None:
			metadata["frm_duration"] = upco_timecode.Timecode(tc_duration, fps).framecount
		if tc_end is not None:
			metadata["frm_end"] = upco_timecode.Timecode(tc_end, fps).framecount
		search = {
			"guid_show": guid_show,
			"metadata" : metadata,
			"subclip"  : subclip
		}
		
		r = requests.post(f"{self.api_url}/shots/", json=search)

		if not r.ok:
			raise ValueError(f"({r.status_code}) Invalid search: {metadata}")

		return [upco_shot.Shot(shot.get("shot"), shot.get("frm_start"), tc_duration=shot.get("frm_duration"), metadata=json.loads(shot.get("metadata"))) for shot in r.json()]



class _Show:

	def __init__(self, client, show):
		self.title = show.get("title")
		self.guid  = show.get("guid_show")
		self._client = client

	def getShotList(self):
		return self._client.getShotList(self.guid)
	
	def getShot(self, guid):
		return self._client.getShot(guid)