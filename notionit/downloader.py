#!/usr/bin/env python3
"""Simple Notion page downloader."""

from typing import Any, Dict, List, Optional, cast

import requests

from ._utils import safe_url_join, unwrap_callable
from .config import get_config
from .types import StrOrCallable


class NotionDownloader:
    """Download Notion pages as Markdown."""

    def __init__(
        self,
        token: StrOrCallable = lambda: get_config("notion_token"),
        base_url: StrOrCallable = lambda: get_config("notion_base_url"),
        notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
        debug: bool = False,
    ) -> None:
        token = unwrap_callable(token)
        base_url = unwrap_callable(base_url)
        notion_version = unwrap_callable(notion_version)
        self.debug = debug
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
        }

    def fetch_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """Fetch blocks for a page."""
        url = safe_url_join(self.base_url, "blocks", page_id, "children") + "?page_size=100"
        blocks: List[Dict[str, Any]] = []
        while url:
            if self.debug:
                print(f"GET {url}")
            response = requests.get(url, headers=self.headers)
            data = response.json()
            blocks.extend(data.get("results", []))
            next_cursor = cast(Optional[str], data.get("next_cursor"))
            has_more = bool(data.get("has_more"))
            if has_more and next_cursor:
                url = safe_url_join(self.base_url, "blocks", page_id, "children") + f"?page_size=100&start_cursor={next_cursor}"
            else:
                url = None
        return blocks

    def blocks_to_markdown(self, blocks: List[Dict[str, Any]]) -> str:
        """Convert blocks to Markdown text."""
        lines: List[str] = []
        for block in blocks:
            block_type = cast(Optional[str], block.get("type"))
            if block_type is None:
                continue
            content = cast(Dict[str, Any], block.get(block_type, {}))
            rich_text = cast(List[Dict[str, Any]], content.get("rich_text", []))
            text = self._rich_text_to_plain(rich_text)
            if block_type == "heading_1":
                lines.append(f"# {text}")
            elif block_type == "heading_2":
                lines.append(f"## {text}")
            elif block_type == "heading_3":
                lines.append(f"### {text}")
            elif block_type == "paragraph":
                lines.append(text)
            elif block_type == "bulleted_list_item":
                lines.append(f"- {text}")
            elif block_type == "numbered_list_item":
                lines.append(f"1. {text}")
            elif block_type == "quote":
                lines.append(f"> {text}")
            elif block_type == "code":
                language = content.get("language", "")
                lines.append(f"```{language}")
                lines.append(text)
                lines.append("```")
            elif block_type == "equation":
                expression = content.get("expression", "")
                lines.append(f"$$\n{expression}\n$$")
            elif block_type == "divider":
                lines.append("---")
        return "\n\n".join(lines).strip() + "\n"

    def _rich_text_to_plain(self, rich_list: List[Dict[str, Any]]) -> str:
        parts: List[str] = []
        for item in rich_list:
            if item.get("type") == "text":
                parts.append(item.get("plain_text", ""))
            elif item.get("type") == "equation":
                expression = item.get("equation", {}).get("expression", "")
                parts.append(f"${expression}$")
        return "".join(parts)

    def download_page(self, page_id: str, output_path: str) -> str:
        blocks = self.fetch_page_blocks(page_id)
        markdown = self.blocks_to_markdown(blocks)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        return output_path

