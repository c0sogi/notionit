#!/usr/bin/env python3
"""
Advanced Notion Markdown uploader.

Supports code blocks, equation normalization, debug output and other advanced features.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, TypeGuard, Union

import mistune
import requests

from ._utils import format_upload_error_message, format_upload_success_message, safe_url_join, unwrap_callable
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
    StrOrCallable,
    UploadResult,
    UploadStatusResult,
)


class NotionUploader:
    """Advanced Notion Markdown uploader."""

    def __init__(
        self,
        token: StrOrCallable = lambda: get_config("notion_token"),
        base_url: StrOrCallable = lambda: get_config("notion_base_url"),
        notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
        plugins: Optional[Union[Iterable[mistune.plugins.PluginRef], Callable[[], Iterable[mistune.plugins.PluginRef]]]] = lambda: get_config("notion_parser_plugins").split(","),
        debug: bool = False,
        renderer: mistune.RendererRef = "ast",
        escape: bool = True,
        hard_wrap: bool = False,
    ) -> None:
        """
        Initialize the uploader.

        Args:
            token: Notion API token
            debug: Enable debug output
        """
        token = unwrap_callable(token)
        base_url = unwrap_callable(base_url)
        notion_version = unwrap_callable(notion_version)
        self.token: str = token
        self.debug: bool = debug
        self.base_url: str = base_url
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": notion_version,
        }
        self.markdown_parser: mistune.Markdown = mistune.create_markdown(renderer=renderer, escape=escape, hard_wrap=hard_wrap, plugins=unwrap_callable(plugins))
        self.notion_renderer = MistuneNotionRenderer(token=token, base_url=base_url, notion_version=notion_version)

    def create_page(self, parent_page_id: str, title: str, blocks: Sequence[NotionExtendedBlock]) -> NotionAPIResponse:
        """
        Create a new Notion page.

        Args:
            parent_page_id: Parent page ID
            title: Page title
            blocks: List of Notion blocks

        Returns:
            Notion API response
        """
        url = safe_url_join(self.base_url, "pages")
        data: NotionExtendedCreatePageRequest = {
            "parent": {"page_id": parent_page_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": list(blocks),
        }

        if self.debug:
            print(f"🔍 Blocks to create: {len(blocks)}")
            for i, block in enumerate(blocks):
                if block["type"] == "equation":
                    print(f"  📐 Equation block {i + 1}: {block['equation']['expression']}")
                else:
                    print(f"  📝 {block['type']} block {i + 1}")

        response = requests.post(url, headers=self.headers, json=data)
        result = response.json()

        if response.status_code != 200 and self.debug:
            print(f"❌ API error (Status: {response.status_code}):")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        return result

    def parse_markdown_to_blocks(self, markdown_content: str) -> List[NotionExtendedBlock]:
        """
        Parse Markdown text into Notion blocks using Mistune.

        Args:
            markdown_content: Markdown text

        Returns:
            List of Notion blocks
        """
        try:
            # Parse with Mistune (extract AST from tuple result)
            parse_result = self.markdown_parser.parse(markdown_content)
            if isinstance(parse_result, tuple):  # pyright: ignore[reportUnnecessaryIsInstance]
                ast_nodes = parse_result[0]
            else:
                ast_nodes = parse_result

            # Handle case where AST is a string
            if isinstance(ast_nodes, str):
                raise TypeError("Mistune returned a string")

            # Convert AST to Notion blocks
            blocks = self.notion_renderer.render_ast(ast_nodes)

            return blocks

        except Exception as e:
            # Fall back to the legacy parser on failure
            print(f"Failed to parse with Mistune, falling back to legacy method: {e}")
            return list(self.parse_markdown_to_basic_blocks(markdown_content))

    def parse_markdown_to_basic_blocks(self, markdown_content: str) -> List[NotionBasicBlock]:
        """
        Convert Markdown to Notion blocks.

        Args:
            markdown_content: Markdown text

        Returns:
            List of Notion blocks
        """
        blocks: List[NotionBasicBlock] = []
        lines = markdown_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Handle block equations ($$...$$)
            if line.startswith("$$") and line.endswith("$$"):
                equation = line[2:-2].strip()
                blocks.append(self._create_equation_block(equation))
                i += 1
                continue

            # Multi-line block equation
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

            # Code block
            if line.startswith("```"):
                language = line[3:].strip()
                code_lines: List[str] = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # closing fence
                code = "\n".join(code_lines)
                blocks.append(self._create_code_block(code, language))
                continue

            # Heading
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                text = line.lstrip("# ").strip()
                blocks.append(self._create_heading_block(text, level))
                i += 1
                continue

            # Regular paragraph (may include inline math)
            paragraph_lines = [line]
            i += 1

            # Collect subsequent lines in the same paragraph
            while i < len(lines) and lines[i].strip() and not self._is_special_line(lines[i]):
                paragraph_lines.append(lines[i].strip())
                i += 1

            paragraph_text = " ".join(paragraph_lines)
            blocks.append(self._create_paragraph_block(paragraph_text))

        return blocks

    def check_existing_pages_with_title(self, title: str) -> List[NotionSearchResultPage]:
        """
        Search for existing pages with the same title.

        Args:
            title: Page title to search for

        Returns:
            List of pages with the same title
        """
        url = safe_url_join(self.base_url, "search")
        search_data = {"query": title, "filter": {"value": "page", "property": "object"}}

        response = requests.post(url, headers=self.headers, json=search_data)
        result: NotionSearchResponse = response.json()

        if "results" in result:
            # Filter only exact title matches
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
        Generate a unique title.

        Args:
            base_title: Base title
            strategy: Uniqueness strategy ("timestamp", "counter", "hash")

        Returns:
            Unique title
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
            # Hash based on file content
            file_hash = hashlib.md5(base_title.encode()).hexdigest()[:8]
            return f"{base_title} ({file_hash})"

        return base_title

    def upload_markdown_file(
        self,
        file_path: str,
        parent_page_id: str,
        page_title: Optional[str] = None,
        duplicate_strategy: Optional[DuplicateStrategy] = None,
        progress: Optional[Callable[[float], None]] = None,
    ) -> UploadResult:
        """
        Upload a Markdown file.

        Args:
            file_path: Path to the Markdown file
            parent_page_id: Parent page ID
            page_title: Page title (defaults to file name)
            duplicate_strategy: Strategy for handling duplicates
            progress: Optional callback receiving progress percentage (0.0-1.0)

        Returns:
            Upload result (success response or status)
        """
        path = Path(file_path)

        if page_title is None:
            page_title = path.stem

        # Check for existing pages with the same title
        if duplicate_strategy is not None and (existing_pages := self.check_existing_pages_with_title(page_title)):
            if self.debug:
                print(f"⚠️  {len(existing_pages)} pages with the same title '{page_title}' exist.")

            if duplicate_strategy == "ask":
                print(f"⚠️  {len(existing_pages)} pages with the same title '{page_title}' exist.")
                print("How would you like to proceed?")
                print("1. Add timestamp and create a new page")
                print("2. Add counter and create a new page")
                print("3. Ignore and create anyway")
                print("4. Cancel upload")

                choice = input("Choose (1-4): ").strip()
                if choice == "1":
                    duplicate_strategy = "timestamp"
                elif choice == "2":
                    duplicate_strategy = "counter"
                elif choice == "3":
                    duplicate_strategy = "create_anyway"
                else:
                    print("❌ Upload cancelled.")
                    return {"status": "cancelled"}

            if duplicate_strategy == "timestamp":
                page_title = self.generate_unique_title(page_title, "timestamp")
                if self.debug:
                    print(f"📝 New title: {page_title}")

            elif duplicate_strategy == "counter":
                page_title = self.generate_unique_title(page_title, "counter")
                if self.debug:
                    print(f"📝 New title: {page_title}")

            elif duplicate_strategy == "skip":
                if self.debug:
                    print("⏭️  Skipping upload.")
                return {"status": "skipped"}

        # Proceed with normal upload
        result = self._upload_markdown_file(
            file_path=file_path,
            parent_page_id=parent_page_id,
            page_title=page_title,
            progress=progress,
        )
        return result

    def upload_markdown_files(
        self,
        file_paths: List[str],
        parent_page_id: str,
        page_title: Optional[str] = None,
        duplicate_strategy: Optional[DuplicateStrategy] = None,
        delay_seconds: float = 1.0,
        progress: Optional[Callable[[float], None]] = None,
    ) -> List[UploadResult]:
        """
        Upload multiple files in batch.

        Args:
            file_paths: List of file paths to upload
            parent_page_id: Parent page ID
            duplicate_strategy: Strategy for handling duplicates
            delay_seconds: Delay between files in seconds

        Returns:
            List of upload results
        """
        results: List[UploadResult] = []

        if progress is not None:
            progress(0.0)

        for i, file_path in enumerate(file_paths, start=1):
            if self.debug:
                print(f"\n📁 {i + 1}/{len(file_paths)}: {file_path}")

            try:
                result = self.upload_markdown_file(
                    file_path=file_path,
                    parent_page_id=parent_page_id,
                    page_title=page_title,
                    duplicate_strategy=duplicate_strategy,
                )
                results.append(result)

                if is_success_result(result):
                    if self.debug:
                        print(format_upload_success_message(result))
                else:
                    if self.debug:
                        print(format_upload_error_message(result))

            except Exception as e:
                if self.debug:
                    print(f"❌ Upload failed: {e}")
                # Convert the error to a status result
                error_result: UploadStatusResult = {"status": "cancelled"}
                results.append(error_result)
            finally:
                if progress is not None:
                    progress(i / len(file_paths))

            # Delay before uploading the next file
            if i < len(file_paths) and delay_seconds > 0:
                time.sleep(delay_seconds)

        if progress is not None:
            progress(1.0)

        return results

    def get_upload_summary(self, results: List[UploadResult]) -> Dict[str, int]:
        """
        Generate a summary of upload results.

        Args:
            results: List of upload results

        Returns:
            Summary dictionary
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
        """Print upload summary."""
        summary = self.get_upload_summary(results)

        print("\n📊 Upload summary:")
        print(f"  Total: {summary['total']}")
        print(f"  Success: {summary['success']} ✅")
        print(f"  Cancelled: {summary['cancelled']} ❌")
        print(f"  Skipped: {summary['skipped']} ⏭️")
        print(f"  Failed: {summary['failed']} 🚫")

        success_rate = (summary["success"] / summary["total"] * 100) if summary["total"] > 0 else 0
        print(f"  Success rate: {success_rate:.1f}%")

    def _upload_markdown_file(
        self,
        file_path: str,
        parent_page_id: str,
        page_title: Optional[str] = None,
        progress: Optional[Callable[[float], None]] = None,
    ) -> NotionAPIResponse:
        """
        Upload a Markdown file to Notion.

        Args:
            file_path: Path to the Markdown file
            parent_page_id: Parent page ID
            page_title: Page title (defaults to file name)

        Returns:
            Notion API response

        Raises:
            FileNotFoundError: When the file does not exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if page_title is None:
            page_title = path.stem

        blocks = self.parse_markdown_to_blocks(content)

        # Split into chunks of 100 blocks (API limit)
        block_chunks = [blocks[i : i + 100] for i in range(0, len(blocks), 100)]
        total_chunks = max(len(block_chunks), 1)
        if progress is not None:
            progress(0.0)

        # Create page with the first chunk
        result = self.create_page(
            parent_page_id=parent_page_id,
            title=page_title,
            blocks=block_chunks[0] if block_chunks else [],
        )

        if "id" not in result:
            if progress is not None:
                progress(1.0)
            return result

        page_id = result["id"]
        if progress is not None:
            progress(1 / total_chunks)

        # Append remaining chunks as children
        for index, chunk in enumerate(block_chunks[1:], start=1):
            self._append_blocks_to_page(page_id, chunk)
            if progress is not None:
                progress((index + 1) / total_chunks)

        if progress is not None:
            progress(1.0)
        return result

    def _parse_text_formatting(self, text: str) -> List[NotionTextRichText]:
        """Parse basic text formatting such as bold or italic."""
        # Currently treated as plain text
        # Future: handle **bold**, *italic*, etc.
        if not text:
            return []

        return [
            {
                "type": "text",
                "text": {"content": text, "link": None},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
            }
        ]

    def _append_blocks_to_page(self, page_id: str, blocks: List[NotionExtendedBlock]) -> NotionAPIResponse:
        """Append blocks to a page."""
        url = safe_url_join(self.base_url, f"blocks/{page_id}/children")
        data = {"children": blocks}

        response = requests.patch(url, headers=self.headers, json=data)
        return response.json()

    def _create_code_block(self, code: str, language: str = "") -> NotionCodeBlock:
        """Create a code block."""
        normalized_language = self._normalize_language(language)

        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": code, "link": None},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default",
                        },
                    }
                ],
                "language": normalized_language,
            },
        }

    def _create_heading_block(self, text: str, level: int) -> Union[NotionHeading1Block, NotionHeading2Block, NotionHeading3Block]:
        """Create a heading block."""
        # Notion supports only heading_1, heading_2 and heading_3
        level = min(level, 3)

        rich_text: List[NotionRichText] = [
            {
                "type": "text",
                "text": {"content": text, "link": None},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
            }
        ]

        if level == 1:
            return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text}}
        elif level == 2:
            return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text}}
        else:  # level == 3
            return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text}}

    def _create_paragraph_block(self, text: str) -> NotionParagraphBlock:
        """Create a paragraph block (supports inline math)."""
        rich_text = self._parse_inline_content(text)
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}

    def _parse_inline_content(self, text: str) -> List[NotionRichText]:
        """Parse text containing inline math and formatting."""
        rich_text: List[NotionRichText] = []

        # Split by inline math (single $)
        parts = re.split(r"(\$[^$]+\$)", text)

        for part in parts:
            if not part:
                continue

            if part.startswith("$") and part.endswith("$"):
                # Inline equation
                equation = part[1:-1]
                if self.debug:
                    print(f"      💫 Inline math: {equation}")
                rich_text.append({"type": "equation", "equation": {"expression": equation}})
            else:
                # Plain text
                rich_text.extend(self._parse_text_formatting(part))

        return rich_text

    def _is_special_line(self, line: str) -> bool:
        """Return True if the line starts a special block."""
        stripped = line.strip()
        return stripped.startswith("#") or stripped == "$$" or stripped.startswith("```")

    def _create_equation_block(self, equation: str) -> NotionEquationBlock:
        """Create an equation block (includes LaTeX normalization)."""
        # Normalize equation
        equation = equation.strip()

        # Simple replacements for Notion compatibility
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
            print(f"    🔧 Normalized equation: {equation}")

        return {"object": "block", "type": "equation", "equation": {"expression": equation}}

    def _normalize_language(self, language: str) -> NotionCodeLanguage:
        """Normalize a language string to one supported by Notion."""
        language = language.lower().strip()

        # Mapping of common aliases
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

        # Direct mapping if possible
        if language in language_map:
            return language_map[language]

        # Check if the language is a valid Notion language
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

        # Default to plain text for unknown languages
        return "plain text"


def is_success_result(result: UploadResult) -> TypeGuard[NotionAPIResponse]:
    """Return True if the result is a successful API response."""
    return "id" in result and "status" not in result


def is_status_result(result: UploadResult) -> TypeGuard[UploadStatusResult]:
    """Return True if the result is a status response."""
    return "status" in result
