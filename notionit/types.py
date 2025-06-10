#!/usr/bin/env python3
"""
Collection of Notion API type definitions.

All TypedDict and Literal types are defined here.
"""

from typing import Callable, Dict, List, Literal, Optional, TypedDict, Union

# Common types for config
StrOrCallable = Union[str, Callable[[], str]]

# Color types for Notion
NotionColor = Literal[
    "default",
    "gray",
    "brown",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "red",
    "gray_background",
    "brown_background",
    "orange_background",
    "yellow_background",
    "green_background",
    "blue_background",
    "purple_background",
    "pink_background",
    "red_background",
]

# Programming languages supported by Notion
NotionCodeLanguage = Literal[
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


# Basic content types
class NotionLinkObject(TypedDict):
    url: str


class NotionTextContent(TypedDict):
    content: str
    link: Optional[NotionLinkObject]


class NotionTextAnnotations(TypedDict):
    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: NotionColor


# Rich text types
class NotionTextRichText(TypedDict):
    type: Literal["text"]
    text: NotionTextContent
    annotations: NotionTextAnnotations


class NotionEquationRichText(TypedDict):
    type: Literal["equation"]
    equation: Dict[Literal["expression"], str]


NotionRichText = Union[NotionTextRichText, NotionEquationRichText]


# File object types for blocks
class NotionFileUploadObject(TypedDict):
    id: str


class NotionExternalFileObject(TypedDict):
    url: str


class NotionFileObject(TypedDict):
    url: str
    expiry_time: str


class NotionFileContent(TypedDict, total=False):
    type: Literal["external", "file", "file_upload"]
    external: NotionExternalFileObject
    file: NotionFileObject
    file_upload: NotionFileUploadObject
    caption: List[NotionRichText]
    name: str


class NotionImageContent(TypedDict, total=False):
    type: Literal["external", "file", "file_upload"]
    external: NotionExternalFileObject
    file: NotionFileObject
    file_upload: NotionFileUploadObject
    caption: List[NotionRichText]


# Block types
class NotionEquationBlock(TypedDict):
    object: Literal["block"]
    type: Literal["equation"]
    equation: Dict[Literal["expression"], str]


class NotionHeadingContent(TypedDict):
    rich_text: List[NotionRichText]


class NotionHeading1Block(TypedDict):
    object: Literal["block"]
    type: Literal["heading_1"]
    heading_1: NotionHeadingContent


class NotionHeading2Block(TypedDict):
    object: Literal["block"]
    type: Literal["heading_2"]
    heading_2: NotionHeadingContent


class NotionHeading3Block(TypedDict):
    object: Literal["block"]
    type: Literal["heading_3"]
    heading_3: NotionHeadingContent


class NotionParagraphContent(TypedDict):
    rich_text: List[NotionRichText]


class NotionParagraphBlock(TypedDict):
    object: Literal["block"]
    type: Literal["paragraph"]
    paragraph: NotionParagraphContent


class NotionCodeContent(TypedDict):
    rich_text: List[NotionRichText]
    language: NotionCodeLanguage


class NotionCodeBlock(TypedDict):
    object: Literal["block"]
    type: Literal["code"]
    code: NotionCodeContent


class NotionBulletedListItemContent(TypedDict, total=False):
    rich_text: List[NotionRichText]
    children: List["NotionExtendedBlock"]


class NotionBulletedListItemBlock(TypedDict):
    object: Literal["block"]
    type: Literal["bulleted_list_item"]
    bulleted_list_item: NotionBulletedListItemContent


class NotionNumberedListItemContent(TypedDict, total=False):
    rich_text: List[NotionRichText]
    children: List["NotionExtendedBlock"]


class NotionNumberedListItemBlock(TypedDict):
    object: Literal["block"]
    type: Literal["numbered_list_item"]
    numbered_list_item: NotionNumberedListItemContent


class NotionQuoteContent(TypedDict):
    rich_text: List[NotionRichText]


class NotionQuoteBlock(TypedDict):
    object: Literal["block"]
    type: Literal["quote"]
    quote: NotionQuoteContent


# Empty dict type for divider
class EmptyDict(TypedDict):
    pass


class NotionDividerBlock(TypedDict):
    object: Literal["block"]
    type: Literal["divider"]
    divider: EmptyDict


class NotionFileBlock(TypedDict):
    object: Literal["block"]
    type: Literal["file"]
    file: NotionFileContent


class NotionImageBlock(TypedDict):
    object: Literal["block"]
    type: Literal["image"]
    image: NotionImageContent


class NotionTableContent(TypedDict):
    table_width: int
    has_column_header: bool
    has_row_header: bool
    children: List["NotionTableRowBlock"]


class NotionTableBlock(TypedDict):
    object: Literal["block"]
    type: Literal["table"]
    table: NotionTableContent


class NotionTableRowContent(TypedDict):
    cells: List[List[NotionRichText]]


class NotionTableRowBlock(TypedDict):
    object: Literal["block"]
    type: Literal["table_row"]
    table_row: NotionTableRowContent


# Block unions
NotionBasicBlock = Union[
    NotionEquationBlock,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionParagraphBlock,
    NotionCodeBlock,
]

NotionExtendedBlock = Union[
    NotionEquationBlock,
    NotionHeading1Block,
    NotionHeading2Block,
    NotionHeading3Block,
    NotionParagraphBlock,
    NotionCodeBlock,
    NotionBulletedListItemBlock,
    NotionNumberedListItemBlock,
    NotionQuoteBlock,
    NotionDividerBlock,
    NotionFileBlock,
    NotionImageBlock,
    NotionTableBlock,
    NotionTableRowBlock,
]


# Page creation types
class NotionTitleTextObject(TypedDict):
    text: Dict[Literal["content"], str]


class NotionTitleProperty(TypedDict):
    title: List[NotionTitleTextObject]


class NotionPageProperties(TypedDict):
    title: NotionTitleProperty


class NotionPageParent(TypedDict):
    page_id: str


class NotionCreatePageRequest(TypedDict):
    parent: NotionPageParent
    properties: NotionPageProperties
    children: List[NotionBasicBlock]


class NotionExtendedCreatePageRequest(TypedDict):
    parent: NotionPageParent
    properties: NotionPageProperties
    children: List[NotionExtendedBlock]


# API response types
class NotionUser(TypedDict):
    object: Literal["user"]
    id: str


class NotionPageResponseProperties(TypedDict):
    title: Dict[Literal["id", "type", "title"], Union[str, List[NotionTitleTextObject]]]


class NotionAPIResponse(TypedDict, total=False):
    # Success fields
    id: str
    object: Literal["page"]
    created_time: str
    last_edited_time: str
    created_by: NotionUser
    last_edited_by: NotionUser
    cover: Optional[Dict[Literal["type", "external", "file"], Union[str, Dict[str, str]]]]
    icon: Optional[Dict[Literal["type", "emoji", "external", "file"], Union[str, Dict[str, str]]]]
    parent: Dict[Literal["type", "page_id"], Union[str, str]]
    archived: bool
    properties: NotionPageResponseProperties
    url: str
    public_url: Optional[str]
    # Error fields
    status: int
    code: Literal[
        "unauthorized",
        "forbidden",
        "object_not_found",
        "rate_limited",
        "invalid_request",
        "conflict",
        "internal_server_error",
    ]
    message: str
    request_id: str


# Search API types
class NotionSearchTextContent(TypedDict):
    content: str
    link: Optional[NotionLinkObject]


class NotionSearchTitleTextObject(TypedDict):
    type: Literal["text"]
    text: NotionSearchTextContent
    plain_text: str
    href: Optional[str]


class NotionSearchTitleProperty(TypedDict):
    id: str
    type: Literal["title"]
    title: List[NotionSearchTitleTextObject]


class NotionSearchPageProperties(TypedDict):
    title: NotionSearchTitleProperty


# Parent types for search results
class NotionPageParentRef(TypedDict):
    type: Literal["page_id"]
    page_id: str


class NotionDatabaseParentRef(TypedDict):
    type: Literal["database_id"]
    database_id: str


class NotionWorkspaceParentRef(TypedDict):
    type: Literal["workspace"]
    workspace: Literal[True]


NotionParent = Union[NotionPageParentRef, NotionDatabaseParentRef, NotionWorkspaceParentRef]


# Cover and icon types
class NotionExternalFile(TypedDict):
    type: Literal["external"]
    external: Dict[Literal["url"], str]


class NotionUploadedFile(TypedDict):
    type: Literal["file"]
    file: Dict[Literal["url", "expiry_time"], str]


class NotionEmojiIcon(TypedDict):
    type: Literal["emoji"]
    emoji: str


NotionCover = Union[NotionExternalFile, NotionUploadedFile]
NotionIcon = Union[NotionEmojiIcon, NotionExternalFile, NotionUploadedFile]


class NotionSearchUser(TypedDict):
    object: Literal["user"]
    id: str


class NotionSearchResultPage(TypedDict):
    object: Literal["page"]
    id: str
    created_time: str
    last_edited_time: str
    created_by: NotionSearchUser
    last_edited_by: NotionSearchUser
    cover: Optional[NotionCover]
    icon: Optional[NotionIcon]
    parent: NotionParent
    archived: bool
    properties: NotionSearchPageProperties
    url: str
    public_url: Optional[str]


class NotionSearchResponse(TypedDict):
    object: Literal["list"]
    results: List[NotionSearchResultPage]
    next_cursor: Optional[str]
    has_more: bool
    type: Literal["page_or_database"]
    page_or_database: Dict[str, str]


# Smart uploader types
class UploadStatusResult(TypedDict):
    status: Literal["cancelled", "skipped"]


UploadResult = Union[NotionAPIResponse, UploadStatusResult]

# Duplicate handling strategies
DuplicateStrategy = Literal["ask", "timestamp", "counter", "create_anyway", "skip"]
