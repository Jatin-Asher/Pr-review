import os
from pathlib import Path
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def build_review_prompt(pr_context: dict[str, Any]) -> str:
    return f"""
You are a senior software engineer reviewing a GitHub pull request.

Repository: {pr_context.get("repository")}
PR Number: {pr_context.get("number")}
Title: {pr_context.get("title")}
Author: {pr_context.get("author")}
Base Branch: {pr_context.get("base_branch")}
Head Branch: {pr_context.get("head_branch")}
Changed Files: {pr_context.get("changed_files")}
Additions: {pr_context.get("additions")}
Deletions: {pr_context.get("deletions")}
Description:
{pr_context.get("body")}

Review the PR and respond with:
1. Summary
2. Risks
3. Test gaps
4. Merge recommendation: APPROVE / CHANGES_REQUESTED
5. Short reviewer comment
""".strip()


def review_pull_request(pr_context: dict[str, Any]) -> dict[str, Any]:
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    prompt = build_review_prompt(pr_context)

    if provider == "mock":
        return {
            "provider": "mock",
            "prompt_preview": prompt[:300],
            "summary": "Starter review only. No real LLM call is connected yet.",
            "risks": [
                "Diff content is not fetched yet.",
                "Automated tests and static analysis are not integrated yet.",
            ],
            "test_gaps": ["No repository-aware validation has been performed yet."],
            "merge_recommendation": "CHANGES_REQUESTED",
            "reviewer_comment": (
                "This is a scaffold. Connect GitHub diff fetching and an LLM before using it for real merge decisions."
            ),
        }

    if provider in {"openai", "groq"}:
        client = OpenAI(
            base_url=os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=(
                os.getenv("GROQ_API_KEY")
                or os.getenv("HF_TOKEN")
                or os.getenv("OPENAI_API_KEY")
                or os.getenv("API_KEY")
            ),
        )
        model = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict pull request reviewer. Return a concise structured review with "
                        "summary, risks, test gaps, merge recommendation, and reviewer comment."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            stream=False,
        )
        content = (completion.choices[0].message.content or "").strip()
        return {
            "provider": provider,
            "model": model,
            "raw_review": content,
            "merge_recommendation": "COMMENT",
        }

    raise NotImplementedError("Unsupported AI_PROVIDER. Use mock, openai, or groq.")
