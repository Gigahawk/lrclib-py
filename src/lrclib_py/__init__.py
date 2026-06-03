from dataclasses import dataclass
import urllib.request
import urllib.parse
import json
from typing import Optional


@dataclass
class LrcLibResponse:
    id: int
    name: str
    trackName: str
    artistName: str
    albumName: str
    duration: int
    instrumental: bool
    plainLyrics: str
    syncedLyrics: str
    lyricsfile: Optional[str]


class LrcLibError(Exception):
    pass


class LrcLib:
    def __init__(self):
        self.api_url: str = "https://lrclib.net"
        self.api_path: str = "/api"
        self.user_agent: str = "lrclib-py (https://github.com/Gigahawk/lrclib-py)"
        self.timeout: int = 10

    @property
    def _api_url(self) -> str:
        return self.api_url + self.api_path

    def _get_generic(self, endpoint: str, **kwargs):
        query = urllib.parse.urlencode(kwargs)
        req_url = f"{self._api_url + endpoint}?{query}"
        with urllib.request.urlopen(req_url, timeout=self.timeout) as resp:
            data = resp.read().decode("utf-8")
            if resp.status != 200:
                raise LrcLibError(f"HTTP Error, response: {data}")
            return json.loads(data)

    def _get(self, endpoint: str, **kwargs) -> LrcLibResponse:
        return LrcLibResponse(**self._get_generic(endpoint, **kwargs))

    def get(
        self,
        track_name: str,
        artist_name: str,
        album_name: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> LrcLibResponse:
        kwargs = locals()
        kwargs.pop("self")
        return self._get(endpoint="/get", **kwargs)
