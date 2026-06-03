from lrclib_py import LrcLib


def test_get():
    client = LrcLib()
    result = client.get(
        artist_name="Borislav Slavov",
        track_name="I Want To Live",
        album_name="Baldur's Gate 3 (Original Game Soundtrack)",
        duration=233,
    )

    assert result.id == 3396226
