from typing import List, Literal, Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from spargear import ArgumentSpec, BaseArguments, SubcommandSpec

from . import DuplicateStrategy, get_config, is_success_result, quick_upload
from ._utils import format_upload_error_message, format_upload_success_message

BASE_URL = get_config("notion_base_url")
NOTION_VERSION = get_config("notion_api_version")
PARSER_PLUGINS = get_config("notion_parser_plugins")


class UploadArguments(BaseArguments):
    path_to_markdown: ArgumentSpec[List[str]] = ArgumentSpec(
        ["path_to_markdown"],
        help="Path to the markdown file to upload.",
        required=True,
        nargs="+",
    )
    """Path to the markdown file to upload."""
    token: Optional[str] = None
    """Notion API token."""
    parent: Optional[str] = None
    """Notion parent page ID."""
    base_url: str = BASE_URL
    """Notion API base URL."""
    version: str = NOTION_VERSION
    """Notion API version."""
    plugins: str = PARSER_PLUGINS
    """Markdown parser plugins."""
    title: Optional[str] = None
    """Notion page title. If not set, the file name will be used."""
    duplicate: Optional[DuplicateStrategy] = None
    """Strategy to handle duplicate pages (same title in the same parent page)."""
    delay: float = 1.0
    """Delay between uploads in seconds. Used only if uploading multiple files."""
    debug: bool = False
    """Debug mode. Prints the Notion API request and response."""
    renderer: Literal["html", "ast"] = "ast"
    """Mistune: Markdown renderer method."""
    noescape: bool = False
    """Mistune: Disable escaping HTML tags."""
    hardwrap: bool = False
    """Mistune: Hard wrap."""

    def run(self) -> None:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("Uploading", total=100)

            def update(pct: float) -> None:
                progress.update(task, completed=pct * 100)

            responses = quick_upload(
                file_path=self.path_to_markdown.unwrap(),
                token=self.token or get_config("notion_token"),
                parent_page_id=self.parent or get_config("notion_parent_page_id"),
                base_url=self.base_url or BASE_URL,
                notion_version=self.version or NOTION_VERSION,
                plugins=self.plugins.split(",") if self.plugins else PARSER_PLUGINS.split(","),
                page_title=self.title,
                duplicate_strategy=self.duplicate,
                debug=self.debug,
                renderer=self.renderer,
                escape=not self.noescape,
                hard_wrap=self.hardwrap,
                delay_seconds=self.delay,
                progress=update,
            )

        for i, response in enumerate(responses, start=1):
            if is_success_result(response):
                msg = format_upload_success_message(response)
            else:
                msg = format_upload_error_message(response)
            print(f"📁 {i}/{len(responses)}: {msg}")


class NotionItCLI(BaseArguments):
    """CLI for NotionIt."""

    upload: SubcommandSpec[UploadArguments] = SubcommandSpec(
        name="upload",
        argument_class=UploadArguments,
        help="Upload a markdown file to Notion.",
        description="Upload a markdown file to Notion using the Notion API.",
    )


def main():
    cli = NotionItCLI()
    subcommand = cli.last_subcommand
    if isinstance(subcommand, UploadArguments):
        subcommand.run()
    else:
        cli.get_parser().print_help()
        return


if __name__ == "__main__":
    main()
