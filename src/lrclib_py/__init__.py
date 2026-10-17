import hashlib
from dataclasses import dataclass, asdict
import urllib.request
import urllib.parse
from urllib.error import HTTPError
import json
from typing import Optional, List, Dict, Any, cast
import time
from random import random


class LrcLibError(Exception):
    pass


class LrcLibHttpError(LrcLibError):
    def __init__(
        self,
        *args,
        message: str = "",
        # unused
        name: str = "",
        statusCode: int = 999,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.message: str = message


class LrcLibErrorDecodeFailure(LrcLibError):
    pass


class LrcLibValidationError(LrcLibHttpError):
    pass


class LrcLibIncorrectPublishTokenError(LrcLibHttpError):
    pass


class LrcLibInvalidAppIdError(LrcLibHttpError):
    pass


class LrcLibMissingApiKeyError(LrcLibHttpError):
    pass


class LrcLibInvalidApiKeyError(LrcLibHttpError):
    pass


class LrcLibTrackNotFound(LrcLibHttpError):
    pass


class LrcLibRateLimitError(LrcLibHttpError):
    def __init__(
        self,
        *args,
        retry_after: int = 1,
        scope: str = "",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.retry_after: int = retry_after
        self.scope: str = scope


class LrcLibRateLimitExceeded(LrcLibRateLimitError):
    pass


class LrcLibUnknownError(LrcLibHttpError):
    pass


class LrcLibServerOverloaded(LrcLibRateLimitError):
    pass


ERROR_MAP = {
    "ValidationError": LrcLibValidationError,
    "IncorrectPublishTokenError": LrcLibIncorrectPublishTokenError,
    "InvalidAppIdError": LrcLibInvalidAppIdError,
    "MissingApiKeyError": LrcLibMissingApiKeyError,
    "InvalidApiKeyError": LrcLibInvalidApiKeyError,
    "TrackNotFound": LrcLibTrackNotFound,
    "RateLimitExceeded": LrcLibRateLimitExceeded,
    "UnknownError": LrcLibUnknownError,
    "ServerOverloaded": LrcLibServerOverloaded,
}


@dataclass
class LrcLibSubmission:
    trackName: str
    artistName: str
    albumName: str
    duration: int
    plainLyrics: Optional[str]
    syncedLyrics: Optional[str]
    lyricsfile: Optional[str]


@dataclass
class LrcLibResponse(LrcLibSubmission):
    id: int
    name: str
    instrumental: bool
    hasWordSync: bool


class LrcLib:
    def __init__(self):
        self.api_url: str = "https://lrclib.net"
        self.api_path: str = "/api"
        self.user_agent: str = "lrclib-py (https://github.com/Gigahawk/lrclib-py)"
        self.timeout: int = 10
        self._auto_retries: int = 3
        self._retries_remaining: int = self._auto_retries
        # Token is always expired when we initialize
        self._token_expiry: float = time.time()
        self._token_prefix: Optional[str] = None
        self._token_target: Optional[bytes] = None
        self._token_nonce: Optional[str] = None

    @property
    def auto_retries(self) -> int:
        return self._auto_retries

    @auto_retries.setter
    def auto_retries(self, value: int):
        # Don't reset if we are in the middle of retries
        reset = self._auto_retries == self._retries_remaining
        self._auto_retries = value
        if reset:
            self._reset_retries()

    def _reset_retries(self):
        self._retries_remaining = self._auto_retries

    @property
    def _api_url(self) -> str:
        return self.api_url + self.api_path

    def _handle_http_error(self, err: HTTPError):
        body = err.read()
        text = body.decode("utf-8", "replace")

        if text:
            try:
                err_data: Dict[str, Any] = json.loads(text)
                err_class = ERROR_MAP.get(
                    cast(str, err_data.get("name")),
                    LrcLibHttpError,
                )
                raise err_class(**err_data) from err
            except ValueError as dec_err:
                raise LrcLibErrorDecodeFailure(text) from dec_err
        else:
            raise LrcLibHttpError from err

    def _get_generic(self, endpoint: str, **kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v}
        query = urllib.parse.urlencode(kwargs)
        req = urllib.request.Request(
            f"{self._api_url + endpoint}?{query}",
            headers=self._request_header(),
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data: str = resp.read().decode("utf-8")
                self._reset_retries()
                return json.loads(data)
        except HTTPError as resp_err:
            try:
                self._handle_http_error(resp_err)
            except LrcLibRateLimitError as rate_err:
                if self._retries_remaining > 0:
                    time.sleep(rate_err.retry_after + random())
                    self._retries_remaining -= 1
                    return self._get_generic(endpoint, **kwargs)
                else:
                    self._reset_retries()
                    raise rate_err

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
            headers=self._request_header(with_publish_token=True),
            method="POST",
            data=json_data,
        )
        with urllib.request.urlopen(req, timeout=self.timeout):
            pass
        # Token immediately expires after usage
        self._token_expiry = time.time()

    def flag(self, trackId: int, content: str = ""):
        kwargs = locals()
        kwargs.pop("self")
        json_data = json.dumps(kwargs).encode("utf-8")
        req = urllib.request.Request(
            self._api_url + "/flag",
            headers=self._request_header(with_publish_token=True),
            method="POST",
            data=json_data,
        )
        with urllib.request.urlopen(req, timeout=self.timeout):
            pass
        # Token immediately expires after usage
        self._token_expiry = time.time()

    def _request_header(self, with_publish_token: bool = False):
        headers = {
            "User-Agent": self.user_agent,
        }
        if with_publish_token:
            headers["X-Publish-Token"] = self._publish_token
            headers["Content-Type"] = "application/json"
        return headers

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
