#!/usr/bin/env python3
"""
기본 Notion 마크다운 업로더
간단한 마크다운을 Notion 페이지로 변환합니다.
"""

import re
import requests
from typing import List, Dict, Optional, Union
from pathlib import Path

from .types import (
    NOTION_API_VERSION,
    NotionBasicBlock,
    NotionAPIResponse,
    NotionCreatePageRequest,
    NotionEquationBlock,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionParagraphBlock,
    NotionRichText,
    NotionTextRichText,
)


class NotionMarkdownUploader:
    """기본 Notion 마크다운 업로더"""

    def __init__(self, token: str) -> None:
        """
        업로더 초기화

        Args:
            token: Notion API 토큰
        """
        self.token = token
        self.headers: Dict[str, str] = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": NOTION_API_VERSION}

    def create_page(self, parent_page_id: str, title: str, blocks: List[NotionBasicBlock]) -> NotionAPIResponse:
        """
        새 Notion 페이지 생성

        Args:
            parent_page_id: 부모 페이지 ID
            title: 페이지 제목
            blocks: Notion 블록 리스트

        Returns:
            Notion API 응답
        """
        url = "https://api.notion.com/v1/pages"

        data: NotionCreatePageRequest = {"parent": {"page_id": parent_page_id}, "properties": {"title": {"title": [{"text": {"content": title}}]}}, "children": blocks}

        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

    def parse_markdown_to_blocks(self, markdown_content: str) -> List[NotionBasicBlock]:
        """
        마크다운을 Notion 블록으로 변환

        Args:
            markdown_content: 마크다운 텍스트

        Returns:
            Notion 블록 리스트
        """
        blocks: List[NotionBasicBlock] = []
        lines = markdown_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 빈 라인 건너뛰기
            if not line:
                i += 1
                continue

            # 블록 수식 처리 ($$...$$)
            if line.startswith("$$") and line.endswith("$$"):
                equation = line[2:-2].strip()
                blocks.append(self._create_equation_block(equation))
                i += 1
                continue

            # 다중 라인 블록 수식
            if line.startswith("$$"):
                equation_lines = [line[2:]]
                i += 1
                while i < len(lines) and not lines[i].strip().endswith("$$"):
                    equation_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    equation_lines.append(lines[i].strip()[:-2])
                    i += 1

                equation = "\n".join(equation_lines).strip()
                blocks.append(self._create_equation_block(equation))
                continue

            # 헤더 처리
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                text = line.lstrip("# ").strip()
                blocks.append(self._create_heading_block(text, level))
                i += 1
                continue

            # 일반 단락 처리 (인라인 수식 포함 가능)
            paragraph_lines = [line]
            i += 1

            # 같은 단락에 속하는 후속 라인들 수집
            while i < len(lines) and lines[i].strip() and not self._is_special_line(lines[i]):
                paragraph_lines.append(lines[i].strip())
                i += 1

            paragraph_text = " ".join(paragraph_lines)
            blocks.append(self._create_paragraph_block(paragraph_text))

        return blocks

    def _is_special_line(self, line: str) -> bool:
        """특별한 블록을 시작하는 라인인지 확인"""
        stripped = line.strip()
        return stripped.startswith("#") or stripped.startswith("$$") or stripped.startswith("```")

    def _create_equation_block(self, equation: str) -> NotionEquationBlock:
        """수식 블록 생성"""
        return {"object": "block", "type": "equation", "equation": {"expression": equation}}

    def _create_heading_block(self, text: str, level: int) -> Union[NotionHeading1Block, NotionHeading2Block, NotionHeading3Block]:
        """헤더 블록 생성"""
        # Notion은 heading_1, heading_2, heading_3만 지원
        level = min(level, 3)

        rich_text: List[NotionRichText] = [
            {"type": "text", "text": {"content": text, "link": None}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}}
        ]

        if level == 1:
            return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text}}
        elif level == 2:
            return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text}}
        else:  # level == 3
            return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text}}

    def _create_paragraph_block(self, text: str) -> NotionParagraphBlock:
        """단락 블록 생성 (인라인 수식 지원)"""
        rich_text = self._parse_inline_content(text)
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}

    def _parse_inline_content(self, text: str) -> List[NotionRichText]:
        """인라인 수식과 서식이 포함된 텍스트 파싱"""
        rich_text: List[NotionRichText] = []

        # 인라인 수식(단일 $)으로 분할
        parts = re.split(r"(\$[^$]+\$)", text)

        for part in parts:
            if not part:
                continue

            if part.startswith("$") and part.endswith("$"):
                # 인라인 수식
                equation = part[1:-1]
                rich_text.append({"type": "equation", "equation": {"expression": equation}})
            else:
                # 일반 텍스트
                rich_text.extend(self._parse_text_formatting(part))

        return rich_text

    def _parse_text_formatting(self, text: str) -> List[NotionTextRichText]:
        """텍스트 서식 파싱 (굵게, 기울임 등)"""
        # 현재는 단순하게 일반 텍스트로 처리
        # 향후 **굵게**, *기울임* 등을 처리할 수 있음
        if not text:
            return []

        return [
            {"type": "text", "text": {"content": text, "link": None}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}}
        ]

    def upload_markdown_file(self, file_path: str, parent_page_id: str, page_title: Optional[str] = None) -> NotionAPIResponse:
        """
        마크다운 파일을 Notion에 업로드

        Args:
            file_path: 마크다운 파일 경로
            parent_page_id: 부모 페이지 ID
            page_title: 페이지 제목 (None이면 파일명 사용)

        Returns:
            Notion API 응답

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if page_title is None:
            page_title = path.stem

        blocks = self.parse_markdown_to_blocks(content)

        # 100개 블록 제한으로 청크 분할
        block_chunks = [blocks[i : i + 100] for i in range(0, len(blocks), 100)]

        # 첫 번째 청크로 페이지 생성
        result = self.create_page(parent_page_id, page_title, block_chunks[0] if block_chunks else [])

        if "id" not in result:
            return result

        page_id = result["id"]

        # 나머지 청크들을 자식으로 추가
        for chunk in block_chunks[1:]:
            self._append_blocks_to_page(page_id, chunk)

        return result

    def _append_blocks_to_page(self, page_id: str, blocks: List[NotionBasicBlock]) -> NotionAPIResponse:
        """기존 페이지에 블록 추가"""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        data = {"children": blocks}
        response = requests.patch(url, headers=self.headers, json=data)
        return response.json()
