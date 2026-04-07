import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel


TASKS_FILE = Path(__file__).parent / "tasks" / "pr_review_tasks.json"
DEFAULT_MAX_STEPS = 4


class Action(BaseModel):
    review: str


class Observation(BaseModel):
    task_id: str
    repository: str
    pr_number: int
    title: str
    description: str
    changed_files: list[str]
    diff: str
    step_count: int
    attempts_remaining: int
    last_action_error: str | None = None
    evaluator_feedback: str | None = None


class Reward(BaseModel):
    value: float
    breakdown: dict[str, float]


class State(BaseModel):
    benchmark: str
    task_name: str
    max_steps: int
    step_count: int
    total_reward: float
    done: bool
    current_task_id: str | None
    last_action_error: str | None
    review_history: list[str]


class PRReviewTask(BaseModel):
    task_id: str
    repository: str
    pr_number: int
    title: str
    description: str
    changed_files: list[str]
    diff: str
    expected_verdict: str
    required_findings: list[str]
    nice_to_have_findings: list[str]
    merge_blockers: list[str]
    live_github: bool = False


class MyEnvV4Env:
    def __init__(
        self,
        tasks: list[PRReviewTask],
        benchmark: str = "my_env_v4",
        task_name: str = "pr_review",
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        if not tasks:
            raise ValueError("At least one task is required to build the environment.")

        self._tasks = tasks
        self._benchmark = benchmark
        self._task_name = task_name
        self._max_steps = max_steps
        self._state = State(
            benchmark=benchmark,
            task_name=task_name,
            max_steps=max_steps,
            step_count=0,
            total_reward=0.0,
            done=False,
            current_task_id=None,
            last_action_error=None,
            review_history=[],
        )
        self._current_task: PRReviewTask | None = None

    @classmethod
    async def from_docker_image(cls, image_name: str | None = None) -> "MyEnvV4Env":
        del image_name
        tasks = load_tasks()
        task_name = os.getenv("MY_ENV_V4_TASK", "pr_review")
        benchmark = os.getenv("MY_ENV_V4_BENCHMARK", "my_env_v4")
        max_steps = int(os.getenv("MY_ENV_V4_MAX_STEPS", str(DEFAULT_MAX_STEPS)))
        return cls(tasks=tasks, benchmark=benchmark, task_name=task_name, max_steps=max_steps)

    async def reset(self) -> tuple[Observation, float, bool, dict[str, Any]]:
        repo_override = os.getenv("GITHUB_PR_REPO", "").strip()
        pr_override = os.getenv("GITHUB_PR_NUMBER", "").strip()
        task_override = os.getenv("PR_REVIEW_TASK_ID", "").strip()

        if repo_override and pr_override:
            try:
                pr_number = int(pr_override)
                return await self.reset_from_github(repo_override, pr_number)
            except ValueError:
                raise ValueError("GITHUB_PR_NUMBER must be an integer")

        self._current_task = select_task(self._tasks, task_override)
        self._state.step_count = 0
        self._state.total_reward = 0.0
        self._state.done = False
        self._state.current_task_id = self._current_task.task_id
        self._state.last_action_error = None
        self._state.review_history = []

        observation = self._build_observation(evaluator_feedback="Review the pull request and decide whether it is safe to merge.")
        reward = 0.0
        done = False
        info = {"task_id": self._current_task.task_id}
        return observation, reward, done, info

    async def reset_from_github(self, repo: str, pr_number: int) -> tuple[Observation, float, bool, dict[str, Any]]:
        github_token = os.getenv("GITHUB_TOKEN")
        self._current_task = load_github_pr_task(repo, pr_number, github_token=github_token)
        self._state.step_count = 0
        self._state.total_reward = 0.0
        self._state.done = False
        self._state.current_task_id = self._current_task.task_id
        self._state.last_action_error = None
        self._state.review_history = []

        observation = self._build_observation(evaluator_feedback="Review the GitHub pull request and decide whether it is safe to merge.")
        reward = 0.0
        done = False
        info = {"task_id": self._current_task.task_id, "live_github": True}
        return observation, reward, done, info

    async def step(self, action: Action) -> tuple[Observation, float, bool, dict[str, Any]]:
        if self._current_task is None:
            raise RuntimeError("Environment has not been reset.")

        if self._state.done:
            observation = self._build_observation(evaluator_feedback="Episode already finished.")
            reward = 0.0
            done = True
            info = {"reason": "episode_finished"}
            return observation, reward, done, info

        self._state.step_count += 1
        self._state.last_action_error = None

        review_text = (action.review or "").strip()
        if not review_text:
            self._state.last_action_error = "empty_review"
            done = self._state.step_count >= self._max_steps
            self._state.done = done
            observation = self._build_observation(evaluator_feedback="Your review was empty. Provide a verdict and concrete findings.")
            reward = 0.0
            info = {"score_breakdown": {}}
            return observation, reward, done, info

        verdict = extract_verdict(review_text)
        score_breakdown = score_review(review_text, verdict, self._current_task)
        reward = round(score_breakdown["total"], 2)

        # Penalize repetitive reviews
        if self._state.review_history and any(review_text.lower() in prev.lower() for prev in self._state.review_history[-2:]):
            reward = max(0.0, reward - 0.2)  # Penalty for repetition

        self._state.total_reward += reward
        self._state.review_history.append(review_text)

        success = reward >= 0.9
        done = success or self._state.step_count >= self._max_steps
        self._state.done = done

        feedback = build_feedback(review_text, score_breakdown, verdict, self._current_task)

        observation = self._build_observation(evaluator_feedback=feedback)
        info = {
            "task_id": self._current_task.task_id,
            "success": success,
            "score_breakdown": score_breakdown,
            "predicted_verdict": verdict,
        }
        return observation, reward, done, info

    async def state(self) -> State:
        return self._state

    async def close(self) -> None:
        return None

    def _build_observation(self, evaluator_feedback: str | None = None) -> Observation:
        if self._current_task is None:
            raise RuntimeError("Environment has not been reset.")

        attempts_remaining = max(self._max_steps - self._state.step_count, 0)
        return Observation(
            task_id=self._current_task.task_id,
            repository=self._current_task.repository,
            pr_number=self._current_task.pr_number,
            title=self._current_task.title,
            description=self._current_task.description,
            changed_files=self._current_task.changed_files,
            diff=self._current_task.diff,
            step_count=self._state.step_count,
            attempts_remaining=attempts_remaining,
            last_action_error=self._state.last_action_error,
            evaluator_feedback=evaluator_feedback,
        )


def load_tasks() -> list[PRReviewTask]:
    raw = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    return [PRReviewTask(**item) for item in raw["tasks"]]


def load_github_pr_task(repo: str, pr_number: int, github_token: str | None = None) -> PRReviewTask:
    github_api_url = "https://api.github.com"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    with httpx.Client(headers=headers, timeout=20.0) as client:
        pr_url = f"{github_api_url}/repos/{repo}/pulls/{pr_number}"
        response = client.get(pr_url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch PR {repo}#{pr_number}: {response.status_code} {response.text}")
        pr_data = response.json()

        diff_response = client.get(pr_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
        if diff_response.status_code != 200:
            raise ValueError(f"Failed to fetch diff for PR {repo}#{pr_number}: {diff_response.status_code}")
        diff_text = diff_response.text

        files_url = f"{github_api_url}/repos/{repo}/pulls/{pr_number}/files"
        files_response = client.get(files_url)
        if files_response.status_code != 200:
            raise ValueError(f"Failed to fetch changed files for PR {repo}#{pr_number}: {files_response.status_code}")
        files_data = files_response.json()
        changed_files = [file_info.get("filename", "") for file_info in files_data]

    title = pr_data.get("title") or "GitHub PR Review"
    description = pr_data.get("body") or ""

    return PRReviewTask(
        task_id=f"github-{repo.replace('/', '_')}-{pr_number}",
        repository=repo,
        pr_number=pr_number,
        title=title,
        description=description,
        changed_files=changed_files,
        diff=diff_text,
        expected_verdict="COMMENT",
        required_findings=[],
        nice_to_have_findings=[],
        merge_blockers=[],
        live_github=True,
    )


def select_task(tasks: list[PRReviewTask], task_id: str) -> PRReviewTask:
    if task_id:
        for task in tasks:
            if task.task_id == task_id:
                return task
        raise ValueError(f"Unknown PR_REVIEW_TASK_ID: {task_id}")
    return tasks[0]


def extract_verdict(review_text: str) -> str | None:
    normalized = review_text.upper()
    for verdict in ("APPROVE", "REQUEST_CHANGES", "COMMENT"):
        if verdict in normalized:
            return verdict
    return None


def score_review(review_text: str, verdict: str | None, task: PRReviewTask) -> dict[str, float]:
    normalized = normalize_text(review_text)

    if task.live_github:
        verdict_score = 0.4 if verdict else 0.0
        required_score = 0.0
        nice_to_have_score = 0.1 if any(keyword in normalized for keyword in ["test", "tests", "coverage", "security", "bug", "risk"]) else 0.0

        explanation_score = 0.0
        if len(review_text.split()) >= 40:
            explanation_score += 0.05
        if "test" in normalized or "tests" in normalized:
            explanation_score += 0.05

        total = min(verdict_score + nice_to_have_score + explanation_score, 1.0)
        return {
            "verdict": round(verdict_score, 4),
            "required_findings": round(required_score, 4),
            "nice_to_have_findings": round(nice_to_have_score, 4),
            "explanation": round(explanation_score, 4),
            "total": round(total, 4),
        }

    normalized = normalize_text(review_text)
    verdict_score = 0.4 if verdict == task.expected_verdict else 0.0

    required_hits = sum(1 for finding in task.required_findings if finding_in_text(finding, normalized))
    required_score = 0.4 * (required_hits / max(len(task.required_findings), 1))

    nice_to_have_hits = sum(1 for finding in task.nice_to_have_findings if finding_in_text(finding, normalized))
    nice_to_have_score = 0.1 * (nice_to_have_hits / max(len(task.nice_to_have_findings), 1))

    explanation_score = 0.0
    if len(review_text.split()) >= 40:
        explanation_score += 0.05
    if "test" in normalized or "tests" in normalized:
        explanation_score += 0.05

    total = min(verdict_score + required_score + nice_to_have_score + explanation_score, 1.0)
    return {
        "verdict": round(verdict_score, 4),
        "required_findings": round(required_score, 4),
        "nice_to_have_findings": round(nice_to_have_score, 4),
        "explanation": round(explanation_score, 4),
        "total": round(total, 4),
    }


def build_feedback(
    review_text: str,
    score_breakdown: dict[str, float],
    verdict: str | None,
    task: PRReviewTask,
) -> str:
    normalized_review = normalize_text(review_text)

    if task.live_github:
        feedback_parts = []
        if not verdict:
            feedback_parts.append("Add a verdict line with APPROVE, REQUEST_CHANGES, or COMMENT.")
        if score_breakdown["explanation"] < 0.1:
            feedback_parts.append("Add clearer justification and mention potential impacts or tests.")
        if score_breakdown["nice_to_have_findings"] < 0.1:
            feedback_parts.append("Mention security, bug risk, or test coverage if relevant.")
        if not feedback_parts:
            feedback_parts.append("Good live PR review. You identified a clear verdict and provided useful reasoning.")
        return " ".join(feedback_parts).strip()

    missing_required = [
        finding for finding in task.required_findings if not finding_in_text(finding, normalized_review)
    ]
    feedback_parts = []
    if verdict != task.expected_verdict:
        feedback_parts.append(
            f"Verdict mismatch: expected {task.expected_verdict}, but your review implied {verdict or 'NONE'}."
        )

    review_hint_parts = []
    for blocker in task.merge_blockers[:2]:
        review_hint_parts.append(f"Check whether the review addresses: {blocker}.")

    if missing_required:
        feedback_parts.append(
            "Missing high-priority findings: " + "; ".join(missing_required[:2]) + "."
        )
    if score_breakdown["explanation"] < 0.1:
        feedback_parts.append("Add clearer justification and mention test impact.")
    if not feedback_parts:
        feedback_parts.append("Strong review. You identified the main merge decision and key code risks.")

    feedback_parts.extend(review_hint_parts)
    return " ".join(feedback_parts).strip()


def finding_in_text(finding: str, normalized_review_text: str) -> bool:
    keywords = [token for token in re.split(r"[^a-z0-9]+", finding.lower()) if len(token) > 2]
    if not keywords:
        return False
    hits = sum(1 for keyword in keywords if keyword in normalized_review_text)
    threshold = max(1, min(3, len(keywords) - 1))
    return hits >= threshold


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
