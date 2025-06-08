from typing import Literal, Optional

from spargear import ArgumentSpec, BaseArguments

from . import DuplicateStrategy, get_config, quick_upload

BASE_URL = get_config("notion_base_url")
NOTION_VERSION = get_config("notion_api_version")
PARSER_PLUGINS = get_config("notion_parser_plugins")


class Arguments(BaseArguments):
    file_path: ArgumentSpec[str] = ArgumentSpec(
        ["file_path"],
        help="Path to the markdown file to upload.",
        required=True,
    )
    """Path to the markdown file to upload."""
    token: Optional[str] = None
    """Notion API token."""
    parent_page_id: Optional[str] = None
    """Notion parent page ID."""
    base_url: str = BASE_URL
    """Notion API base URL."""
    notion_version: str = NOTION_VERSION
    """Notion API version."""
    plugins: str = PARSER_PLUGINS
    """Markdown parser plugins."""
    page_title: Optional[str] = None
    """Notion page title. If not set, the file name will be used."""
    duplicate_strategy: Optional[DuplicateStrategy] = None
    """Strategy to handle duplicate pages (same title in the same parent page)."""
    debug: bool = False
    """Debug mode. Prints the Notion API request and response."""
    renderer: Literal["html", "ast"] = "ast"
    """Mistune: Markdown renderer method."""
    escape: bool = True
    """Mistune: Escape HTML tags."""
    hard_wrap: bool = False
    """Mistune: Hard wrap."""

    def run(self) -> None:
        print("Uploading...")
        response = quick_upload(
            file_path=self.file_path.unwrap(),
            token=self.token or get_config("notion_token"),
            parent_page_id=self.parent_page_id or get_config("notion_parent_page_id"),
            base_url=self.base_url or BASE_URL,
            notion_version=self.notion_version or NOTION_VERSION,
            plugins=self.plugins.split(",") if self.plugins else PARSER_PLUGINS.split(","),
            page_title=self.page_title,
            duplicate_strategy=self.duplicate_strategy,
            debug=self.debug,
            renderer=self.renderer,
            escape=self.escape,
            hard_wrap=self.hard_wrap,
        )
        print("Upload response:", response)


def main():
    Arguments().run()


if __name__ == "__main__":
    main()
