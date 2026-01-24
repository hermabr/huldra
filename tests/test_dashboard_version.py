import importlib.metadata

from furu.dashboard import __version__


def test_dashboard_version_matches_package_metadata() -> None:
    metadata_version = importlib.metadata.version("furu")

    assert metadata_version
    assert __version__ == metadata_version
