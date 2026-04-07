import json
import os
import re
import textwrap
import uuid
from pathlib import Path
from typing import Any

from openai import OpenAI

TASKS_FILE = Path(__file__).parent / "tasks" / "pr_review_tasks.json"


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("No OpenAI API key found. Set OPENAI_API_KEY, GROQ_API_KEY, or API_KEY.")
    base_url = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
    return OpenAI(base_url=base_url, api_key=api_key)


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Generated task text does not contain a valid JSON object.")
    return text[start : end + 1]


def _normalize_task_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"ai-{slug[:40]}-{uuid.uuid4().hex[:8]}"


def generate_synthetic_task() -> dict[str, Any]:
    client = _get_openai_client()

    prompt = textwrap.dedent(
        """
        Generate a synthetic GitHub pull request review task for a code review benchmark.
        Output only valid JSON with the following keys:
        - task_id
        - repository
        - pr_number
        - title
        - description
        - changed_files
        - diff
        - expected_verdict
        - required_findings
        - nice_to_have_findings
        - merge_blockers

        The diff should be realistic and short. Use Python, JavaScript, or documentation changes.
        Use one of APPROVE, REQUEST_CHANGES, COMMENT for expected_verdict.
        Ensure changed_files is a JSON array of file paths.
        Keep text values concise and natural.
        """
    ).strip()

    response = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4"),
        messages=[
            {"role": "system", "content": "You are a task generator for an AI code review benchmark."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=600,
    )

    raw = response.choices[0].message.content or ""
    try:
        payload = json.loads(_extract_json(raw))
    except ValueError as exc:
        raise ValueError(f"Could not parse generated task JSON: {exc}\nRaw output:\n{raw}")

    if "task_id" not in payload or not payload["task_id"]:
        payload["task_id"] = _normalize_task_id(payload.get("title", "ai-task"))

    if payload.get("expected_verdict") not in {"APPROVE", "REQUEST_CHANGES", "COMMENT"}:
        payload["expected_verdict"] = "COMMENT"

    payload.setdefault("required_findings", [])
    payload.setdefault("nice_to_have_findings", [])
    payload.setdefault("merge_blockers", [])

    return payload


def save_synthetic_task(task: dict[str, Any]) -> dict[str, Any]:
    raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    tasks = raw.get("tasks", [])
    tasks.append(task)
    raw["tasks"] = tasks
    TASKS_FILE.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return task


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic PR review tasks.")
    parser.add_argument("--count", type=int, default=1, help="Number of tasks to generate")
    args = parser.parse_args()

    for _ in range(args.count):
        task = generate_synthetic_task()
        save_synthetic_task(task)
        print(f"Generated task: {task['task_id']}")
