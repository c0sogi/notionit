from typing import Callable, Optional, TypeVar, Union

from .types import NotionAPIResponse, UploadResult

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
    if callable(value):
        return value()  # pyright: ignore[reportReturnType]
    return value


def format_upload_success_message(upload_result: NotionAPIResponse) -> str:
    """
    Format a success message for an uploaded page.

    Args:
        id: The ID of the uploaded page

    Returns:
        A formatted success message
    """
    url: Optional[str]
    if "url" in upload_result:
        url = upload_result["url"]
    elif "public_url" in upload_result:
        url = upload_result["public_url"]
    else:
        url = None
    if url:
        return f"✅ Upload successful: {url}"
    else:
        return "✅ Upload successful"


def format_upload_error_message(upload_result: UploadResult) -> str:
    """
    Format an error message for an uploaded page.
    """
    status = upload_result.get("status")
    if status is None:
        status = "unknown error"

    if status == "skipped":
        return f"⚠️ Upload skipped: {status}"
    else:
        return f"❌ Upload failed: {status}"
