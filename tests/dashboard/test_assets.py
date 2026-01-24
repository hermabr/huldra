import importlib.resources


def test_dashboard_frontend_assets_present() -> None:
    ref = importlib.resources.files("furu.dashboard").joinpath(
        "frontend/dist/index.html"
    )
    with importlib.resources.as_file(ref) as path:
        assert path.exists()
