def safe_url_join(base: str, *paths: str) -> str:
    """
    슬래시 유무에 상관없이 안전하게 URL을 결합하는 함수

    Args:
        base: 기본 URL
        *paths: 결합할 경로들

    Returns:
        올바르게 결합된 URL
    """
    url = base.rstrip("/")
    for path in paths:
        path = path.strip("/")
        if path:  # 빈 문자열이 아닌 경우만
            url = f"{url}/{path}"
    return url
