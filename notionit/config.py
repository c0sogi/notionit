from os import environ
from typing import Literal

DEFAULT_NOTION_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_API_VERSION = "2022-06-28"
DEFAULT_NOTION_PARSER_PLUGINS = "strikethrough,mark,insert,subscript,superscript,footnotes,table,task_lists,def_list,abbr,ruby,notionit.math_plugin.notion_math"


def get_config(
    key: Literal["notion_base_url", "notion_api_version", "notion_token", "notion_parent_page_id", "notion_parser_plugins"],
) -> str:
    if key == "notion_base_url":
        return environ.get("NOTION_BASE_URL", DEFAULT_NOTION_BASE_URL)
    elif key == "notion_api_version":
        return environ.get("NOTION_API_VERSION", DEFAULT_NOTION_API_VERSION)
    elif key == "notion_parent_page_id":
        if parent_page_id := environ.get("NOTION_PARENT_PAGE_ID"):
            return parent_page_id
        else:
            raise ValueError("NOTION_PARENT_PAGE_ID is not set")
    elif key == "notion_token":
        if token := environ.get("NOTION_TOKEN"):
            return token
        else:
            raise ValueError("NOTION_TOKEN is not set")
    elif key == "notion_parser_plugins":
        return environ.get("NOTION_PARSER_PLUGINS", DEFAULT_NOTION_PARSER_PLUGINS)
    else:
        raise ValueError(f"Invalid key: {key}")
