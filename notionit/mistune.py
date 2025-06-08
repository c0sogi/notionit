#!/usr/bin/env python3
"""
Mistune 기반 Full-markdown 지원 Notion 업로더
모든 마크다운 문법을 지원하는 고급 파서
"""

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast
from urllib.parse import urlparse

import requests

from ._utils import safe_url_join
from .config import get_config
from .types import (
    NotionBulletedListItemBlock,
    NotionCodeBlock,
    NotionCodeLanguage,
    NotionDividerBlock,
    NotionEquationBlock,
    NotionExtendedBlock,
    NotionFileBlock,
    NotionImageBlock,
    NotionNumberedListItemBlock,
    NotionQuoteBlock,
    NotionRichText,
    NotionTableBlock,
    NotionTextRichText,
)


class NotionFileUploader:
    """Notion 파일 업로드 헬퍼 클래스"""

    def __init__(
        self,
        token: Union[str, Callable[[], str]] = lambda: get_config("notion_token"),
        base_url: Union[str, Callable[[], str]] = lambda: get_config("notion_base_url"),
        notion_version: Union[str, Callable[[], str]] = lambda: get_config("notion_api_version"),
    ):
        _token = token() if callable(token) else token
        _base_url = base_url() if callable(base_url) else base_url
        _notion_version = notion_version() if callable(notion_version) else notion_version
        del token, base_url, notion_version

        self.base_url: str = _base_url
        self.headers: Dict[str, str] = {"Authorization": f"Bearer {_token}", "Notion-Version": _notion_version}

    def upload_file(self, file_path: str) -> Optional[str]:
        """파일을 업로드하고 file_upload_id를 반환"""
        try:
            if not os.path.exists(file_path):
                print(f"파일을 찾을 수 없습니다: {file_path}")
                return None

            # 파일 크기 확인 (20MB 제한)
            file_size = os.path.getsize(file_path)
            if file_size > 20 * 1024 * 1024:  # 20MB
                print(f"파일이 너무 큽니다 (20MB 초과): {file_path}")
                return None

            # 1단계: File Upload 객체 생성
            upload_obj = self._create_file_upload_object()
            if not upload_obj:
                return None

            file_upload_id = upload_obj["id"]
            upload_url = upload_obj["upload_url"]

            # 2단계: 파일 내용 업로드
            success = self._upload_file_content(upload_url, file_path)
            if not success:
                return None

            return file_upload_id

        except Exception as e:
            print(f"파일 업로드 실패: {e}")
            return None

    def _create_file_upload_object(self) -> Optional[Dict[str, Any]]:
        """File Upload 객체 생성"""
        url = safe_url_join(self.base_url, "file_uploads")
        try:
            response = requests.post(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"File Upload 객체 생성 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"File Upload 객체 생성 오류: {e}")
            return None

    def _upload_file_content(self, upload_url: str, file_path: str) -> bool:
        """파일 내용을 업로드"""
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                # upload_url에는 Authorization 헤더가 필요하지 않음
                response = requests.post(upload_url, files=files)

            print(f"파일 업로드 응답 상태: {response.status_code}")
            if response.status_code != 200:
                print(f"파일 업로드 응답 내용: {response.text}")

            return response.status_code == 200

        except Exception as e:
            print(f"파일 내용 업로드 오류: {e}")
            return False

    def is_supported_image(self, file_path: str) -> bool:
        """지원되는 이미지 파일인지 확인"""
        image_extensions = {".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp", ".ico"}
        return Path(file_path).suffix.lower() in image_extensions

    def is_supported_file(self, file_path: str) -> bool:
        """지원되는 파일인지 확인"""
        # 모든 지원되는 확장자 (이미지, 문서, 오디오, 비디오)
        supported_extensions = {
            # 이미지
            ".gif",
            ".heic",
            ".jpeg",
            ".jpg",
            ".png",
            ".svg",
            ".tif",
            ".tiff",
            ".webp",
            ".ico",
            # 문서
            ".pdf",
            ".txt",
            ".json",
            ".doc",
            ".dot",
            ".docx",
            ".dotx",
            ".xls",
            ".xlt",
            ".xla",
            ".xlsx",
            ".xltx",
            ".ppt",
            ".pot",
            ".pps",
            ".ppa",
            ".pptx",
            ".potx",
            # 오디오
            ".aac",
            ".adts",
            ".mid",
            ".midi",
            ".mp3",
            ".mpga",
            ".m4a",
            ".m4b",
            ".mp4",
            ".oga",
            ".ogg",
            ".wav",
            ".wma",
            # 비디오
            ".amv",
            ".asf",
            ".wmv",
            ".avi",
            ".f4v",
            ".flv",
            ".gifv",
            ".m4v",
            ".mp4",
            ".mkv",
            ".webm",
            ".mov",
            ".qt",
            ".mpeg",
        }
        return Path(file_path).suffix.lower() in supported_extensions


class MistuneNotionRenderer:
    """Mistune AST를 Notion 블록으로 변환하는 렌더러"""

    def __init__(
        self,
        token: Union[str, Callable[[], str]] = lambda: get_config("notion_token"),
        base_url: Union[str, Callable[[], str]] = lambda: get_config("notion_base_url"),
        notion_version: Union[str, Callable[[], str]] = lambda: get_config("notion_api_version"),
    ):
        self.blocks: List[NotionExtendedBlock] = []
        if token and base_url and notion_version:
            self.file_uploader = NotionFileUploader(token=token, base_url=base_url, notion_version=notion_version)
        else:
            self.file_uploader = None

    def render_ast(self, ast_nodes: List[Dict[str, Any]]) -> List[NotionExtendedBlock]:
        """AST 노드들을 Notion 블록으로 변환"""
        self.blocks = []

        for node in ast_nodes:
            self._render_node(node)

        return self.blocks

    def _render_node(self, node: Dict[str, Any]) -> None:
        """단일 AST 노드를 처리"""
        node_type = node.get("type")

        if node_type == "heading":
            self._render_heading(node)
        elif node_type == "paragraph":
            self._render_paragraph(node)
        elif node_type == "list":
            self._render_list(node)
        elif node_type == "block_code":
            self._render_code_block(node)
        elif node_type == "block_quote":
            self._render_block_quote(node)
        elif node_type == "thematic_break":
            self._render_divider()
        elif node_type == "table":
            self._render_table(node)
        elif node_type == "block_math":
            self._render_math_block(node)
        elif node_type == "blank_line":
            # 빈 줄은 무시
            pass
        else:
            # 알 수 없는 노드 타입은 단락으로 처리
            self._render_unknown_node(node)

    def _render_heading(self, node: Dict[str, Any]) -> None:
        """헤딩 노드 렌더링"""
        level = node.get("attrs", {}).get("level", 1)
        rich_text = self._render_inline_children(node.get("children", []))

        if level == 1:
            block = {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text}}
        elif level == 2:
            block = {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text}}
        else:  # level >= 3
            block = {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text}}

        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_paragraph(self, node: Dict[str, Any]) -> None:
        """단락 노드 렌더링"""
        rich_text = self._render_inline_children(node.get("children", []))

        if rich_text:  # 빈 단락은 추가하지 않음
            block = {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}
            self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_list(self, node: Dict[str, Any]) -> None:
        """리스트 노드 렌더링"""
        is_ordered = node.get("attrs", {}).get("ordered", False)

        for item_node in node.get("children", []):
            if item_node.get("type") == "list_item":
                self._render_list_item(item_node, is_ordered)

    def _render_list_item(self, node: Dict[str, Any], is_ordered: bool) -> None:
        """리스트 아이템 렌더링"""
        # 리스트 아이템의 내용을 추출
        rich_text = []

        for child in node.get("children", []):
            if child.get("type") == "block_text":
                rich_text.extend(self._render_inline_children(child.get("children", [])))
            elif child.get("type") == "paragraph":
                rich_text.extend(self._render_inline_children(child.get("children", [])))

        if rich_text:
            if is_ordered:
                block = {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": rich_text},
                }
                self.blocks.append(cast(NotionNumberedListItemBlock, block))
            else:
                block = {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rich_text},
                }
                self.blocks.append(cast(NotionBulletedListItemBlock, block))

    def _render_code_block(self, node: Dict[str, Any]) -> None:
        """코드 블록 렌더링"""
        code = node.get("raw", "")
        language = node.get("attrs", {}).get("info", "plain text")

        # Create proper rich text for code content
        code_rich_text: List[NotionRichText] = [
            cast(
                NotionTextRichText,
                {
                    "type": "text",
                    "text": {"content": code, "link": None},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"},
                },
            )
        ]

        block = {
            "object": "block",
            "type": "code",
            "code": {"rich_text": code_rich_text, "language": cast(NotionCodeLanguage, self._map_language(language))},
        }

        self.blocks.append(cast(NotionCodeBlock, block))

    def _render_block_quote(self, node: Dict[str, Any]) -> None:
        """인용문 블록 렌더링"""
        rich_text = []

        for child in node.get("children", []):
            if child.get("type") == "paragraph":
                rich_text.extend(self._render_inline_children(child.get("children", [])))

        if rich_text:
            block = {"object": "block", "type": "quote", "quote": {"rich_text": rich_text}}
            self.blocks.append(cast(NotionQuoteBlock, block))

    def _render_divider(self) -> None:
        """구분선 렌더링"""
        block = {"object": "block", "type": "divider", "divider": {}}
        self.blocks.append(cast(NotionDividerBlock, block))

    def _render_table(self, node: Dict[str, Any]) -> None:
        """테이블 렌더링 - 실제 Notion 테이블 블록 생성"""
        try:
            # 테이블 구조 분석
            table_data = self._analyze_table_structure(node)

            if not table_data["rows"]:
                # 빈 테이블인 경우 단락으로 처리
                self._render_empty_table_fallback()
                return

            # 테이블 행 블록들 생성
            table_row_blocks = []
            for row_data in table_data["rows"]:
                row_block = self._create_table_row_block(row_data, table_data["column_count"])
                table_row_blocks.append(row_block)

            # 테이블 블록 생성 (children 포함)
            table_block = {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": table_data["column_count"],
                    "has_column_header": table_data["has_header"],
                    "has_row_header": False,  # 마크다운 테이블은 일반적으로 행 헤더가 없음
                    "children": table_row_blocks,
                },
            }

            self.blocks.append(cast(NotionTableBlock, table_block))

        except Exception as e:
            # 테이블 파싱 실패 시 폴백
            print(f"테이블 렌더링 실패, 코드 블록으로 폴백: {e}")
            self._render_table_fallback(node)

    def _analyze_table_structure(self, table_node: Dict[str, Any]) -> Dict[str, Any]:
        """테이블 노드 구조 분석"""
        children = table_node.get("children", [])

        thead_nodes = [child for child in children if child.get("type") == "table_head"]
        tbody_nodes = [child for child in children if child.get("type") == "table_body"]

        all_rows = []
        has_header = False

        # 헤더 행 처리
        if thead_nodes:
            has_header = True
            header_rows = self._extract_table_rows(thead_nodes[0])
            all_rows.extend(header_rows)

        # 바디 행 처리
        if tbody_nodes:
            body_rows = self._extract_table_rows(tbody_nodes[0])
            all_rows.extend(body_rows)

        # 컬럼 수 계산 (첫 번째 행 기준)
        column_count = len(all_rows[0]) if all_rows else 0

        return {"rows": all_rows, "column_count": column_count, "has_header": has_header}

    def _extract_table_rows(self, section_node: Dict[str, Any]) -> List[List[str]]:
        """테이블 섹션에서 행 데이터 추출"""
        rows = []

        # table_head의 경우 직접 table_cell들이 children이므로 특별 처리
        if section_node.get("type") == "table_head":
            # table_head는 하나의 행으로 처리
            row_cells = []
            for cell_node in section_node.get("children", []):
                if cell_node.get("type") == "table_cell":
                    cell_content = self._extract_cell_content(cell_node)
                    row_cells.append(cell_content)

            if row_cells:  # 빈 행은 제외
                rows.append(row_cells)
        else:
            # table_body의 경우 기존 로직 사용
            for row_node in section_node.get("children", []):
                if row_node.get("type") == "table_row":
                    row_cells = []

                    for cell_node in row_node.get("children", []):
                        if cell_node.get("type") == "table_cell":
                            cell_content = self._extract_cell_content(cell_node)
                            row_cells.append(cell_content)

                    if row_cells:  # 빈 행은 제외
                        rows.append(row_cells)

        return rows

    def _extract_cell_content(self, cell_node: Dict[str, Any]) -> str:
        """셀 노드에서 텍스트 내용 추출"""
        content_parts = []

        def extract_text_recursive(node: Any) -> str:
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("raw", "")
                elif "children" in node:
                    return "".join(extract_text_recursive(child) for child in node["children"])
            return ""

        for child in cell_node.get("children", []):
            content_parts.append(extract_text_recursive(child))

        return "".join(content_parts).strip()

    def _create_table_row_block(self, row_data: List[str], expected_columns: int) -> Dict[str, Any]:
        """테이블 행 블록 생성"""
        # 컬럼 수 맞추기 (부족한 경우 빈 셀 추가)
        while len(row_data) < expected_columns:
            row_data.append("")

        # 초과하는 컬럼은 잘라내기
        row_data = row_data[:expected_columns]

        # 각 셀을 rich_text 배열로 변환
        cells = []
        for cell_content in row_data:
            cell_rich_text = (
                [
                    {
                        "type": "text",
                        "text": {"content": cell_content, "link": None},
                        "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"},
                    }
                ]
                if cell_content
                else []
            )

            cells.append(cell_rich_text)

        return {"object": "block", "type": "table_row", "table_row": {"cells": cells}}

    def _render_table_fallback(self, node: Dict[str, Any]) -> None:
        """테이블 렌더링 실패 시 폴백 (코드 블록)"""
        table_text = self._extract_table_text(node)

        block = {"object": "block", "type": "code", "code": {"rich_text": [{"type": "text", "text": {"content": table_text}}], "language": "plain text"}}
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_empty_table_fallback(self) -> None:
        """빈 테이블 처리"""
        block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "[빈 테이블]", "link": None},
                        "annotations": {"bold": False, "italic": True, "strikethrough": False, "underline": False, "code": False, "color": "gray"},
                    }
                ]
            },
        }
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_math_block(self, node: Dict[str, Any]) -> None:
        """수식 블록 렌더링"""
        equation = node.get("raw", "")

        block = {"object": "block", "type": "equation", "equation": {"expression": equation}}
        self.blocks.append(cast(NotionEquationBlock, block))

    def _render_unknown_node(self, node: Dict[str, Any]) -> None:
        """알 수 없는 노드를 단락으로 렌더링"""
        text = str(node.get("raw", ""))
        if text:
            block = {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}
            self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_inline_children(self, children: List[Dict[str, Any]]) -> List[NotionRichText]:
        """인라인 자식 노드들을 Notion RichText로 변환"""
        rich_text: List[NotionRichText] = []

        for child in children:
            child_type = child.get("type")

            if child_type == "text":
                rich_text.append(self._render_text(child))
            elif child_type == "strong":
                rich_text.extend(self._render_strong(child))
            elif child_type == "emphasis":
                rich_text.extend(self._render_emphasis(child))
            elif child_type == "codespan":
                rich_text.append(self._render_codespan(child))
            elif child_type == "link":
                rich_text.extend(self._render_link(child))
            elif child_type == "image":
                rich_text.extend(self._render_image(child))
            elif child_type == "strikethrough":
                rich_text.extend(self._render_strikethrough(child))
            elif child_type == "inline_math":
                rich_text.append(self._render_inline_math(child))
            elif child_type == "softbreak" or child_type == "linebreak":
                rich_text.append(self._render_break())
            else:
                # 알 수 없는 인라인 요소는 텍스트로 처리
                text = child.get("raw", "")
                if text:
                    rich_text.append(cast(NotionTextRichText, {"type": "text", "text": {"content": text}}))

        return rich_text

    def _render_text(self, node: Dict[str, Any]) -> NotionTextRichText:
        """일반 텍스트 렌더링"""
        content = node.get("raw", "")

        return cast(
            NotionTextRichText,
            {
                "type": "text",
                "text": {"content": content, "link": None},
                "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"},
            },
        )

    def _render_strong(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """굵은 텍스트 렌더링"""
        children_text = self._render_inline_children(node.get("children", []))

        # 모든 자식 텍스트에 bold 적용
        for text_item in children_text:
            if text_item.get("type") == "text" and "annotations" in text_item:
                cast(NotionTextRichText, text_item)["annotations"]["bold"] = True

        return children_text

    def _render_emphasis(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """기울임 텍스트 렌더링"""
        children_text = self._render_inline_children(node.get("children", []))

        # 모든 자식 텍스트에 italic 적용
        for text_item in children_text:
            if text_item.get("type") == "text" and "annotations" in text_item:
                cast(NotionTextRichText, text_item)["annotations"]["italic"] = True

        return children_text

    def _render_strikethrough(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """취소선 텍스트 렌더링"""
        children_text = self._render_inline_children(node.get("children", []))

        # 모든 자식 텍스트에 strikethrough 적용
        for text_item in children_text:
            if text_item.get("type") == "text" and "annotations" in text_item:
                cast(NotionTextRichText, text_item)["annotations"]["strikethrough"] = True

        return children_text

    def _render_codespan(self, node: Dict[str, Any]) -> NotionTextRichText:
        """인라인 코드 렌더링"""
        content = node.get("raw", "")

        return cast(
            NotionTextRichText,
            {
                "type": "text",
                "text": {"content": content, "link": None},
                "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": True, "color": "default"},
            },
        )

    def _render_link(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """링크 렌더링 - 파일 링크는 파일 블록으로 처리"""
        url = node.get("attrs", {}).get("url", "")
        children_text = self._render_inline_children(node.get("children", []))

        # 링크가 파일을 가리키는지 확인
        if self._is_file_link(url):
            # 파일 블록 생성
            self._render_file_block(url, self._get_link_text(children_text))
            return []  # 인라인 텍스트로는 반환하지 않음

        # 일반 링크인 경우 모든 자식 텍스트에 링크 적용
        for text_item in children_text:
            if text_item.get("type") == "text" and "text" in text_item:
                cast(NotionTextRichText, text_item)["text"]["link"] = {"url": url}

        return children_text

    def _is_file_link(self, url: str) -> bool:
        """링크가 파일을 가리키는지 확인"""
        if not url:
            return False

        # 로컬 파일 경로인 경우
        if self._is_local_file_path(url):
            return bool(self.file_uploader and self.file_uploader.is_supported_file(url))

        # URL의 경우 확장자로 판단
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            file_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".json", ".zip", ".rar", ".7z", ".mp3", ".wav", ".mp4", ".avi", ".mov"}
            return any(path.endswith(ext) for ext in file_extensions)
        except Exception:
            return False

    def _get_link_text(self, children_text: List[NotionRichText]) -> str:
        """링크 텍스트 추출"""
        text_parts = []
        for item in children_text:
            if item.get("type") == "text" and "text" in item:
                text_parts.append(cast(NotionTextRichText, item).get("text", {}).get("content", ""))
        return "".join(text_parts)

    def _render_file_block(self, url: str, link_text: str = "") -> None:
        """파일 블록 생성"""
        try:
            # URL이 로컬 파일 경로인지 확인
            if self._is_local_file_path(url):
                # 로컬 파일 업로드
                if self.file_uploader and self.file_uploader.is_supported_file(url):
                    file_upload_id = self.file_uploader.upload_file(url)
                    if file_upload_id:
                        # 업로드된 파일로 파일 블록 생성
                        block = {
                            "object": "block",
                            "type": "file",
                            "file": {"type": "file_upload", "file_upload": {"id": file_upload_id}, "caption": [{"type": "text", "text": {"content": link_text, "link": None}}] if link_text else []},
                        }
                        self.blocks.append(cast(NotionFileBlock, block))
                        return
                    else:
                        print(f"파일 업로드 실패: {url}")
                else:
                    print(f"지원되지 않는 파일: {url}")

            # 외부 URL이거나 업로드 실패한 경우 external 타입으로 처리
            if self._is_valid_url(url):
                block = {
                    "object": "block",
                    "type": "file",
                    "file": {"type": "external", "external": {"url": url}, "caption": [{"type": "text", "text": {"content": link_text, "link": None}}] if link_text else []},
                }
                self.blocks.append(cast(NotionFileBlock, block))
            else:
                # 유효하지 않은 URL인 경우 텍스트로 폴백
                self._render_file_fallback(url, link_text)

        except Exception as e:
            print(f"파일 블록 생성 실패: {e}")
            self._render_file_fallback(url, link_text)

    def _render_file_fallback(self, url: str, link_text: str) -> None:
        """파일 렌더링 실패 시 텍스트로 폴백"""
        content = f"[파일: {link_text}]({url})" if link_text else f"[파일]({url})"
        block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": content, "link": {"url": url} if self._is_valid_url(url) else None},
                        "annotations": {"bold": False, "italic": True, "strikethrough": False, "underline": False, "code": False, "color": "blue"},
                    }
                ]
            },
        }
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_image(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """이미지 렌더링 - 블록 레벨 이미지는 별도 처리"""
        url = node.get("attrs", {}).get("url", "")
        alt_text = ""

        for child in node.get("children", []):
            if child.get("type") == "text":
                alt_text = child.get("raw", "")
                break

        # 이미지가 단독으로 있는 경우 (블록 레벨) 실제 이미지 블록 생성
        if self._is_standalone_image(node):
            self._render_image_block(url, alt_text)
            return []  # 인라인 텍스트로는 반환하지 않음

        # 인라인 이미지인 경우 텍스트로 표현
        content = f"[이미지: {alt_text}]({url})" if alt_text else f"[이미지]({url})"

        return [
            cast(
                NotionTextRichText,
                {
                    "type": "text",
                    "text": {"content": content, "link": {"url": url}},
                    "annotations": {"bold": False, "italic": True, "strikethrough": False, "underline": False, "code": False, "color": "gray"},
                },
            )
        ]

    def _is_standalone_image(self, node: Dict[str, Any]) -> bool:
        """이미지가 단독으로 있는 블록 레벨 이미지인지 확인"""
        # 간단한 휴리스틱: 이미지가 paragraph의 유일한 자식인 경우
        # 실제로는 더 정교한 로직이 필요할 수 있음
        return True  # 일단 모든 이미지를 블록으로 처리

    def _render_image_block(self, url: str, alt_text: str = "") -> None:
        """실제 이미지 블록 생성"""
        try:
            # URL이 로컬 파일 경로인지 확인
            if self._is_local_file_path(url):
                # 로컬 파일 업로드
                if self.file_uploader and self.file_uploader.is_supported_image(url):
                    file_upload_id = self.file_uploader.upload_file(url)
                    if file_upload_id:
                        # 업로드된 파일로 이미지 블록 생성
                        block = {
                            "object": "block",
                            "type": "image",
                            "image": {"type": "file_upload", "file_upload": {"id": file_upload_id}, "caption": [{"type": "text", "text": {"content": alt_text, "link": None}}] if alt_text else []},
                        }
                        self.blocks.append(cast(NotionImageBlock, block))
                        return
                    else:
                        print(f"이미지 업로드 실패: {url}")
                else:
                    print(f"지원되지 않는 이미지 파일: {url}")

            # 외부 URL이거나 업로드 실패한 경우 external 타입으로 처리
            if self._is_valid_url(url):
                block = {
                    "object": "block",
                    "type": "image",
                    "image": {"type": "external", "external": {"url": url}, "caption": [{"type": "text", "text": {"content": alt_text, "link": None}}] if alt_text else []},
                }
                self.blocks.append(cast(NotionImageBlock, block))
            else:
                # 유효하지 않은 URL인 경우 텍스트로 폴백
                self._render_image_fallback(url, alt_text)

        except Exception as e:
            print(f"이미지 블록 생성 실패: {e}")
            self._render_image_fallback(url, alt_text)

    def _render_image_fallback(self, url: str, alt_text: str) -> None:
        """이미지 렌더링 실패 시 텍스트로 폴백"""
        content = f"[이미지: {alt_text}]({url})" if alt_text else f"[이미지]({url})"
        block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": content, "link": {"url": url} if self._is_valid_url(url) else None},
                        "annotations": {"bold": False, "italic": True, "strikethrough": False, "underline": False, "code": False, "color": "gray"},
                    }
                ]
            },
        }
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _is_local_file_path(self, path: str) -> bool:
        """로컬 파일 경로인지 확인"""
        # URL 스키마가 없거나 file:// 스키마인 경우
        parsed = urlparse(path)
        return not parsed.scheme or parsed.scheme == "file"

    def _is_valid_url(self, url: str) -> bool:
        """유효한 URL인지 확인"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _render_inline_math(self, node: Dict[str, Any]) -> NotionRichText:
        """인라인 수식 렌더링"""
        equation = node.get("raw", "")

        return {"type": "equation", "equation": {"expression": equation}}

    def _render_break(self) -> NotionTextRichText:
        """줄바꿈 렌더링"""
        return cast(
            NotionTextRichText,
            {"type": "text", "text": {"content": "\n", "link": None}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}},
        )

    def _map_language(self, language: str) -> str:
        """언어 코드를 Notion이 지원하는 형식으로 매핑"""
        language_map = {"py": "python", "js": "javascript", "ts": "typescript", "sh": "shell", "bash": "shell", "yml": "yaml", "md": "markdown", "": "plain text"}

        return language_map.get(language.lower(), language.lower())

    def _extract_table_text(self, node: Dict[str, Any]) -> str:
        """테이블 노드에서 텍스트 추출"""
        # 간단한 테이블 텍스트 추출 (실제 구현에서는 더 정교하게)
        return str(node.get("raw", "Table content"))
