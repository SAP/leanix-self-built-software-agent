import base64
import os
from typing import List, TypedDict, Set, Dict, Optional

from github import Github, GithubException, ContentFile
from langchain_core.tools import tool

from src.logging.logging import get_logger
from src.utils.url_helper import parse_github_url_to_repo_full_name

logger = get_logger(__name__)

# ---- Types -------------------------------------------------------------------

class HeadSHAResult(TypedDict):
    sha: str
    default_branch: str

class TreeEntry(TypedDict):
    path: str
    type: str  # "blob" | "tree"
    size: Optional[int]

class TreeResult(TypedDict):
    entries: List[TreeEntry]

class ReadFileResult(TypedDict):
    content: str        # base64 or text
    encoding: str       # "base64" | "text"
    truncated: bool
    size: int

class SearchMatch(TypedDict):
    path: str

class SearchCodeResult(TypedDict):
    matches: List[SearchMatch]

class Service(TypedDict):
    name: str
    path: str  # relative repo path, no leading slash

# ---- Constants ---------------------------------------------------------------

BUILD_MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "pom.xml",
    "go.mod", "Cargo.toml", "build.gradle", "build.gradle.kts",
    "requirements.txt",
}
DOCKERFILE_NAMES = {"Dockerfile", "dockerfile"}

# ---- Simple in-memory context so subsequent calls don't need the repo URL ----

_CURRENT: Dict[str, str] = {
    "repo_full_name": "",
    "head_sha": "",
}

def _gh_client() -> Github:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN (or GH_TOKEN) not set.")
    return Github(token)

def _ensure_repo() -> "Repository.Repository":
    if not _CURRENT["repo_full_name"]:
        raise RuntimeError("Repository context missing. Call repo.get_head_sha first.")
    gh = _gh_client()
    return gh.get_repo(_CURRENT["repo_full_name"])

# ---- Tools -------------------------------------------------------------------

@tool("repo.get_head_sha")
def repo_get_head_sha(repo_root_url: str) -> HeadSHAResult | Dict[str, str]:
    """
    Resolve default branch and HEAD commit SHA for a GitHub repo URL.
    Sets a global repo context so subsequent calls don't need the URL.
    """
    try:
        owner, repo_name = parse_github_url_to_repo_full_name(repo_root_url)
        repo_full_name = f"{owner}/{repo_name}"
    except Exception as err:
        return {"error": "invalid_url", "message": str(err)}

    try:
        gh = _gh_client()
    except Exception as err:
        return {"error": "tooling_missing", "message": str(err)}

    try:
        repo = gh.get_repo(repo_full_name)
        default_branch = repo.default_branch
        sha = repo.get_branch(default_branch).commit.sha
        _CURRENT["repo_full_name"] = repo_full_name
        _CURRENT["head_sha"] = sha
        logger.info("repo=%s default_branch=%s sha=%s", repo_full_name, default_branch, sha)
        return {"sha": sha, "default_branch": default_branch}
    except GithubException as exc:
        return {"error": "github_error", "message": f"{exc.status} {exc.data}"}
    except Exception as exc:
        return {"error": "unknown_error", "message": str(exc)}

@tool("repo.list_tree")
def repo_list_tree(sha: str, recursive: bool = True) -> TreeResult | Dict[str, str]:
    """
    List directory entries (files/dirs) for the tree at a given commit SHA.
    Requires repo.get_head_sha to have been called first to set context.
    """
    try:
        repo = _ensure_repo()
        # Resolve commit->tree to be explicit
        commit = repo.get_commit(sha)
        tree_sha = commit.commit.tree.sha
        tree = repo.get_git_tree(tree_sha, recursive=recursive).tree
        entries: List[TreeEntry] = []
        for e in tree:
            # e.type is "blob" or "tree"
            entries.append({"path": e.path, "type": e.type, "size": getattr(e, "size", None)})
        return {"entries": entries}
    except GithubException as exc:
        return {"error": "github_error", "message": f"{exc.status} {exc.data}"}
    except Exception as exc:
        return {"error": "unknown_error", "message": str(exc)}

