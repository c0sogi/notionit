# NotionIt

![PyPI](https://img.shields.io/pypi/v/notionit?label=pypi%20package)
![PyPI - Downloads](https://img.shields.io/pypi/dm/notionit)

Markdown to Notion uploader powered by Mistune. It supports rich Markdown, math, tables, files, images, and duplicate-title handling.

## TLDR

```bash
pip install notionit
notionit
```

`notionit` shows the setup steps and checks whether the required Notion settings are visible.

```powershell
$env:NOTION_TOKEN="YOUR_NOTION_INTEGRATION_SECRET"
$env:NOTION_PARENT_PAGE_ID="YOUR_PAGE_ID"
notionit status
notionit upload path/to/file.md
```

You can also pass the required values directly.

```bash
notionit upload path/to/file.md --token YOUR_NOTION_TOKEN --parent-page-id YOUR_PAGE_ID
```

## What You Need

NotionIt needs a Notion integration secret and a parent page ID.

| Setting                 | Required | Default                         |
| ----------------------- | -------- | ------------------------------- |
| `NOTION_TOKEN`          | yes      |                                 |
| `NOTION_PARENT_PAGE_ID` | yes      |                                 |
| `NOTION_BASE_URL`       | no       | `https://api.notion.com/v1`     |
| `NOTION_API_VERSION`    | no       | `2026-03-11`                   |
| `NOTION_PARSER_PLUGINS` | no       | built-in Markdown plugin list   |

`notionit status` checks local environment variables only. It does not verify the token with Notion.

## CLI

```bash
notionit setup
notionit status
notionit upload notes.md
notionit upload notes.md --page-title "My Notes"
notionit upload notes.md --duplicate-strategy timestamp
notionit upload notes.md --debug
```

Useful aliases are also supported: `--parent` for `--parent-page-id`, `--title` for `--page-title`, and `--duplicate` for `--duplicate-strategy`.

Run `notionit upload --help` for all options.

## Python API

```python
from notionit import quick_upload

quick_upload(
    file_path="example.md",
    token="secret_abc123",
    parent_page_id="notion_page_id",
)
```

## Markdown Support

NotionIt supports common Mistune-powered Markdown features, including code blocks, tables, task lists, strikethrough, footnotes, inline and block math, file/image attachments, and invalid anchor-link skipping.

Default parser plugins are `strikethrough`, `mark`, `insert`, `subscript`, `superscript`, `footnotes`, `table`, `task_lists`, `def_list`, `abbr`, `ruby`, and `notionit.math_plugin.notion_math`.

Customize parser plugins with `--plugins` or `NOTION_PARSER_PLUGINS`.

## Development

```bash
uv run --group dev pytest
uv run --group dev pyright
uv run --group dev ruff check .
```

Live Notion API tests are skipped by default because they create a temporary page in your workspace and then move it to trash with `in_trash`.

```powershell
$env:NOTIONIT_LIVE_TEST="1"
$env:NOTION_TOKEN="YOUR_NOTION_INTEGRATION_SECRET"
$env:NOTION_PARENT_PAGE_ID="YOUR_PAGE_ID"
uv run --group dev pytest -m live
```

## License

MIT
