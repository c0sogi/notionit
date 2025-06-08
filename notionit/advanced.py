#!/usr/bin/env python3
"""
고급 Notion 마크다운 업로더
코드 블록, 수식 정리, 디버깅 출력 등 고급 기능을 지원합니다.
"""

import re
import json
import requests
from typing import List, Dict, Optional, Union
from pathlib import Path

from .types import (
    NOTION_API_VERSION,
    NotionExtendedBlock,
    NotionAPIResponse,
    NotionExtendedCreatePageRequest,
    NotionEquationBlock,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionParagraphBlock,
    NotionCodeBlock,
    NotionCodeLanguage,
    NotionRichText,
)


class AdvancedNotionUploader:
    """고급 Notion 마크다운 업로더"""

    def __init__(self, token: str, debug: bool = False) -> None:
        """
        업로더 초기화

        Args:
            token: Notion API 토큰
            debug: 디버깅 출력 활성화 여부
        """
        self.token = token
        self.debug = debug
        self.headers: Dict[str, str] = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": NOTION_API_VERSION}

    def create_page(self, parent_page_id: str, title: str, blocks: List[NotionExtendedBlock]) -> NotionAPIResponse:
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

        data: NotionExtendedCreatePageRequest = {"parent": {"page_id": parent_page_id}, "properties": {"title": {"title": [{"text": {"content": title}}]}}, "children": blocks}

        if self.debug:
            print(f"🔍 생성할 블록 수: {len(blocks)}")
            for i, block in enumerate(blocks):
                if block["type"] == "equation":
                    print(f"  📐 수식 블록 {i + 1}: {block['equation']['expression']}")
                else:
                    print(f"  📝 {block['type']} 블록 {i + 1}")

        response = requests.post(url, headers=self.headers, json=data)
        result = response.json()

        if response.status_code != 200 and self.debug:
            print(f"❌ API 오류 (Status: {response.status_code}):")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        return result

    def parse_markdown_to_blocks(self, markdown_content: str) -> List[NotionExtendedBlock]:
        """
        마크다운을 Notion 블록으로 변환 (고급 기능 포함)

        Args:
            markdown_content: 마크다운 텍스트

        Returns:
            Notion 블록 리스트
        """
        blocks: List[NotionExtendedBlock] = []
        lines = markdown_content.split("\n")
        i = 0

        if self.debug:
            print("🔍 마크다운 파싱 시작...")

        while i < len(lines):
            line = lines[i].strip()

            # 빈 라인 건너뛰기
            if not line:
                i += 1
                continue

            if self.debug:
                print(f"  라인 {i + 1}: {line}")

            # 다중 라인 블록 수식 ($$로 시작)
            if line == "$$":
                if self.debug:
                    print("    📐 다중 라인 수식 시작")
                equation_lines: List[str] = []
                i += 1  # 다음 라인으로 이동

                # 수식 내용 수집
                while i < len(lines):
                    current_line = lines[i].strip()
                    if current_line == "$$":
                        if self.debug:
                            print("    📐 다중 라인 수식 종료")
                        break
                    equation_lines.append(lines[i])  # 원본 라인 유지 (들여쓰기 포함)
                    if self.debug:
                        print(f"      수식 내용: {lines[i]}")
                    i += 1

                if i < len(lines):  # $$ 종료 라인을 찾았으면
                    i += 1  # $$ 라인을 넘어감

                equation = "\n".join(equation_lines).strip()
                if self.debug:
                    print(f"    ✅ 완성된 수식: {equation}")

                if equation:  # 빈 수식이 아닌 경우에만 블록 생성
                    blocks.append(self._create_equation_block(equation))
                continue

            # 단일 라인 블록 수식 ($$...$$)
            if line.startswith("$$") and line.endswith("$$") and len(line) > 4:
                equation = line[2:-2].strip()
                if self.debug:
                    print(f"    📐 단일 라인 수식: {equation}")
                blocks.append(self._create_equation_block(equation))
                i += 1
                continue

            # 헤더 처리
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                text = line.lstrip("# ").strip()
                if self.debug:
                    print(f"    📝 헤더 (레벨 {level}): {text}")
                blocks.append(self._create_heading_block(text, level))
                i += 1
                continue

            # 코드 블록 처리
            if line.startswith("```"):
                if self.debug:
                    print("    💻 코드 블록 시작")
                code_lines: List[str] = []
                language = line[3:].strip() if len(line) > 3 else ""
                i += 1

                while i < len(lines):
                    if lines[i].strip() == "```":
                        if self.debug:
                            print("    💻 코드 블록 종료")
                        break
                    code_lines.append(lines[i])
                    i += 1

                if i < len(lines):
                    i += 1  # ``` 종료 라인을 넘어감

                code_content = "\n".join(code_lines)
                blocks.append(self._create_code_block(code_content, language))
                continue

            # 일반 단락 처리 (인라인 수식 포함 가능)
            paragraph_lines = [line]
            i += 1

            # 같은 단락에 속하는 후속 라인들 수집
            while i < len(lines) and lines[i].strip() and not self._is_special_line(lines[i]):
                paragraph_lines.append(lines[i].strip())
                i += 1

            paragraph_text = " ".join(paragraph_lines)
            if self.debug:
                print(f"    📄 단락: {paragraph_text[:50]}...")

            # 인라인 수식 확인
            if "$" in paragraph_text and not paragraph_text.startswith("$$"):
                if self.debug:
                    print("    💫 인라인 수식 포함")

            blocks.append(self._create_paragraph_block(paragraph_text))

        if self.debug:
            print(f"✅ 파싱 완료! 총 {len(blocks)}개 블록 생성")

        return blocks

    def _is_special_line(self, line: str) -> bool:
        """특별한 블록을 시작하는 라인인지 확인"""
        stripped = line.strip()
        return stripped.startswith("#") or stripped == "$$" or stripped.startswith("```")

    def _create_equation_block(self, equation: str) -> NotionEquationBlock:
        """수식 블록 생성 (LaTeX 정리 포함)"""
        # 수식 정리
        equation = equation.strip()

        # Notion 호환성을 위한 간단한 치환
        replacements: Dict[str, str] = {
            "\\,": " ",
            "\\;": " ",
            "\\bigl[": "[",
            "\\bigr]": "]",
            "\\bigl(": "(",
            "\\bigr)": ")",
            "\\Bigl[": "[",
            "\\Bigr]": "]",
            "\\Bigl(": "(",
            "\\Bigr)": ")",
            "\\mathrm{": "\\text{",
            "\\tfrac": "\\frac",
        }

        for old, new in replacements.items():
            equation = equation.replace(old, new)

        if self.debug:
            print(f"    🔧 정리된 수식: {equation}")

        return {"object": "block", "type": "equation", "equation": {"expression": equation}}

    def _normalize_language(self, language: str) -> NotionCodeLanguage:
        """언어 문자열을 Notion 지원 언어로 정규화"""
        language = language.lower().strip()

        # 언어 매핑 (일반적인 변형들)
        language_map: Dict[str, NotionCodeLanguage] = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "sh": "shell",
            "bash": "bash",
            "zsh": "shell",
            "fish": "shell",
            "cmd": "powershell",
            "ps1": "powershell",
            "rb": "ruby",
            "rs": "rust",
            "go": "go",
            "java": "java",
            "cpp": "c++",
            "cxx": "c++",
            "cc": "c++",
            "c": "c",
            "cs": "c#",
            "fs": "f#",
            "vb": "visual basic",
            "kt": "kotlin",
            "swift": "swift",
            "php": "php",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "scss": "scss",
            "sass": "sass",
            "less": "less",
            "xml": "xml",
            "json": "json",
            "yaml": "yaml",
            "yml": "yaml",
            "toml": "markup",
            "ini": "markup",
            "cfg": "markup",
            "conf": "markup",
            "dockerfile": "docker",
            "makefile": "makefile",
            "tex": "latex",
            "md": "markdown",
            "markdown": "markdown",
            "txt": "plain text",
            "": "plain text",
        }

        # 직접 매핑 시도
        if language in language_map:
            return language_map[language]

        # 유효한 Notion 언어인지 확인
        valid_languages: List[NotionCodeLanguage] = [
            "abap",
            "arduino",
            "bash",
            "basic",
            "c",
            "clojure",
            "coffeescript",
            "c++",
            "c#",
            "css",
            "dart",
            "diff",
            "docker",
            "elixir",
            "elm",
            "erlang",
            "flow",
            "fortran",
            "f#",
            "gherkin",
            "glsl",
            "go",
            "graphql",
            "groovy",
            "haskell",
            "html",
            "java",
            "javascript",
            "json",
            "julia",
            "kotlin",
            "latex",
            "less",
            "lisp",
            "livescript",
            "lua",
            "makefile",
            "markdown",
            "markup",
            "matlab",
            "mermaid",
            "nix",
            "objective-c",
            "ocaml",
            "pascal",
            "perl",
            "php",
            "plain text",
            "powershell",
            "prolog",
            "protobuf",
            "python",
            "r",
            "reason",
            "ruby",
            "rust",
            "sass",
            "scala",
            "scheme",
            "scss",
            "shell",
            "sql",
            "swift",
            "typescript",
            "vb.net",
            "verilog",
            "vhdl",
            "visual basic",
            "webassembly",
            "xml",
            "yaml",
            "java/c/c++/c#",
        ]

        for valid_lang in valid_languages:
            if language == valid_lang:
                return valid_lang

        # 알 수 없는 언어는 기본값으로
        return "plain text"

    def _create_code_block(self, code: str, language: str = "") -> NotionCodeBlock:
        """코드 블록 생성"""
        normalized_language = self._normalize_language(language)

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": code, "link": None},
                        "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"},
                    }
                ],
                "language": normalized_language,
            },
        }

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
                if self.debug:
                    print(f"      💫 인라인 수식: {equation}")
                rich_text.append({"type": "equation", "equation": {"expression": equation}})
            else:
                # 일반 텍스트
                if part:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": part, "link": None},
                        "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"},
                    })

        return rich_text

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

        return result