@tool("repo.read_file")
def repo_read_file(path: str, sha: str, max_bytes: int = 200_000) -> ReadFileResult | Dict[str, str]:
    """
    Read a single file at a specific ref (commit SHA).
    Returns base64 content by default; truncates if larger than max_bytes.
    """
    try:
        repo = _ensure_repo()
        cf: ContentFile.ContentFile = repo.get_contents(path, ref=sha)
        size = getattr(cf, "size", None) or 0

        # Always return base64 to avoid encoding issues
        # cf.content is base64 (when encoding == "base64") — we may need to truncate by bytes.
        if cf.encoding == "base64" and isinstance(cf.content, str):
            raw_bytes = base64.b64decode(cf.content.encode("utf-8"))
            truncated = len(raw_bytes) > max_bytes
            if truncated:
                raw_bytes = raw_bytes[:max_bytes]
            content_b64 = base64.b64encode(raw_bytes).decode("utf-8")
            return {
                "content": content_b64,
                "encoding": "base64",
                "truncated": truncated,
                "size": size,
            }
        else:
            # Fallback: treat as text and truncate by characters
            text = cf.decoded_content.decode("utf-8", errors="replace")
            truncated = len(text.encode("utf-8")) > max_bytes
            if truncated:
                # truncate by bytes, then decode safely again
                b = text.encode("utf-8")[:max_bytes]
                text = b.decode("utf-8", errors="replace")
            return {
                "content": text,
                "encoding": "text",
                "truncated": truncated,
                "size": size,
            }
    except GithubException as exc:
        return {"error": "github_error", "message": f"{exc.status} {exc.data}"}
    except Exception as exc:
        return {"error": "unknown_error", "message": str(exc)}

@tool("repo.search_code")
def repo_search_code(query: str, limit: int = 50) -> SearchCodeResult | Dict[str, str]:
    """
    GitHub code search scoped to the current repo context.
    Example query fragments: '@SpringBootApplication', 'serverless.yml', 'Program.cs path:/cmd/'
    """
    try:
        repo_full_name = _CURRENT.get("repo_full_name")
        if not repo_full_name:
            raise RuntimeError("Repository context missing. Call repo.get_head_sha first.")
        gh = _gh_client()
        # Force repo scoping
        q = f"{query} repo:{repo_full_name}"
        results = gh.search_code(q)
        matches: List[SearchMatch] = []
        for i, item in enumerate(results):
            if i >= limit:
                break
            # Guard against cross-repo hits if GitHub returns extras
            if getattr(item.repository, "full_name", None) == repo_full_name:
                matches.append({"path": item.path})
        return {"matches": matches}
    except GithubException as exc:
        return {"error": "github_error", "message": f"{exc.status} {exc.data}"}
    except Exception as exc:
        return {"error": "unknown_error", "message": str(exc)}

# Your simple heuristic discoverer. API-only, no cloning.
@tool("discover_services")
def discover_services_tool(repo_root_url: str) -> List[Service]:
    """
    Identify services by scanning the git tree for folders that contain BOTH:
    - a build manifest (e.g., package.json, pom.xml, etc.), AND
    - a Dockerfile
    Returns a list of {name, path} with repo-relative paths (no leading slash).
    """
    try:
        owner, repo_name = parse_github_url_to_repo_full_name(repo_root_url)
        repo_full_name = f"{owner}/{repo_name}"
    except ValueError as err:
        return [{"name": "error", "path": str(err)}]

    logger.info("↪️  discover_services_tool(%s)", repo_full_name)

    # Prime context (so downstream repo.* tools can be used immediately if desired)
    try:
        gh = _gh_client()
        repo = gh.get_repo(repo_full_name)
    except Exception as exc:
        return [{"name": "error", "path": f"Auth/Repo error: {exc}"}]

    try:
        default_branch = repo.default_branch
        tree = repo.get_git_tree(default_branch, recursive=True).tree
    except GithubException as exc:
        return [{"name": "error", "path": f"Error fetching git tree: {exc}"}]

    # folder -> set(file_basename)
    folders: Dict[str, Set[str]] = {}

    for entry in tree:
        if entry.type != "blob":
            continue
        folder_path = "/".join(entry.path.split("/")[:-1])  # '' for root
        base = entry.path.rsplit("/", 1)[-1]
        folders.setdefault(folder_path, set()).add(base)

    services: List[Service] = []

    for folder, files in folders.items():
        has_manifest = any(f in BUILD_MANIFESTS for f in files)
        has_docker = any(f in DOCKERFILE_NAMES for f in files)
        if has_manifest and has_docker:
            # Name: last segment of folder, or repo name if root
            service_name = folder.split("/")[-1] if folder else repo_name
            # Path: repo-relative, no leading slash; use '' for root
            service_path = folder  # '' means repo root
            services.append({"name": service_name, "path": service_path})

    logger.info("📦 found services=%s", services)
    # Update global context to this repo for subsequent calls
    try:
        _CURRENT["repo_full_name"] = repo_full_name
        _CURRENT["head_sha"] = repo.get_branch(repo.default_branch).commit.sha
    except Exception:
        pass
    return services
