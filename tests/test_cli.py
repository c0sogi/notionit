from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import notionit.__main__ as cli
from notionit.config import DEFAULT_NOTION_API_VERSION


runner = CliRunner()
DEFAULT_CLI_ENV = {
    "NOTION_TOKEN": "",
    "NOTION_PARENT_PAGE_ID": "",
    "NOTION_BASE_URL": "",
    "NOTION_API_VERSION": "",
    "NOTION_PARSER_PLUGINS": "",
}


def test_no_args_shows_setup_guide_and_config_status() -> None:
    result = runner.invoke(
        cli.app,
        [],
        env=DEFAULT_CLI_ENV,
    )

    assert result.exit_code == 0
    assert "NotionIt setup" in result.output
    assert "Current NotionIt configuration" in result.output
    assert "NOTION_TOKEN" in result.output


def test_status_reports_missing_required_environment() -> None:
    result = runner.invoke(
        cli.app,
        ["status"],
        env=DEFAULT_CLI_ENV,
    )

    assert result.exit_code == 1
    assert "NOTION_TOKEN" in result.output
    assert "missing" in result.output
    assert f"default: {DEFAULT_NOTION_API_VERSION}" in result.output


def test_status_reports_ready_when_required_environment_is_set() -> None:
    result = runner.invoke(
        cli.app,
        ["status"],
        env={
            **DEFAULT_CLI_ENV,
            "NOTION_TOKEN": "secret_test",
            "NOTION_PARENT_PAGE_ID": "page_test",
        },
    )

    assert result.exit_code == 0
    assert "Ready to upload" in result.output
    assert f"default: {DEFAULT_NOTION_API_VERSION}" in result.output


def test_upload_stops_before_api_call_when_token_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown_file = tmp_path / "notes.md"
    markdown_file.write_text("# Notes\n", encoding="utf-8")

    def fail_if_called(**_kwargs: Any) -> list[dict[str, str]]:
        raise AssertionError("quick_upload should not be called when config is missing")

    monkeypatch.setattr(cli, "quick_upload", fail_if_called)

    result = runner.invoke(
        cli.app,
        ["upload", str(markdown_file), "--parent-page-id", "page_test"],
        env=DEFAULT_CLI_ENV,
    )

    assert result.exit_code == 2
    assert "NOTION_TOKEN is missing" in result.output
    assert "NOTION_PARENT_PAGE_ID is missing" not in result.output


def test_upload_passes_options_to_quick_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown_file = tmp_path / "notes.md"
    markdown_file.write_text("# Notes\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    def fake_quick_upload(**kwargs: Any) -> list[dict[str, str]]:
        captured.update(kwargs)
        return [{"id": "page_1", "object": "page", "url": "https://notion.so/page_1"}]

    monkeypatch.setattr(cli, "quick_upload", fake_quick_upload)

    result = runner.invoke(
        cli.app,
        [
            "upload",
            str(markdown_file),
            "--token",
            "secret_test",
            "--parent",
            "page_test",
            "--title",
            "Friendly title",
            "--duplicate",
            "skip",
            "--noescape",
            "--hardwrap",
        ],
        env=DEFAULT_CLI_ENV,
    )

    assert result.exit_code == 0
    assert captured["file_path"] == [str(markdown_file)]
    assert captured["token"] == "secret_test"
    assert captured["parent_page_id"] == "page_test"
    assert captured["page_title"] == "Friendly title"
    assert captured["duplicate_strategy"] == "skip"
    assert captured["notion_version"] == DEFAULT_NOTION_API_VERSION
    assert captured["escape"] is False
    assert captured["hard_wrap"] is True
    assert "Upload successful" in result.output
