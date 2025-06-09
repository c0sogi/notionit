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
