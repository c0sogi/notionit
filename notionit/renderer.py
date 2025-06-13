#!/usr/bin/env python3
"""
Notion uploader with full Markdown support powered by Mistune.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast
from urllib.parse import urlparse

import requests

from ._utils import unwrap_callable
from .config import get_config
from .types import (
    NotionBulletedListItemBlock,
    NotionCodeBlock,
    NotionCodeLanguage,
    NotionDividerBlock,
    NotionEquationBlock,
    NotionExtendedBlock,
    NotionFileBlock,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionImageBlock,
    NotionNumberedListItemBlock,
    NotionParagraphBlock,
    NotionQuoteBlock,
    NotionRichText,
    NotionTableBlock,
    NotionTableRowBlock,
    NotionTextRichText,
    StrOrCallable,
)


class NotionFileUploader:
    """Helper class for uploading files to Notion."""

    def __init__(
        self,
        token: StrOrCallable = lambda: get_config("notion_token"),
        base_url: StrOrCallable = lambda: get_config("notion_base_url"),
        notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
    ):
        self.base_url: str = unwrap_callable(base_url)
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {unwrap_callable(token)}",
            "Notion-Version": unwrap_callable(notion_version),
        }

    def upload_file(self, file_path: str) -> Optional[str]:
        """Upload a file and return its ``file_upload_id``."""
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None

            # Check file size (20MB limit)
            file_size = os.path.getsize(file_path)
            if file_size > 20 * 1024 * 1024:  # 20MB
                print(f"File too large (over 20MB): {file_path}")
                return None

            # Step 1: create File Upload object
            upload_obj = self._create_file_upload_object()
            if not upload_obj:
                return None

            file_upload_id = upload_obj["id"]
            upload_url = upload_obj["upload_url"]

            # Step 2: upload file content
            success = self._upload_file_content(upload_url, file_path)
            if not success:
                return None

            return file_upload_id

        except Exception as e:
            print(f"File upload failed: {e}")
            return None

    def _create_file_upload_object(self) -> Optional[Dict[str, Any]]:
        """Create a File Upload object."""
        try:
            response = requests.post(f"{self.base_url}/file_uploads", headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to create File Upload object: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error creating File Upload object: {e}")
            return None

    def _upload_file_content(self, upload_url: str, file_path: str) -> bool:
        """Upload the actual file contents."""
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                # upload_url does not require an Authorization header
                response = requests.post(upload_url, files=files)

            print(f"File upload response status: {response.status_code}")
            if response.status_code != 200:
                print(f"File upload response body: {response.text}")

            return response.status_code == 200

        except Exception as e:
            print(f"Error uploading file content: {e}")
            return False

    def is_supported_image(self, file_path: str) -> bool:
        """Return ``True`` if the image file type is supported."""
        image_extensions = {".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp", ".ico"}
        return Path(file_path).suffix.lower() in image_extensions

    def is_supported_file(self, file_path: str) -> bool:
        """Return ``True`` if the file type is supported."""
        # All supported extensions (images, documents, audio, video)
        supported_extensions = {
            # images
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
            # documents
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
            # audio
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
            # video
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
    """Renderer that converts a Mistune AST into Notion blocks."""

    def __init__(
        self,
        token: StrOrCallable = lambda: get_config("notion_token"),
        base_url: StrOrCallable = lambda: get_config("notion_base_url"),
        notion_version: StrOrCallable = lambda: get_config("notion_api_version"),
    ):
        self.blocks: List[NotionExtendedBlock] = []
        self.file_uploader = NotionFileUploader(
            token=unwrap_callable(token),
            base_url=unwrap_callable(base_url),
            notion_version=unwrap_callable(notion_version),
        )

    def render_ast(self, ast_nodes: List[Dict[str, Any]]) -> List[NotionExtendedBlock]:
        """Convert AST nodes into Notion blocks."""
        self.blocks = []

        for node in ast_nodes:
            self._render_node(node)

        return self.blocks

    def _render_node(self, node: Dict[str, Any]) -> None:
        """Handle a single AST node."""
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
            # Ignore empty lines
            pass
        else:
            # Unknown node type -> treat as paragraph
            self._render_unknown_node(node)

    def _render_heading(self, node: Dict[str, Any]) -> None:
        """Render a heading node."""
        level = node.get("attrs", {}).get("level", 1)
        rich_text = self._render_inline_children(node.get("children", []))

        block: Union[NotionHeading1Block, NotionHeading2Block, NotionHeading3Block]
        if level == 1:
            block = {"object": "block", "type": "heading_1", "heading_1": {"rich_text": rich_text}}
        elif level == 2:
            block = {"object": "block", "type": "heading_2", "heading_2": {"rich_text": rich_text}}
        else:  # level >= 3
            block = {"object": "block", "type": "heading_3", "heading_3": {"rich_text": rich_text}}

        self.blocks.append(block)

    def _render_paragraph(self, node: Dict[str, Any]) -> None:
        """Render a paragraph node."""
        rich_text = self._render_inline_children(node.get("children", []))

        block: NotionParagraphBlock
        if rich_text:  # Skip empty paragraphs
            block = {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}
            self.blocks.append(block)

    def _render_list(self, node: Dict[str, Any]) -> None:
        """Render a list node."""
        is_ordered = node.get("attrs", {}).get("ordered", False)

        for item_node in node.get("children", []):
            if item_node.get("type") == "list_item":
                block = self._render_list_item(item_node, is_ordered)
                if block:
                    self.blocks.append(block)

    def _render_list_item(self, node: Dict[str, Any], is_ordered: bool) -> Optional[NotionExtendedBlock]:
        """Render a list item."""
        # Extract list item contents
        rich_text: List[NotionRichText] = []
        child_blocks: List[NotionExtendedBlock] = []

        for child in node.get("children", []):
            if child.get("type") == "block_text":
                rich_text.extend(self._render_inline_children(child.get("children", [])))
            elif child.get("type") == "paragraph":
                rich_text.extend(self._render_inline_children(child.get("children", [])))
            elif child.get("type") == "block_math":
                child_blocks.append({
                    "object": "block",
                    "type": "equation",
                    "equation": {"expression": child.get("raw", "")},
                })
            elif child.get("type") == "list":
                child_blocks.extend(self._collect_list_blocks(child))

        if not rich_text:
            # Notion requires at least one text item; use empty string
            rich_text.append({
                "type": "text",
                "text": {"content": "", "link": None},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
            })

        if is_ordered:
            ordered_block: NotionNumberedListItemBlock = {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": rich_text},
            }
            if child_blocks:
                ordered_block["numbered_list_item"]["children"] = child_blocks
            return ordered_block
        else:
            bullet_block: NotionBulletedListItemBlock = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text},
            }
            if child_blocks:
                bullet_block["bulleted_list_item"]["children"] = child_blocks
            return bullet_block

    def _collect_list_blocks(self, node: Dict[str, Any]) -> List[NotionExtendedBlock]:
        """Collect blocks from a nested list node."""
        blocks: List[NotionExtendedBlock] = []
        is_ordered = node.get("attrs", {}).get("ordered", False)
        for item in node.get("children", []):
            if item.get("type") == "list_item":
                block = self._render_list_item(item, is_ordered)
                if block:
                    blocks.append(block)
        return blocks

    def _render_code_block(self, node: Dict[str, Any]) -> None:
        """Render a code block."""
        code = node.get("raw", "")
        language = node.get("attrs", {}).get("info", "plain text")

        # Create proper rich text for code content
        code_rich_text: List[NotionRichText] = [
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
            },
        ]
        block: NotionCodeBlock = {
            "object": "block",
            "type": "code",
            "code": {"rich_text": code_rich_text, "language": cast(NotionCodeLanguage, self._map_language(language))},
        }
        self.blocks.append(block)

    def _render_block_quote(self, node: Dict[str, Any]) -> None:
        """Render a block quote."""
        rich_text: List[NotionRichText] = []

        for idx, child in enumerate(node.get("children", [])):
            text_content = self._extract_text_from_ast(child)
            if text_content:
                if idx > 0:
                    rich_text.append(self._render_break())
                rich_text.append(self._render_text({"raw": text_content}))

        if rich_text:
            block: NotionQuoteBlock = {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": rich_text},
            }
            self.blocks.append(block)

    def _render_divider(self) -> None:
        """Render a divider."""
        block: NotionDividerBlock = {"object": "block", "type": "divider", "divider": {}}
        self.blocks.append(block)

    def _render_table(self, node: Dict[str, Any]) -> None:
        """Render a table by creating actual Notion table blocks."""
        try:
            # Analyze table structure
            table_data = self._analyze_table_structure(node)

            if not table_data["rows"]:
                # Empty table -> render as paragraph
                self._render_empty_table_fallback()
                return

            # Create table row blocks
            table_row_blocks: List[NotionTableRowBlock] = []
            for row_data in table_data["rows"]:
                row_block = self._create_table_row_block(row_data, table_data["column_count"])
                table_row_blocks.append(row_block)

            # Create table block with children
            table_block: NotionTableBlock = {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": table_data["column_count"],
                    "has_column_header": table_data["has_header"],
                    "has_row_header": False,  # Markdown tables usually have no row headers
                    "children": table_row_blocks,
                },
            }
            self.blocks.append(table_block)

        except Exception as e:
            # Fallback to code block if table parsing fails
            print(f"Table rendering failed, falling back to code block: {e}")
            self._render_table_fallback(node)

    def _analyze_table_structure(self, table_node: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the structure of a table node."""
        children = table_node.get("children", [])

        thead_nodes = [child for child in children if child.get("type") == "table_head"]
        tbody_nodes = [child for child in children if child.get("type") == "table_body"]

        all_rows: List[List[List[NotionRichText]]] = []
        has_header = False

        # Handle header rows
        if thead_nodes:
            has_header = True
            header_rows = self._extract_table_rows(thead_nodes[0])
            all_rows.extend(header_rows)

        # Handle body rows
        if tbody_nodes:
            body_rows = self._extract_table_rows(tbody_nodes[0])
            all_rows.extend(body_rows)

        # Determine column count using the first row
        column_count = len(all_rows[0]) if all_rows else 0

        return {"rows": all_rows, "column_count": column_count, "has_header": has_header}

    def _extract_table_rows(self, section_node: Dict[str, Any]) -> List[List[List[NotionRichText]]]:
        """Extract row data from a table section."""
        rows: List[List[List[NotionRichText]]] = []

        # Special handling when table_head directly contains table_cell children
        if section_node.get("type") == "table_head":
            # Treat table_head as a single row
            row_cells: List[List[NotionRichText]] = []
            for cell_node in section_node.get("children", []):
                if cell_node.get("type") == "table_cell":
                    cell_content = self._extract_cell_content(cell_node)
                    row_cells.append(cell_content)

            if row_cells:  # Exclude empty rows
                rows.append(row_cells)
        else:
            # For table_body use the existing logic
            for row_node in section_node.get("children", []):
                if row_node.get("type") == "table_row":
                    row_cells: List[List[NotionRichText]] = []

                    for cell_node in row_node.get("children", []):
                        if cell_node.get("type") == "table_cell":
                            cell_content = self._extract_cell_content(cell_node)
                            row_cells.append(cell_content)

                    if row_cells:  # Skip empty rows
                        rows.append(row_cells)

        return rows

    def _extract_cell_content(self, cell_node: Dict[str, Any]) -> List[NotionRichText]:
        """Extract rich text content from a cell node."""
        return self._render_inline_children(cell_node.get("children", []))

    def _create_table_row_block(self, row_data: List[List[NotionRichText]], expected_columns: int) -> NotionTableRowBlock:
        """Create a table row block."""
        # Pad rows with empty cells if needed
        while len(row_data) < expected_columns:
            row_data.append([])

        # Trim extra columns
        row_data = row_data[:expected_columns]

        # Convert each cell to a rich_text array
        cells: List[List[NotionRichText]] = []
        for cell_content in row_data:
            cell_rich_text: List[NotionRichText] = cell_content if cell_content else []
            cells.append(cell_rich_text)

        return {"object": "block", "type": "table_row", "table_row": {"cells": cells}}

    def _render_table_fallback(self, node: Dict[str, Any]) -> None:
        """Fallback rendering when table parsing fails (code block)."""
        table_text = self._extract_table_text(node)

        block = {
            "object": "block",
            "type": "code",
            "code": {"rich_text": [{"type": "text", "text": {"content": table_text}}], "language": "plain text"},
        }
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_empty_table_fallback(self) -> None:
        """Handle an empty table."""
        block: NotionParagraphBlock = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": "[empty table]", "link": None},
                        "annotations": {
                            "bold": False,
                            "italic": True,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "gray",
                        },
                    }
                ]
            },
        }
        self.blocks.append(block)

    def _render_math_block(self, node: Dict[str, Any]) -> None:
        """Render a math block."""
        equation = node.get("raw", "")

        block: NotionEquationBlock = {"object": "block", "type": "equation", "equation": {"expression": equation}}
        self.blocks.append(block)

    def _render_unknown_node(self, node: Dict[str, Any]) -> None:
        """Render unknown nodes as paragraphs."""
        text = str(node.get("raw", ""))
        if text:
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            }
            self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_inline_children(self, children: List[Dict[str, Any]]) -> List[NotionRichText]:
        """Convert inline child nodes to Notion RichText."""
        rich_text: List[NotionRichText] = []

        for child in children:
            child_type = str(child.get("type"))
            if child_type == "strong":
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
                rich_text.append(self._render_text(child))

        return rich_text

    def _render_text(self, node: Dict[str, Any]) -> NotionTextRichText:
        """Render plain text."""
        return {
            "type": "text",
            "text": {"content": node.get("raw", ""), "link": None},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
        }

    def _render_strong(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """Render bold text."""
        children_text = self._render_inline_children(node.get("children", []))

        # Apply bold to all child text
        for text_item in children_text:
            if text_item["type"] == "text":
                text_item["annotations"]["bold"] = True

        return children_text

    def _render_emphasis(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """Render italic text."""
        children_text = self._render_inline_children(node.get("children", []))

        # Apply italic to all child text
        for text_item in children_text:
            if text_item["type"] == "text":
                text_item["annotations"]["italic"] = True

        return children_text

    def _render_strikethrough(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """Render strikethrough text."""
        children_text = self._render_inline_children(node.get("children", []))

        # Apply strikethrough to all child text
        for text_item in children_text:
            if text_item["type"] == "text":
                text_item["annotations"]["strikethrough"] = True

        return children_text

    def _render_codespan(self, node: Dict[str, Any]) -> NotionTextRichText:
        """Render inline code."""
        content = node.get("raw", "")

        return {
            "type": "text",
            "text": {"content": content, "link": None},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": True,
                "color": "default",
            },
        }

    def _render_link(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """Render a link; file links become file blocks."""
        url = node.get("attrs", {}).get("url", "")
        children_text = self._render_inline_children(node.get("children", []))

        # Check if the link points to a file
        if self._is_file_link(url):
            # Create a file block
            self._render_file_block(url, self._get_link_text(children_text))
            return []  # Do not return inline text

        # Only apply link if the URL is valid (skip anchors and invalid URLs)
        if self._is_valid_url(url):
            for text_item in children_text:
                if text_item["type"] == "text":
                    text_item["text"]["link"] = {"url": url}

        return children_text

    def _is_file_link(self, url: str) -> bool:
        """Return ``True`` if the link points to a file."""
        if not url:
            return False

        # Local file path
        if self._is_local_file_path(url):
            return bool(self.file_uploader and self.file_uploader.is_supported_file(url))

        # For URLs, decide based on the extension
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            file_extensions = {
                ".pdf",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
                ".ppt",
                ".pptx",
                ".txt",
                ".json",
                ".zip",
                ".rar",
                ".7z",
                ".mp3",
                ".wav",
                ".mp4",
                ".avi",
                ".mov",
            }
            return any(path.endswith(ext) for ext in file_extensions)
        except Exception:
            return False

    def _get_link_text(self, children_text: List[NotionRichText]) -> str:
        """Extract link text."""
        text_parts: List[str] = []
        for item in children_text:
            if item.get("type") == "text" and "text" in item:
                text_parts.append(item.get("text", {}).get("content", ""))
        return "".join(text_parts)

    def _render_file_block(self, url: str, link_text: str = "") -> None:
        """Create a file block."""
        try:
            # Check if the URL is a local file path
            if self._is_local_file_path(url):
                # Upload local file
                if self.file_uploader and self.file_uploader.is_supported_file(url):
                    file_upload_id = self.file_uploader.upload_file(url)
                    if file_upload_id:
                        # Create file block from uploaded file
                        block = {
                            "object": "block",
                            "type": "file",
                            "file": {
                                "type": "file_upload",
                                "file_upload": {"id": file_upload_id},
                                "caption": [{"type": "text", "text": {"content": link_text, "link": None}}]
                                if link_text
                                else [],
                            },
                        }
                        self.blocks.append(cast(NotionFileBlock, block))
                        return
                    else:
                        print(f"File upload failed: {url}")
                else:
                    print(f"Unsupported file: {url}")

            # For external URLs or failed uploads use external type
            if self._is_valid_url(url):
                block = {
                    "object": "block",
                    "type": "file",
                    "file": {
                        "type": "external",
                        "external": {"url": url},
                        "caption": [{"type": "text", "text": {"content": link_text, "link": None}}]
                        if link_text
                        else [],
                    },
                }
                self.blocks.append(cast(NotionFileBlock, block))
            else:
                # Fallback to text for invalid URL
                self._render_file_fallback(url, link_text)

        except Exception as e:
            print(f"Failed to create file block: {e}")
            self._render_file_fallback(url, link_text)

    def _render_file_fallback(self, url: str, link_text: str) -> None:
        """Fallback to plain text when file rendering fails."""
        content = f"[File: {link_text}]({url})" if link_text else f"[File]({url})"
        block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": content, "link": {"url": url} if self._is_valid_url(url) else None},
                        "annotations": {
                            "bold": False,
                            "italic": True,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "blue",
                        },
                    }
                ]
            },
        }
        self.blocks.append(cast(NotionExtendedBlock, block))

    def _render_image(self, node: Dict[str, Any]) -> List[NotionRichText]:
        """Render an image; block-level images are handled separately."""
        url = node.get("attrs", {}).get("url", "")
        alt_text = ""

        for child in node.get("children", []):
            if child.get("type") == "text":
                alt_text = child.get("raw", "")
                break

        # If the image stands alone (block level) create an actual image block
        if self._is_standalone_image(node):
            self._render_image_block(url, alt_text)
            return []  # Do not return inline text

        # Inline image -> represent as text
        content = f"[Image: {alt_text}]({url})" if alt_text else f"[Image]({url})"

        return [
            cast(
                NotionTextRichText,
                {
                    "type": "text",
                    "text": {"content": content, "link": {"url": url}},
                    "annotations": {
                        "bold": False,
                        "italic": True,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "gray",
                    },
                },
            )
        ]

    def _is_standalone_image(self, node: Dict[str, Any]) -> bool:
        """Return ``True`` if the image is the only child of a paragraph."""
        # Simple heuristic for now
        return True

    def _render_image_block(self, url: str, alt_text: str = "") -> None:
        """Create an actual image block."""
        try:
            # Check if the URL is a local file path
            if self._is_local_file_path(url):
                # Upload local image
                if self.file_uploader and self.file_uploader.is_supported_image(url):
                    file_upload_id = self.file_uploader.upload_file(url)
                    if file_upload_id:
                        # Create image block from uploaded file
                        block = {
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "file_upload",
                                "file_upload": {"id": file_upload_id},
                                "caption": [{"type": "text", "text": {"content": alt_text, "link": None}}]
                                if alt_text
                                else [],
                            },
                        }
                        self.blocks.append(cast(NotionImageBlock, block))
                        return
                    else:
                        print(f"Image upload failed: {url}")
                else:
                    print(f"Unsupported image file: {url}")

            # For external URLs or failed uploads use external type
            if self._is_valid_url(url):
                block = {
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": url},
                        "caption": [{"type": "text", "text": {"content": alt_text, "link": None}}] if alt_text else [],
                    },
                }
                self.blocks.append(cast(NotionImageBlock, block))
            else:
                # Fallback to text for invalid URL
                self._render_image_fallback(url, alt_text)

        except Exception as e:
            print(f"Failed to create image block: {e}")
            self._render_image_fallback(url, alt_text)

    def _render_image_fallback(self, url: str, alt_text: str) -> None:
        """Fallback to text when image rendering fails."""
        content = f"[Image: {alt_text}]({url})" if alt_text else f"[Image]({url})"
        block: NotionParagraphBlock = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": content, "link": {"url": url} if self._is_valid_url(url) else None},
                        "annotations": {
                            "bold": False,
                            "italic": True,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "gray",
                        },
                    }
                ]
            },
        }
        self.blocks.append(block)

    def _is_local_file_path(self, path: str) -> bool:
        """Return ``True`` if ``path`` is a local file path."""
        # When the URL scheme is missing or ``file://``
        parsed = urlparse(path)
        return not parsed.scheme or parsed.scheme == "file"

    def _is_valid_url(self, url: str) -> bool:
        """Return ``True`` if ``url`` is a valid URL."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def _render_inline_math(self, node: Dict[str, Any]) -> NotionRichText:
        """Render inline math."""
        equation = node.get("raw", "")

        return {"type": "equation", "equation": {"expression": equation}}

    def _render_break(self) -> NotionTextRichText:
        """Render a line break."""
        return {
            "type": "text",
            "text": {"content": "\n", "link": None},
            "annotations": {
                "bold": False,
                "italic": False,
                "strikethrough": False,
                "underline": False,
                "code": False,
                "color": "default",
            },
        }

    def _map_language(self, language: str) -> str:
        """Map a language code to the format Notion expects."""
        language_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "sh": "shell",
            "bash": "shell",
            "yml": "yaml",
            "md": "markdown",
            "": "plain text",
        }

        return language_map.get(language.lower(), language.lower())

    def _extract_table_text(self, node: Dict[str, Any]) -> str:
        """Extract plain text from a table node."""
        # Simple extraction for now
        return str(node.get("raw", "Table content"))

    def _extract_text_from_ast(self, node: Any) -> str:
        """Recursively extract raw text from a Mistune AST node."""
        if isinstance(node, dict):
            node_dict = cast(Dict[object, object], node)
            if node_dict.get("type") == "text":
                return str(node_dict.get("raw", ""))
            if (children := node_dict.get("children")) and isinstance(children, list):
                children = cast(List[Any], children)
                return "".join(self._extract_text_from_ast(child) for child in children)
            if raw := node_dict.get("raw"):
                return str(raw)
        return ""
