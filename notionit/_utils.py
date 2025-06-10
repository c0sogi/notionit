from typing import Callable, TypeVar, Union

from .config import get_config
from .types import StrOrCallable

T = TypeVar("T")


def safe_url_join(base: str, *paths: str) -> str:
    """
    Safely join URL parts regardless of trailing slashes.

    Args:
        base: Base URL
        *paths: Additional path segments to join

    Returns:
        Properly joined URL
    """
    url = base.rstrip("/")
    for path in paths:
        path = path.strip("/")
        if path:  # skip empty segments
            url = f"{url}/{path}"
    return url


def unwrap_callable(value: Union[T, Callable[[], T]]) -> T:
    """
    Unwrap a callable if the value is callable, otherwise return the value.

    Args:
        value: A value that may be a callable

    Returns:
        The result of calling the callable or the value itself
    """
    if isinstance(value, Callable):
        return value()
    return value


def format_upload_success_message(
    id: str, notion_app_base_url: StrOrCallable = get_config("notion_app_base_url")
) -> str:
    """
    Format a success message for an uploaded page.

    Args:
        id: The ID of the uploaded page

    Returns:
        A formatted success message
    """
    return f"✅ Upload successful: {safe_url_join(unwrap_callable(notion_app_base_url), id.replace('-', ''))}"
