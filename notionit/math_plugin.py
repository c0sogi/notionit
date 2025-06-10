from typing import TYPE_CHECKING, Match
from mistune.plugins.math import (
    math as base_math,
    math_in_list as base_math_in_list,
    math_in_quote as base_math_in_quote,
    render_block_math,
    render_inline_math,
)

if TYPE_CHECKING:
    from mistune.block_parser import BlockParser
    from mistune.core import BlockState
    from mistune.markdown import Markdown

__all__ = ["notion_math"]

SINGLE_LINE_BLOCK_MATH_PATTERN = r"^ {0,3}\$\$(?P<math_text_single>[^\n]+?)\$\$[ \t]*$"

def parse_single_line_math(block: "BlockParser", m: Match[str], state: "BlockState") -> int:
    text = m.group("math_text_single")
    state.append_token({"type": "block_math", "raw": text})
    return m.end() + 1


def notion_math(md: "Markdown") -> None:
    """Enhanced math plugin supporting single-line block math and math in lists."""
    base_math(md)
    md.block.register(
        "block_math_single", SINGLE_LINE_BLOCK_MATH_PATTERN, parse_single_line_math, before="block_math"
    )
    base_math_in_list(md)
    md.block.insert_rule(md.block.list_rules, "block_math_single", before="block_math")
    base_math_in_quote(md)
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("block_math", render_block_math)
        md.renderer.register("inline_math", render_inline_math)
