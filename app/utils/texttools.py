import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

url_regex = re.compile(
    r"^(https?|ftp):\/\/"  # http:// or https:// or ftp://
    r"(?"
    r":(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
    r"localhost|"  # or localhost...
    # r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # or IPv4...
    # r"\[?[A-F0-9]*:[A-F0-9:]+\]?"  # or IPv6...
    r")"
    r"(?::\d+)?"  # optional port
    r"(?:\/[-A-Z0-9+&@#\/%=~_|$]*)*$",
    re.IGNORECASE,
)


def is_valid_url(url: str) -> bool:
    # Check if the URL matches the regex
    if re.match(url_regex, url) is None:
        return False

    # Additional check using urllib.parse to ensure proper scheme and netloc
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


def add_query_params(url: str, new_params: dict) -> str:
    parsed = urlparse(url)
    existing_params = parse_qs(parsed.query)
    flat_params = {k: v[0] for k, v in existing_params.items()}
    flat_params.update(new_params)
    query = urlencode(flat_params)
    new_url = urlunparse(parsed._replace(query=query))
    return new_url
