#!/usr/bin/env python3
from typing import Callable, Iterable, List, Optional, Union

import mistune

from .config import get_config
from .renderer import MistuneNotionRenderer
from .types import (
    # duplicate handling strategy
    DuplicateStrategy,
    # API response type
    NotionAPIResponse,
    # block type
    NotionExtendedBlock,
    StrOrCallable,
    UploadResult,
)
from .uploader import NotionUploader, is_status_result, is_success_result

# public interface
__all__ = [
    # main classes
    "NotionUploader",
    "MistuneNotionRenderer",
    # helper functions
    "is_success_result",
    "is_status_result",
    # important types
    "get_config",
    "NotionAPIResponse",
    "UploadResult",
    "DuplicateStrategy",
    "NotionExtendedBlock",
]


def create_uploader(
    token: StrOrCallable = lambda: get_config("notion_token"),
    base_url: StrOrCallable = lambda: get_config("notion_base_url"),
    notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
    plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
    debug: bool = False,
    renderer: mistune.RendererRef = "ast",
    escape: bool = True,
    hard_wrap: bool = False,
) -> NotionUploader:
    """
    Convenience function to create an uploader instance.

    Args:
        token: Notion API token
        debug: Enable debug output

    Returns:
        Configured uploader instance
    """
    return NotionUploader(
        token=token,
        base_url=base_url,
        notion_version=notion_version,
        debug=debug,
        renderer=renderer,
        escape=escape,
        hard_wrap=hard_wrap,
        plugins=plugins,
    )


def quick_upload(
    file_path: Union[str, List[str]],
    token: StrOrCallable = lambda: get_config("notion_token"),
    base_url: StrOrCallable = lambda: get_config("notion_base_url"),
    notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
    parent_page_id: StrOrCallable = lambda: get_config("notion_parent_page_id"),
    plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
    page_title: Optional[str] = None,
    duplicate_strategy: Optional[DuplicateStrategy] = None,
    debug: bool = False,
    renderer: mistune.RendererRef = "ast",
    escape: bool = True,
    hard_wrap: bool = False,
    delay_seconds: float = 1.0,
    progress: Optional[Callable[[float], None]] = None,
) -> List[UploadResult]:
    """
    Convenience wrapper for quick uploads.

    Args:
        file_path: Path to the Markdown file
        token: Notion API token
        parent_page_id: Parent page ID
        page_title: Page title (defaults to file name)
        duplicate_strategy: Strategy for handling duplicates
        progress: Optional callback receiving progress percentage (0.0-1.0)

    Returns:
        Upload result
    """
    _parent_page_id = parent_page_id() if callable(parent_page_id) else parent_page_id
    del parent_page_id

    uploader = create_uploader(
        token=token,
        base_url=base_url,
        notion_version=notion_version,
        debug=debug,
        renderer=renderer,
        escape=escape,
        hard_wrap=hard_wrap,
        plugins=plugins,
    )
    if isinstance(file_path, (list, tuple)):
        return uploader.upload_markdown_files(
            file_paths=file_path,
            parent_page_id=_parent_page_id,
            page_title=page_title,
            duplicate_strategy=duplicate_strategy,
            delay_seconds=delay_seconds,
            progress=progress,
        )
    else:
        return [
            uploader.upload_markdown_file(
                file_path=file_path,
                parent_page_id=_parent_page_id,
                page_title=page_title,
                duplicate_strategy=duplicate_strategy,
                progress=progress,
            )
        ]
