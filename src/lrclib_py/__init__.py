import hashlib
from dataclasses import dataclass, asdict
import urllib.request
import urllib.parse
import json
from typing import Optional, List, cast
import time


@dataclass
class LrcLibSubmission:
    name: str
    trackName: str
    artistName: str
    albumName: str
    duration: int
    instrumental: bool
    plainLyrics: str
    syncedLyrics: str
    lyricsfile: Optional[str]


@dataclass
class LrcLibResponse(LrcLibSubmission):
    id: int


class LrcLib:
    def __init__(self):
        self.api_url: str = "https://lrclib.net"
        self.api_path: str = "/api"
        self.user_agent: str = "lrclib-py (https://github.com/Gigahawk/lrclib-py)"
        self.timeout: int = 10
        # Token is always expired when we initialize
        self._token_expiry: float = time.time()
        self._token_prefix: Optional[str] = None
        self._token_target: Optional[bytes] = None
        self._token_nonce: Optional[str] = None

    @property
    def _api_url(self) -> str:
        return self.api_url + self.api_path

    def _get_generic(self, endpoint: str, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v}
        query = urllib.parse.urlencode(kwargs)
        req = urllib.request.Request(
            f"{self._api_url + endpoint}?{query}",
            headers={
                "User-Agent": self.user_agent,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = resp.read().decode("utf-8")
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

    def get_cached(
        self,
        track_name: str,
        artist_name: str,
        album_name: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> LrcLibResponse:
        kwargs = locals()
        kwargs.pop("self")
        return self._get(endpoint="/get-cached", **kwargs)

    def get_by_id(self, id: int) -> LrcLibResponse:
        return self._get(endpoint=f"/get/{id}")

    def search(
        self,
        q: Optional[str] = None,
        track_name: Optional[str] = None,
        artist_name: Optional[str] = None,
        album_name: Optional[str] = None,
    ) -> List[LrcLibResponse]:
        kwargs = locals()
        kwargs.pop("self")
        return [
            LrcLibResponse(**e) for e in self._get_generic(endpoint="/search", **kwargs)
        ]

    def publish(self, data: LrcLibSubmission):
        dict_data = asdict(data)
        json_data = json.dumps(dict_data).encode("utf-8")
        req = urllib.request.Request(
            self._api_url + "/publish",
            headers={
                "User-Agent": self.user_agent,
                "X-Publish-Token": self._publish_token,
                "Content-Type": "application/json",
            },
            method="POST",
            data=json_data,
        )
        with urllib.request.urlopen(req, timeout=self.timeout):
            pass
        # Token immediately expires after usage
        self._token_expiry = time.time()

    def _request_challenge(self):
        self._token_nonce = None
        req = urllib.request.Request(
            self._api_url + "/request-challenge",
            method="POST",
            headers={
                "User-Agent": self.user_agent,
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self._token_prefix = data["prefix"]
            self._token_target = bytes.fromhex(data["target"])
            self._token_expiry = time.time() + 5 * 60

    def _verify_challenge_solution(self, result: bytes) -> bool:
        target = cast(bytes, self._token_target)
        for i in range(len(result)):
            if result[i] > target[i]:
                return False
            elif result[i] < target[i]:
                break
        return True

    def _solve_challenge(self):
        # Ensure we have a challenge to solve
        if (
            time.time() > self._token_expiry
            or self._token_prefix is None
            or self._token_target is None
        ):
            self._request_challenge()

        if self._token_nonce is not None:
            return

        nonce = 0
        assert self._token_target is not None
        while time.time() < self._token_expiry:
            context = hashlib.sha256()
            test_val = f"{self._token_prefix}{nonce}"
            context.update(test_val.encode("utf-8"))
            hashed = context.digest()
            assert len(hashed) == len(self._token_target)
            if self._verify_challenge_solution(hashed):
                break
            else:
                nonce += 1
        else:
            raise TimeoutError(f"""
                Timeout occured while trying to find a nonce for
                prefix: {self._token_prefix!r}
                target {self._token_target!r}
            """)
        self._token_nonce = str(nonce)

    @property
    def _publish_token(self) -> str:
        self._solve_challenge()
        return f"{self._token_prefix}:{self._token_nonce}"
