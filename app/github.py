import hashlib
import hmac
from typing import Any


def verify_github_signature(secret: str, body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


def is_pull_request_event(event_name: str, payload: dict[str, Any]) -> bool:
    if event_name != "pull_request":
        return False

    action = payload.get("action")
    return action in {"opened", "synchronize", "reopened"}


def extract_pull_request_context(payload: dict[str, Any]) -> dict[str, Any]:
    pull_request = payload.get("pull_request", {})
    repository = payload.get("repository", {})

    return {
        "repository": repository.get("full_name"),
        "title": pull_request.get("title"),
        "body": pull_request.get("body"),
        "number": pull_request.get("number"),
        "author": pull_request.get("user", {}).get("login"),
        "base_branch": pull_request.get("base", {}).get("ref"),
        "head_branch": pull_request.get("head", {}).get("ref"),
        "changed_files": pull_request.get("changed_files"),
        "additions": pull_request.get("additions"),
        "deletions": pull_request.get("deletions"),
        "diff_url": pull_request.get("diff_url"),
        "html_url": pull_request.get("html_url"),
    }
