from telemetry_deck_mcp.server import _load_tql_guide, _load_apps


def test_load_tql_guide_returns_guide_content():
    guide = _load_tql_guide()
    assert guide.startswith("# TQL Complete Reference & Guide")
    assert len(guide) > 1000


def test_load_apps_returns_known_apps():
    apps = _load_apps()
    names = [a["appName"] for a in apps]
    assert "iOS App" in names
    assert "Web Player" in names
    for a in apps:
        assert set(a.keys()) == {"appId", "appName"}
        assert a["appId"]
        assert a["appName"]
