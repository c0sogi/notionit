#!/usr/bin/env python3
"""
고급 Notion 마크다운 업로더
코드 블록, 수식 정리, 디버깅 출력 등 고급 기능을 지원합니다.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Union, cast

import mistune
import requests

from ._utils import safe_url_join
from .config import get_config
from .renderer import MistuneNotionRenderer
from .types import (
    DuplicateStrategy,
    NotionAPIResponse,
    NotionBasicBlock,
    NotionCodeBlock,
    NotionCodeLanguage,
    NotionEquationBlock,
    NotionExtendedBlock,
    NotionExtendedCreatePageRequest,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionParagraphBlock,
    NotionRichText,
    NotionSearchResponse,
    NotionSearchResultPage,
    NotionSearchTitleTextObject,
    NotionTextRichText,
    UploadResult,
    UploadStatusResult,
)


class NotionUploader:
    """고급 Notion 마크다운 업로더"""

    def __init__(
        self,
        token: Union[str, Callable[[], str]] = lambda: get_config("notion_token"),
        base_url: Union[str, Callable[[], str]] = lambda: get_config("notion_base_url"),
        notion_version: Union[str, Callable[[], str]] = lambda: get_config("notion_api_version"),
        plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
        debug: bool = False,
        renderer: mistune.RendererRef = "ast",
        escape: bool = True,
        hard_wrap: bool = False,
    ) -> None:
        """
        업로더 초기화

        Args:
            token: Notion API 토큰
            debug: 디버깅 출력 활성화 여부
        """
        _notion_version = notion_version() if callable(notion_version) else notion_version
        _base_url = base_url() if callable(base_url) else base_url
        _token = token() if callable(token) else token
        _plugins = plugins() if callable(plugins) else plugins
        del token, base_url, notion_version, plugins

        self.token: str = _token
        self.debug: bool = debug
        self.base_url: str = _base_url
        self.headers: Dict[str, str] = {"Authorization": f"Bearer {_token}", "Content-Type": "application/json", "Notion-Version": _notion_version}
        self.markdown_parser: mistune.Markdown = mistune.create_markdown(renderer=renderer, escape=escape, hard_wrap=hard_wrap, plugins=_plugins)
        self.notion_renderer = MistuneNotionRenderer(token=_token, base_url=_base_url, notion_version=_notion_version)

    def create_page(self, parent_page_id: str, title: str, blocks: Sequence[NotionExtendedBlock]) -> NotionAPIResponse:
        """
        새 Notion 페이지 생성

        Args:
            parent_page_id: 부모 페이지 ID
            title: 페이지 제목
            blocks: Notion 블록 리스트

        Returns:
            Notion API 응답
        """
        url = safe_url_join(self.base_url, "pages")
        data: NotionExtendedCreatePageRequest = {"parent": {"page_id": parent_page_id}, "properties": {"title": {"title": [{"text": {"content": title}}]}}, "children": list(blocks)}

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
        마크다운 텍스트를 Notion 블록으로 파싱 (Mistune 사용)

        Args:
            markdown_content: 마크다운 텍스트

        Returns:
            Notion 블록 리스트
        """
        try:
            # Mistune으로 파싱 (튜플 반환값에서 AST 추출)
            parse_result = self.markdown_parser.parse(markdown_content)
            if isinstance(parse_result, tuple):
                ast_nodes = parse_result[0]
            else:
                ast_nodes = parse_result

            # AST가 문자열인 경우 처리
            if isinstance(ast_nodes, str):
                raise TypeError("Mistune 파싱 결과가 문자열입니다.")

            # AST를 Notion 블록으로 변환
            blocks = self.notion_renderer.render_ast(ast_nodes)

            return blocks

        except Exception as e:
            # 파싱 실패 시 기존 방식으로 폴백
            print(f"Mistune 파싱 실패, 기존 방식 사용: {e}")
            # Cast the basic blocks to extended blocks for compatibility
            basic_blocks = self._parse_markdown_to_blocks(markdown_content)
            return cast(List[NotionExtendedBlock], basic_blocks)

    def _upload_markdown_file(self, file_path: str, parent_page_id: str, page_title: Optional[str] = None) -> NotionAPIResponse:
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
        result = self.create_page(
            parent_page_id=parent_page_id,
            title=page_title,
            blocks=block_chunks[0] if block_chunks else [],
        )

        if "id" not in result:
            return result

        page_id = result["id"]

        # 나머지 청크들을 자식으로 추가
        for chunk in block_chunks[1:]:
            self._append_blocks_to_page(page_id, chunk)

        return result

    def check_existing_pages_with_title(self, title: str) -> List[NotionSearchResultPage]:
        """
        동일한 제목을 가진 기존 페이지들을 검색

        Args:
            title: 검색할 페이지 제목

        Returns:
            동일한 제목을 가진 페이지 리스트
        """
        url = safe_url_join(self.base_url, "search")
        search_data = {"query": title, "filter": {"value": "page", "property": "object"}}

        response = requests.post(url, headers=self.headers, json=search_data)
        result: NotionSearchResponse = response.json()

        if "results" in result:
            # 정확한 제목 매치만 필터링
            exact_matches: List[NotionSearchResultPage] = []
            for page in result["results"]:
                if "properties" in page and "title" in page["properties"]:
                    page_title_array: List[NotionSearchTitleTextObject] = page["properties"]["title"]["title"]
                    if page_title_array:
                        page_title: str = page_title_array[0]["text"]["content"]
                        if page_title == title:
                            exact_matches.append(page)
            return exact_matches

        return []

    def generate_unique_title(self, base_title: str, strategy: str = "timestamp") -> str:
        """
        고유한 제목 생성

        Args:
            base_title: 기본 제목
            strategy: 고유화 전략 ("timestamp", "counter", "hash")

        Returns:
            고유한 제목
        """
        if strategy == "timestamp":
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            return f"{base_title} ({timestamp})"

        elif strategy == "counter":
            existing_pages = self.check_existing_pages_with_title(base_title)
            if not existing_pages:
                return base_title

            counter = 1
            while True:
                new_title = f"{base_title} ({counter})"
                if not self.check_existing_pages_with_title(new_title):
                    return new_title
                counter += 1

        elif strategy == "hash":
            # 파일 내용 기반 해시
            file_hash = hashlib.md5(base_title.encode()).hexdigest()[:8]
            return f"{base_title} ({file_hash})"

        return base_title

    def upload_markdown_file(
        self,
        file_path: str,
        parent_page_id: str,
        page_title: Optional[str] = None,
        duplicate_strategy: Optional[DuplicateStrategy] = None,
    ) -> UploadResult:
        """
        마크다운 파일 업로드

        Args:
            file_path: 마크다운 파일 경로
            parent_page_id: 부모 페이지 ID
            page_title: 페이지 제목 (None이면 파일명 사용)
            duplicate_strategy: 중복 처리 전략

        Returns:
            업로드 결과 (성공 응답 또는 상태)
        """
        path = Path(file_path)

        if page_title is None:
            page_title = path.stem

        # 기존 페이지 확인
        if duplicate_strategy is not None and (existing_pages := self.check_existing_pages_with_title(page_title)):
            if self.debug:
                print(f"⚠️  동일한 제목 '{page_title}'을 가진 페이지가 {len(existing_pages)}개 존재합니다.")

            if duplicate_strategy == "ask":
                print(f"⚠️  동일한 제목 '{page_title}'을 가진 페이지가 {len(existing_pages)}개 존재합니다.")
                print("어떻게 처리하시겠습니까?")
                print("1. 타임스탬프 추가하여 새 페이지 생성")
                print("2. 번호 추가하여 새 페이지 생성")
                print("3. 기존 페이지 무시하고 새 페이지 생성")
                print("4. 업로드 취소")

                choice = input("선택 (1-4): ").strip()
                if choice == "1":
                    duplicate_strategy = "timestamp"
                elif choice == "2":
                    duplicate_strategy = "counter"
                elif choice == "3":
                    duplicate_strategy = "create_anyway"
                else:
                    print("❌ 업로드가 취소되었습니다.")
                    return {"status": "cancelled"}

            if duplicate_strategy == "timestamp":
                page_title = self.generate_unique_title(page_title, "timestamp")
                if self.debug:
                    print(f"📝 새 제목: {page_title}")

            elif duplicate_strategy == "counter":
                page_title = self.generate_unique_title(page_title, "counter")
                if self.debug:
                    print(f"📝 새 제목: {page_title}")

            elif duplicate_strategy == "skip":
                if self.debug:
                    print("⏭️  업로드를 건너뜁니다.")
                return {"status": "skipped"}

        # 일반 업로드 진행
        result = self._upload_markdown_file(file_path, parent_page_id, page_title)
        return result

    def batch_upload_files(
        self,
        file_paths: List[str],
        parent_page_id: str,
        duplicate_strategy: DuplicateStrategy = "timestamp",
        delay_seconds: float = 1.0,
    ) -> List[UploadResult]:
        """
        여러 파일을 일괄 업로드

        Args:
            file_paths: 업로드할 파일 경로 리스트
            parent_page_id: 부모 페이지 ID
            duplicate_strategy: 중복 처리 전략
            delay_seconds: 파일 간 지연 시간 (초)

        Returns:
            업로드 결과 리스트
        """
        results: List[UploadResult] = []

        for i, file_path in enumerate(file_paths):
            if self.debug:
                print(f"\n📁 {i + 1}/{len(file_paths)}: {file_path}")

            try:
                result = self.upload_markdown_file(file_path, parent_page_id, duplicate_strategy=duplicate_strategy)
                results.append(result)

                if is_success_result(result):
                    if self.debug:
                        print(f"✅ 업로드 성공: {result.get('id', '')}")
                else:
                    if self.debug:
                        print(f"⚠️  업로드 결과: {result.get('status', 'unknown')}")

            except Exception as e:
                if self.debug:
                    print(f"❌ 업로드 실패: {e}")
                # 에러를 상태 결과로 변환
                error_result: UploadStatusResult = {"status": "cancelled"}
                results.append(error_result)

            # 다음 파일 업로드 전 지연
            if i < len(file_paths) - 1 and delay_seconds > 0:
                time.sleep(delay_seconds)

        return results

    def get_upload_summary(self, results: List[UploadResult]) -> Dict[str, int]:
        """
        업로드 결과 요약 생성

        Args:
            results: 업로드 결과 리스트

        Returns:
            결과 요약 딕셔너리
        """
        summary = {"total": len(results), "success": 0, "cancelled": 0, "skipped": 0, "failed": 0}

        for result in results:
            if is_success_result(result):
                summary["success"] += 1
            elif is_status_result(result):
                status = result.get("status", "failed")
                if status == "cancelled":
                    summary["cancelled"] += 1
                elif status == "skipped":
                    summary["skipped"] += 1
                else:
                    summary["failed"] += 1
            else:
                summary["failed"] += 1

        return summary

    def print_upload_summary(self, results: List[UploadResult]) -> None:
        """업로드 결과 요약 출력"""
        summary = self.get_upload_summary(results)

        print("\n📊 업로드 결과 요약:")
        print(f"  전체: {summary['total']}개")
        print(f"  성공: {summary['success']}개 ✅")
        print(f"  취소: {summary['cancelled']}개 ❌")
        print(f"  건너뜀: {summary['skipped']}개 ⏭️")
        print(f"  실패: {summary['failed']}개 🚫")

        success_rate = (summary["success"] / summary["total"] * 100) if summary["total"] > 0 else 0
        print(f"  성공률: {success_rate:.1f}%")

    ###

    def _parse_markdown_to_blocks(self, markdown_content: str) -> List[NotionBasicBlock]:
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

            # 코드 블록 처리
            if line.startswith("```"):
                language = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # closing fence
                code = "\n".join(code_lines)
                blocks.append(self._create_code_block(code, language))
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

    def _parse_text_formatting(self, text: str) -> List[NotionTextRichText]:
        """텍스트 서식 파싱 (굵게, 기울임 등)"""
        # 현재는 단순하게 일반 텍스트로 처리
        # 향후 **굵게**, *기울임* 등을 처리할 수 있음
        if not text:
            return []

        return [
            {"type": "text", "text": {"content": text, "link": None}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}}
        ]

    def _append_blocks_to_page(self, page_id: str, blocks: List[NotionExtendedBlock]) -> NotionAPIResponse:
        """페이지에 블록들 추가"""
        url = safe_url_join(self.base_url, f"blocks/{page_id}/children")
        data = {"children": blocks}

        response = requests.patch(url, headers=self.headers, json=data)
        return response.json()

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
                rich_text.extend(self._parse_text_formatting(part))

        return rich_text

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


def is_success_result(result: UploadResult) -> bool:
    """결과가 성공적인 API 응답인지 확인"""
    return "id" in result and "status" not in result


def is_status_result(result: UploadResult) -> bool:
    """결과가 상태 결과인지 확인"""
    return "status" in result
