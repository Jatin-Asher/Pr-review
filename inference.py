import asyncio
import json
import os
import textwrap
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from dotenv import load_dotenv

from my_env_v4 import Action, MyEnvV4Env


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
API_KEY = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("HF_TOKEN")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("API_KEY")
)
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
TASK_NAME = os.getenv("MY_ENV_V4_TASK", "pr_review")
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "my_env_v4")
MAX_STEPS = int(os.getenv("MY_ENV_V4_MAX_STEPS", "4"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))
SUCCESS_SCORE_THRESHOLD = float(os.getenv("SUCCESS_SCORE_THRESHOLD", "0.90"))

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are reviewing a GitHub pull request inside an OpenEnv benchmark.
    Return a concise but substantive code review in plain text.
    Your review must include:
    1. A verdict line containing exactly one of: APPROVE, REQUEST_CHANGES, COMMENT
    2. A summary of the main risk
    3. Specific findings grounded in the diff
    4. Test impact or missing coverage
    Keep the answer focused on merge readiness.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    safe_action = action.replace("\n", "\\n")
    error_value = error if error else "null"
    print(
        f"[STEP] step={step} action={safe_action} reward={reward:.2f} done={str(done).lower()} error={error_value}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)


def build_user_prompt(observation: object, history: List[str]) -> str:
    history_block = "\n".join(history[-3:]) if history else "None"
    return textwrap.dedent(
        f"""
        Review this pull request.

        Task ID: {observation.task_id}
        Repository: {observation.repository}
        PR Number: {observation.pr_number}
        Title: {observation.title}
        Description: {observation.description}
        Changed Files: {", ".join(observation.changed_files)}
        Diff:
        {observation.diff}

        Evaluator Feedback:
        {observation.evaluator_feedback or "None"}

        Previous Attempts:
        {history_block}
        """
    ).strip()


def get_model_review(client: OpenAI, observation: object, history: List[str]) -> str:
    prompt = build_user_prompt(observation, history)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stream=False,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        return "VERDICT: COMMENT\nSummary: No review generated.\nFindings: Unable to analyze.\nTests: Unknown."
    return text


async def main() -> None:
    if not API_KEY:
        raise RuntimeError(
            f"Missing API key. Set GROQ_API_KEY in {ROOT_DIR / '.env'} or in your shell environment."
        )

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = await MyEnvV4Env.from_docker_image(LOCAL_IMAGE_NAME)

    history: List[str] = []
    rewards: List[float] = []
    success = False
    steps_taken = 0

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        observation, reward, done, info = await env.reset()

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            review_text = get_model_review(client, observation, history)
            observation, reward, done, info = await env.step(Action(review=review_text))

            rewards.append(reward)
            steps_taken = step

            error = observation.last_action_error
            log_step(
                step=step,
                action=review_text,
                reward=reward,
                done=done,
                error=error,
            )

            history.append(json.dumps({"step": step, "review": review_text, "reward": reward}))

            if done:
                break

        success = any(reward >= SUCCESS_SCORE_THRESHOLD for reward in rewards)
    finally:
        await env.close()
        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())
