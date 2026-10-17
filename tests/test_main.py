from time import sleep
from random import random

import pytest

from lrclib_py import LrcLib, LrcLibSubmission, LrcLibRateLimitError

TEST_DATA = LrcLibSubmission(
    trackName="TEST-LRCLIBPY",
    artistName="TEST-LRCLIBPY",
    albumName="TEST-LRCLIBPY",
    duration=1,
    plainLyrics="TEST-LRCLIBPY",
    syncedLyrics="TEST-LRCLIBPY",
    lyricsfile=None,
)


def test_get():
    client = LrcLib()
    result = client.get(
        artist_name="Borislav Slavov",
        track_name="I Want to Live",
        album_name="Baldur's Gate 3 (Original Game Soundtrack)",
        duration=233,
    )
    assert result.id == 3396226


def test_get_by_id():
    client = LrcLib()
    result = client.get_by_id(3396226)

    assert result.trackName == "I Want to Live"


def test_search():
    client = LrcLib()
    results = client.search(q="still alive portal")
    assert any(r.id == 9954485 for r in results)


def test_ratelimit_error():
    max_runs = 9999
    client = LrcLib()
    client.auto_retries = 0
    with pytest.raises(LrcLibRateLimitError) as e:
        for _ in range(max_runs):
            result = client.get_by_id(3396226)

            assert result.trackName == "I Want to Live"
            sleep(0.1)
    assert isinstance(e.value.retry_after, int)
    sleep(e.value.retry_after + random())


@pytest.mark.post
def test_publish():
    client = LrcLib()
    client.publish(TEST_DATA)


@pytest.mark.post
def test_flag():
    client = LrcLib()
    flag_track = client.get(
        track_name=TEST_DATA.trackName,
        artist_name=TEST_DATA.artistName,
        album_name=TEST_DATA.albumName,
        duration=TEST_DATA.duration,
    )
    client.flag(trackId=flag_track.id, content="TEST-LRCLIBPY")
