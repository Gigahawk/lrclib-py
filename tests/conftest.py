import pytest


def pytest_collection_modifyitems(config, items):
    if not config.getoption("-m"):
        for item in items:
            if "post" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(
                        reason="use `-m post` to run this test. WARNING: will post test lyrics to lrclib"
                    )
                )
