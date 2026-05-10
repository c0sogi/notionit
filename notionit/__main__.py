from enum import Enum
from os import environ
from pathlib import Path
from typing import List, NoReturn, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from typing_extensions import Annotated

from . import DuplicateStrategy, is_success_result, quick_upload
from ._utils import format_upload_error_message, format_upload_success_message
from .config import (
    DEFAULT_NOTION_API_VERSION,
    DEFAULT_NOTION_BASE_URL,
    DEFAULT_NOTION_PARSER_PLUGINS,
)

console = Console()


class DuplicateOption(str, Enum):
    ask = "ask"
    timestamp = "timestamp"
    counter = "counter"
    create_anyway = "create_anyway"
    skip = "skip"


class RendererOption(str, Enum):
    ast = "ast"
    html = "html"


MarkdownPathsArgument = Annotated[
    List[Path],
    typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=False,
        help="Markdown file path. Pass multiple files to upload them in order.",
    ),
]
TokenOption = Annotated[
    Optional[str],
    typer.Option(
        "--token",
        envvar="NOTION_TOKEN",
        help="Notion integration secret. Can also be set with NOTION_TOKEN.",
    ),
]
ParentPageOption = Annotated[
    Optional[str],
    typer.Option(
        "--parent-page-id",
        "--parent",
        envvar="NOTION_PARENT_PAGE_ID",
        help="Target Notion parent page ID. Can also be set with NOTION_PARENT_PAGE_ID.",
    ),
]
BaseUrlOption = Annotated[
    str,
    typer.Option(
        "--base-url",
        envvar="NOTION_BASE_URL",
        help="Notion API base URL.",
    ),
]
ApiVersionOption = Annotated[
    str,
    typer.Option(
        "--api-version",
        "--version",
        envvar="NOTION_API_VERSION",
        help="Notion API version header.",
    ),
]
PluginsOption = Annotated[
    str,
    typer.Option(
        "--plugins",
        envvar="NOTION_PARSER_PLUGINS",
        help="Comma-separated Mistune plugin list.",
    ),
]
PageTitleOption = Annotated[
    Optional[str],
    typer.Option(
        "--page-title",
        "--title",
        help="Notion page title. Defaults to the Markdown file name.",
    ),
]
DuplicateStrategyOption = Annotated[
    Optional[DuplicateOption],
    typer.Option(
        "--duplicate-strategy",
        "--duplicate",
        help="How to handle same-title pages in the target parent page.",
    ),
]
DelayOption = Annotated[
    float,
    typer.Option(
        "--delay",
        min=0.0,
        help="Delay between uploads in seconds when uploading multiple files.",
    ),
]
RendererCliOption = Annotated[
    RendererOption,
    typer.Option(
        "--renderer",
        help="Mistune renderer method.",
    ),
]
NoEscapeOption = Annotated[
    bool,
    typer.Option(
        "--no-escape",
        "--noescape",
        help="Disable escaping HTML tags.",
    ),
]
HardWrapOption = Annotated[
    bool,
    typer.Option(
        "--hard-wrap",
        "--hardwrap",
        help="Enable Mistune hard wrapping.",
    ),
]

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Upload Markdown files to Notion.",
    no_args_is_help=False,
)


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _clean_required(value: str, default: str) -> str:
    value = value.strip()
    if value:
        return value
    return default


def _parse_plugins(value: str) -> List[str]:
    plugins = [plugin.strip() for plugin in value.split(",") if plugin.strip()]
    if plugins:
        return plugins
    return [
        plugin.strip()
        for plugin in DEFAULT_NOTION_PARSER_PLUGINS.split(",")
        if plugin.strip()
    ]


def _env_status(name: str, *, required: bool, default: Optional[str] = None) -> str:
    value = environ.get(name)
    if value:
        return "set"
    if default is not None:
        return f"default: {default}"
    if required:
        return "missing"
    return "not set"


def _print_config_status() -> bool:
    token_is_set = bool(environ.get("NOTION_TOKEN"))
    parent_is_set = bool(environ.get("NOTION_PARENT_PAGE_ID"))
    ready = token_is_set and parent_is_set

    table = Table(title="Current NotionIt configuration")
    table.add_column("Setting")
    table.add_column("Status")
    table.add_column("Purpose")
    table.add_row(
        "NOTION_TOKEN",
        _env_status("NOTION_TOKEN", required=True),
        "Required. Notion integration secret.",
    )
    table.add_row(
        "NOTION_PARENT_PAGE_ID",
        _env_status("NOTION_PARENT_PAGE_ID", required=True),
        "Required. Destination page ID.",
    )
    table.add_row(
        "NOTION_BASE_URL",
        _env_status("NOTION_BASE_URL", required=False, default=DEFAULT_NOTION_BASE_URL),
        "Optional. Notion API endpoint.",
    )
    table.add_row(
        "NOTION_API_VERSION",
        _env_status(
            "NOTION_API_VERSION", required=False, default=DEFAULT_NOTION_API_VERSION
        ),
        "Optional. Notion API version.",
    )
    table.add_row(
        "NOTION_PARSER_PLUGINS",
        _env_status(
            "NOTION_PARSER_PLUGINS", required=False, default="built-in defaults"
        ),
        "Optional. Markdown parser plugins.",
    )
    console.print(table)

    if ready:
        console.print("Ready to upload. Try: notionit upload notes.md")
    else:
        console.print(
            "Not ready yet. Run notionit setup for the setup steps, or pass --token and --parent-page-id to upload."
        )
    return ready


