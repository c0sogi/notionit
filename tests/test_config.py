import pytest

from notionit.config import DEFAULT_NOTION_API_VERSION, get_config


def test_default_notion_api_version_is_latest_supported_version() -> None:
    assert DEFAULT_NOTION_API_VERSION == "2026-03-11"


def test_get_config_uses_latest_notion_api_version_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NOTION_API_VERSION", raising=False)

    assert get_config("notion_api_version") == "2026-03-11"


def test_get_config_allows_notion_api_version_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTION_API_VERSION", "2025-09-03")

    assert get_config("notion_api_version") == "2025-09-03"
