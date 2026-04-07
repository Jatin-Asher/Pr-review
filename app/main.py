import os
from fastapi import FastAPI, Header, HTTPException, Request

from .ai import review_pull_request
from .github import (
    extract_pull_request_context,
    is_pull_request_event,
    verify_github_signature,
)


app = FastAPI(title="AI PR Reviewer", version="0.1.0")


@app.get("/")
async def root() -> dict:
    return {"message": "AI PR Reviewer is running"}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if secret and not verify_github_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")

    payload = await request.json()

    if not is_pull_request_event(x_github_event, payload):
        return {"status": "ignored", "reason": "Not a pull request event"}

    pr_context = extract_pull_request_context(payload)
    review = review_pull_request(pr_context)

    return {"status": "reviewed", "review": review}