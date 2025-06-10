# NotionIt

![PyPI](https://img.shields.io/pypi/v/notionit?label=pypi%20package)
![PyPI - Downloads](https://img.shields.io/pypi/dm/notionit)

**Markdown to Notion uploader** with full-featured support powered by Mistune.

> Upload rich, formatted Markdown files—including equations, code, tables, and attachments—directly to Notion with ease.

---

## ✨ Features

* ✅ **Full Markdown Support** via [Mistune](https://mistune.readthedocs.io/)
* 📤 **Upload to Notion** using official API
* 📎 **File & Image Attachment Support**
* 🔗 **Skips invalid links like anchors**
* 📐 **LaTeX Math Block Rendering**
* 🧩 **Plugin-based Parsing** (supports strikethrough, footnotes, task lists, etc.)
* 📄 **Table-to-Block Conversion**
* 🧠 **Smart Title Conflict Handling** (`timestamp`, `counter`, `ask`, `skip`)
* 🛠️ **Debug Mode for Development**

---

## 🚀 Quick Start

```bash
pip install notionit
```

Then run:

```bash
notionit upload path/to/file.md --token YOUR_NOTION_TOKEN --parent-page-id YOUR_PAGE_ID
```

You'll see an animated progress bar showing upload percentage and remaining time.

Or use the convenience function in Python:

```python
from notionit import quick_upload

quick_upload(
    file_path="example.md",
    token="secret_abc123",
    parent_page_id="notion_page_id",
)
```

---

## 🧩 Plugin Support

Default enabled plugins:

* `strikethrough`
* `mark`
* `insert`
* `subscript`
* `superscript`
* `footnotes`
* `table`
* `task_lists`
* `def_list`
* `abbr`
* `ruby`
* `math` (via `notionit.math_plugin.notion_math` for single-line $$ and list support)

Customize them via `--plugins` or programmatically.

---

## 🛡️ Environment Variables

Optionally configure via environment variables:

| Variable                | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `NOTION_TOKEN`          | Notion integration token                        |
| `NOTION_PARENT_PAGE_ID` | Parent page ID                                  |
| `NOTION_BASE_URL`       | API base (default: `https://api.notion.com/v1`) |
| `NOTION_API_VERSION`    | API version (default: `2022-06-28`)             |
| `NOTION_PARSER_PLUGINS` | Comma-separated plugin list                     |

---

## 📦 CLI Options

Run `notionit --help` for full options:

```bash
notionit upload example.md \
  --page-title "My Notes" \
  --duplicate-strategy timestamp \
  --debug
```

During uploads, the CLI reports progress with a spinner and estimated remaining time.

---

## 🧠 Use Case Ideas

* Publish lecture notes with math equations
* Upload tech blogs with code snippets
* Back up documentation in Notion
* Convert Markdown meeting notes into Notion pages

---

## 📃 License

MIT
