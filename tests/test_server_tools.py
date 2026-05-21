from telemetry_deck_mcp.server import _load_tql_guide


def test_load_tql_guide_returns_guide_content():
    guide = _load_tql_guide()
    assert guide.startswith("# TQL Complete Reference & Guide")
    assert len(guide) > 1000
