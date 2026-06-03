import pytest

from lrclib_py import LrcLib, LrcLibSubmission


def test_get():
    client = LrcLib()
    result = client.get(
        artist_name="Borislav Slavov",
        track_name="I Want to Live",
        album_name="Baldur's Gate 3 (Original Game Soundtrack)",
        duration=233,
    )

    assert result.id == 3396226


# get-cached seems to 404 now?
@pytest.mark.xfail
def test_get_cached():
    client = LrcLib()
    result = client.get_cached(
        artist_name="Jeremy Soule",
        track_name="Dragonborn",
        album_name="The Elder Scrolls V: Skyrim (Original Game Soundtrack)",
        duration=236,
    )

    assert result.id == 67


def test_get_by_id():
    client = LrcLib()
    result = client.get_by_id(3396226)

    assert result.trackName == "I Want to Live"


def test_search():
    client = LrcLib()
    results = client.search(q="still alive portal")

    assert any(r.id == 195 for r in results)


@pytest.mark.post
def test_publish():
    test_data = LrcLibSubmission(
        name="TEST-LRCLIBPY",
        trackName="TEST-LRCLIBPY",
        artistName="TEST-LRCLIBPY",
        albumName="TEST-LRCLIBPY",
        duration=1,
        instrumental=False,
        plainLyrics="TEST-LRCLIBPY",
        syncedLyrics="TEST-LRCLIBPY",
        lyricsfile=None,
    )
    client = LrcLib()
    client.publish(test_data)
