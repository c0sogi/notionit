from os import environ
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pytest
import requests

from notionit import is_success_result, quick_upload
from notionit.config import DEFAULT_NOTION_API_VERSION, DEFAULT_NOTION_BASE_URL


def _live_credentials() -> tuple[str, str]:
    if environ.get("NOTIONIT_LIVE_TEST") != "1":
        pytest.skip("Set NOTIONIT_LIVE_TEST=1 to run live Notion API tests.")

    token = environ.get("NOTION_TOKEN")
    parent_page_id = environ.get("NOTION_PARENT_PAGE_ID")
    if not token or not parent_page_id:
        pytest.skip(
            "Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID for live Notion API tests."
        )

    return token, parent_page_id


def _trash_page(page_id: str, token: str) -> None:
    response = requests.patch(
        f"{DEFAULT_NOTION_BASE_URL}/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": DEFAULT_NOTION_API_VERSION,
        },
        json={"in_trash": True},
        timeout=30,
    )
    response.raise_for_status()


@pytest.mark.live
def test_live_quick_upload_creates_page_with_latest_notion_api(
    tmp_path: Path,
) -> None:
    token, parent_page_id = _live_credentials()
    markdown_file = tmp_path / "notionit-live-test.md"
    page_title = f"NotionIt live API test {uuid4().hex[:8]}"
    markdown_file.write_text(
        "# Live API test\n\nThis page was created by the NotionIt live test suite.\n",
        encoding="utf-8",
    )
    page_id: Optional[str] = None

    try:
        results = quick_upload(
            file_path=str(markdown_file),
            token=token,
            parent_page_id=parent_page_id,
            notion_version=DEFAULT_NOTION_API_VERSION,
            page_title=page_title,
        )

        assert len(results) == 1
        result = results[0]
        assert is_success_result(result)
        page_id = result.get("id")
        assert page_id is not None
        assert result.get("object") == "page"
        assert result.get("in_trash") is False
        assert result.get("url")
    finally:
        if page_id is not None:
            _trash_page(page_id, token)