def _print_setup_guide() -> None:
    console.print(
        Panel.fit(
            "NotionIt uploads local Markdown files into a Notion page. Before the first upload, you need a Notion integration secret and the destination parent page ID.",
            title="NotionIt setup",
        )
    )
    console.print(
        "1. Create a Notion integration in your Notion workspace and copy its internal integration secret."
    )
    console.print(
        "2. Open the Notion page that should receive uploads, then share that page with the integration."
    )
    console.print("3. Copy the destination page ID from the Notion page URL.")
    console.print("4. Set the values for the current PowerShell session:")
    console.print('   $env:NOTION_TOKEN="your_notion_integration_secret"')
    console.print('   $env:NOTION_PARENT_PAGE_ID="your_parent_page_id"')
    console.print("5. Check the local setup with: notionit status")
    console.print("6. Upload a file with: notionit upload notes.md")
    console.print(
        "You can also skip environment variables and pass --token and --parent-page-id directly to notionit upload."
    )


def _missing_upload_settings(
    token: Optional[str], parent_page_id: Optional[str]
) -> List[str]:
    missing: List[str] = []
    if token is None:
        missing.append("NOTION_TOKEN")
    if parent_page_id is None:
        missing.append("NOTION_PARENT_PAGE_ID")
    return missing


def _exit_missing_upload_settings(missing: List[str]) -> NoReturn:
    console.print(
        Panel.fit(
            "Upload needs a Notion integration secret and a destination parent page ID before it can call the Notion API.",
            title="Missing upload settings",
        )
    )
    if "NOTION_TOKEN" in missing:
        console.print("NOTION_TOKEN is missing. Set it with PowerShell like:")
        console.print('   $env:NOTION_TOKEN="your_notion_integration_secret"')
        console.print("Or pass it once with: --token your_notion_integration_secret")
    if "NOTION_PARENT_PAGE_ID" in missing:
        console.print(
            "NOTION_PARENT_PAGE_ID is missing. Share the target Notion page with your integration, then set:"
        )
        console.print('   $env:NOTION_PARENT_PAGE_ID="your_parent_page_id"')
        console.print("Or pass it once with: --parent-page-id your_parent_page_id")
    console.print(
        "After setting them, run notionit status to confirm the CLI can see them."
    )
    raise typer.Exit(code=2)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _print_setup_guide()
        console.print()
        _print_config_status()


@app.command()
def setup() -> None:
    """Show first-time setup steps."""
    _print_setup_guide()
    console.print()
    _print_config_status()


@app.command()
def status() -> None:
    """Check whether required local configuration is visible to the CLI."""
    ready = _print_config_status()
    console.print(
        "This command checks local environment variables only. It does not verify the token with Notion."
    )
    if not ready:
        raise typer.Exit(code=1)


@app.command()
def upload(
    path_to_markdown: MarkdownPathsArgument,
    token: TokenOption = None,
    parent_page_id: ParentPageOption = None,
    base_url: BaseUrlOption = DEFAULT_NOTION_BASE_URL,
    api_version: ApiVersionOption = DEFAULT_NOTION_API_VERSION,
    plugins: PluginsOption = DEFAULT_NOTION_PARSER_PLUGINS,
    page_title: PageTitleOption = None,
    duplicate_strategy: DuplicateStrategyOption = None,
    delay: DelayOption = 1.0,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Print Notion API request and response details."),
    ] = False,
    renderer: RendererCliOption = RendererOption.ast,
    no_escape: NoEscapeOption = False,
    hard_wrap: HardWrapOption = False,
) -> None:
    """Upload one or more Markdown files to Notion."""
    token = _clean_optional(token)
    parent_page_id = _clean_optional(parent_page_id)
    missing = _missing_upload_settings(token, parent_page_id)
    if missing:
        _exit_missing_upload_settings(missing)
    assert token is not None
    assert parent_page_id is not None

    duplicate: Optional[DuplicateStrategy]
    if duplicate_strategy is None:
        duplicate = None
    else:
        duplicate = duplicate_strategy.value

    renderer_value = renderer.value
    markdown_paths = [str(path) for path in path_to_markdown]
    plugin_list = _parse_plugins(plugins)
    cleaned_page_title = _clean_optional(page_title)
    cleaned_base_url = _clean_required(base_url, DEFAULT_NOTION_BASE_URL)
    cleaned_api_version = _clean_required(api_version, DEFAULT_NOTION_API_VERSION)

    console.print(f"Uploading {len(markdown_paths)} Markdown file(s) to Notion.")
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
            file_path=markdown_paths,
            token=token,
            parent_page_id=parent_page_id,
            base_url=cleaned_base_url,
            notion_version=cleaned_api_version,
            plugins=plugin_list,
            page_title=cleaned_page_title,
            duplicate_strategy=duplicate,
            debug=debug,
            renderer=renderer_value,
            escape=not no_escape,
            hard_wrap=hard_wrap,
            delay_seconds=delay,
            progress=update,
        )

    for i, response in enumerate(responses, start=1):
        if is_success_result(response):
            msg = format_upload_success_message(response)
        else:
            msg = format_upload_error_message(response)
        console.print(f"📁 {i}/{len(responses)}: {msg}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
