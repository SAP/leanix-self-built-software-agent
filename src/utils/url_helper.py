import re
from typing import Tuple
from urllib.parse import urlparse


def extract_url(md_link: str) -> str:
    """
    Converts `[text](https://foo.bar)` → `https://foo.bar`
    """
    m = re.search(r"\((https?://[^)]+)\)", md_link)
    return m.group(1) if m else md_link        # fall back: return unchanged


def parse_github_url_to_repo_full_name(repo_url: str) -> Tuple[str, str]:
    """
    Extract ``(<owner>, <repo>)`` from a GitHub URL.

    >>> parse_github_url_to_repo_full_name("https://github.com/foo/bar.git")
    ('foo', 'bar')
    """
    parsed = urlparse(repo_url.strip())

    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("URL must point to github.com")

    # Path is '/owner/repo' or '/owner/repo.git'
    parts = parsed.path.lstrip("/").split("/", 2)
    if len(parts) < 2:
        raise ValueError("URL path must be /<owner>/<repo>")

    owner, repo = parts[0], parts[1].removesuffix(".git")
    return owner, repo