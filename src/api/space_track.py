"""Space-Track.org API client for fetching space debris data."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SpaceTrackClient:
    BASE_URL = "https://www.space-track.org"
    
    def __init__(self):
        self.email = os.getenv("SPACETRACK_EMAIL")
        self.password = os.getenv("SPACETRACK_PASSWORD")
        self.session = requests.Session()
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Space-Track.org."""
        auth_data = {
            "identity": self.email,
            "password": self.password
        }
        response = self.session.post(f"{self.BASE_URL}/ajaxauth/login", data=auth_data)
        response.raise_for_status()
    
    def get_debris_data(self, days_back=7):
        """Fetch recent space debris data."""
        query = f"{self.BASE_URL}/basicspacedata/query/class/gp/EPOCH/%3Enow-{days_back}d/orderby/EPOCH%20desc/format/json"
        response = self.session.get(query)
        response.raise_for_status()
        return response.json()
