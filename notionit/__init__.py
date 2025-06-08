#!/usr/bin/env python3
"""
Notion Markdown Uploader

마크다운 파일을 Notion 페이지로 변환하고 업로드하는 Python 패키지

Features:
- 기본 마크다운 지원 (헤더, 단락, 인라인/블록 수식)
- 코드 블록 지원 (60+ 프로그래밍 언어)
- 수식 정리 및 최적화
- 중복 제목 감지 및 처리
- 일괄 업로드 지원
- 완전한 타입 안전성 (mypy 호환)

Example:
    from notion_md_uploader import SmartNotionUploader

    uploader = SmartNotionUploader("your_notion_token", debug=True)
    result = uploader.smart_upload_markdown_file(
        "document.md",
        "parent_page_id",
        duplicate_strategy="timestamp"
    )
"""

from typing import Optional, Union

from .advanced import AdvancedNotionUploader
from .core import NotionMarkdownUploader
from .smart import SmartNotionUploader, is_status_result, is_success_result
from .types import (
    # 중복 처리 전략
    DuplicateStrategy,
    # API 응답 타입
    NotionAPIResponse,
    # 블록 타입
    NotionExtendedBlock,
    UploadResult,
)

# 기본 공개 인터페이스
__all__ = [
    # 메인 클래스들
    "NotionMarkdownUploader",
    "AdvancedNotionUploader",
    "SmartNotionUploader",
    # 헬퍼 함수들
    "is_success_result",
    "is_status_result",
    # 중요한 타입들
    "NotionAPIResponse",
    "UploadResult",
    "DuplicateStrategy",
    "NotionExtendedBlock",
]


def create_uploader(token: str, smart: bool = True, debug: bool = False) -> Union[SmartNotionUploader, AdvancedNotionUploader]:
    """
    편의 함수: 업로더 인스턴스 생성

    Args:
        token: Notion API 토큰
        smart: 스마트 기능 사용 여부 (중복 처리 등)
        debug: 디버깅 출력 활성화 여부

    Returns:
        설정된 업로더 인스턴스
    """
    if smart:
        return SmartNotionUploader(token, debug=debug)
    else:
        return AdvancedNotionUploader(token, debug=debug)


def quick_upload(token: str, file_path: str, parent_page_id: str, page_title: Optional[str] = None, duplicate_strategy: DuplicateStrategy = "timestamp") -> UploadResult:
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
    uploader = SmartNotionUploader(token)
    return uploader.smart_upload_markdown_file(file_path, parent_page_id, page_title, duplicate_strategy)
