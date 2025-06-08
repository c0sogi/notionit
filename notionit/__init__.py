#!/usr/bin/env python3
from typing import Callable, Iterable, Optional, Union

import mistune

from .config import get_config
from .renderer import MistuneNotionRenderer
from .types import (
    # 중복 처리 전략
    DuplicateStrategy,
    # API 응답 타입
    NotionAPIResponse,
    # 블록 타입
    NotionExtendedBlock,
    UploadResult,
)
from .uploader import NotionUploader, is_status_result, is_success_result

# 기본 공개 인터페이스
__all__ = [
    # 메인 클래스들
    "NotionUploader",
    "MistuneNotionRenderer",
    # 헬퍼 함수들
    "is_success_result",
    "is_status_result",
    # 중요한 타입들
    "get_config",
    "NotionAPIResponse",
    "UploadResult",
    "DuplicateStrategy",
    "NotionExtendedBlock",
]


def create_uploader(
    token: Union[str, Callable[[], str]] = lambda: get_config("notion_token"),
    base_url: Union[str, Callable[[], str]] = lambda: get_config("notion_base_url"),
    notion_version: Union[str, Callable[[], str]] = lambda: get_config("notion_api_version"),
    plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
    debug: bool = False,
    renderer: mistune.RendererRef = "ast",
    escape: bool = True,
    hard_wrap: bool = False,
) -> NotionUploader:
    """
    편의 함수: 업로더 인스턴스 생성

    Args:
        token: Notion API 토큰
        debug: 디버깅 출력 활성화 여부

    Returns:
        설정된 업로더 인스턴스
    """
    return NotionUploader(token=token, base_url=base_url, notion_version=notion_version, debug=debug, renderer=renderer, escape=escape, hard_wrap=hard_wrap, plugins=plugins)


def quick_upload(
    file_path: str,
    token: Union[str, Callable[[], str]] = lambda: get_config("notion_token"),
    base_url: Union[str, Callable[[], str]] = lambda: get_config("notion_base_url"),
    notion_version: Union[str, Callable[[], str]] = lambda: get_config("notion_api_version"),
    parent_page_id: Union[str, Callable[[], str]] = lambda: get_config("notion_parent_page_id"),
    plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
    page_title: Optional[str] = None,
    duplicate_strategy: Optional[DuplicateStrategy] = None,
    debug: bool = False,
    renderer: mistune.RendererRef = "ast",
    escape: bool = True,
    hard_wrap: bool = False,
) -> UploadResult:
    """
    편의 함수: 빠른 업로드

    Args:
        token: Notion API 토큰
        file_path: 마크다운 파일 경로
        parent_page_id: 부모 페이지 ID
        page_title: 페이지 제목 (None이면 파일명 사용)
        duplicate_strategy: 중복 처리 전략

    Returns:
        업로드 결과
    """
    _parent_page_id = parent_page_id() if callable(parent_page_id) else parent_page_id
    del parent_page_id

    uploader = create_uploader(token=token, base_url=base_url, notion_version=notion_version, debug=debug, renderer=renderer, escape=escape, hard_wrap=hard_wrap, plugins=plugins)
    return uploader.upload_markdown_file(file_path=file_path, parent_page_id=_parent_page_id, page_title=page_title, duplicate_strategy=duplicate_strategy)
