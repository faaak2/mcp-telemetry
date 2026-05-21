import pytest
from telemetry_deck_mcp.server import _load_tql_guide, _load_apps, _load_app_structure


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


def test_load_app_structure_returns_events_and_parameters():
    ios_app_id = "8F4C8F44-B281-4316-86C1-627D66367194"
    data = _load_app_structure(ios_app_id)
    assert data["appId"] == ios_app_id
    assert data["appName"] == "iOS App"
    assert isinstance(data["events"], list)
    assert isinstance(data["parameters"], list)
    assert len(data["events"]) > 0


def test_load_app_structure_raises_on_unknown_id():
    with pytest.raises(ValueError, match="not found"):
        _load_app_structure("00000000-0000-0000-0000-000000000000")
