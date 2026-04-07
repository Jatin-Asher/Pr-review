# AI PR Reviewer

This project implements a complete OpenEnv-compliant benchmark environment for training and evaluating AI code review agents.

**[🚀 Quick Start](QUICKSTART.md)** | **[📦 Deploy to Hugging Face](DEPLOYMENT.md)** | **[📚 Documentation](#documentation)**

## Features

- ✅ **OpenEnv Spec Compliant**: Full implementation with typed Pydantic models, proper step/reset methods, and metadata
- ✅ **Real-world Task Simulation**: Code review tasks that humans actually perform
- ✅ **Multiple Difficulty Levels**: Easy, medium, and hard tasks with clear success criteria
- ✅ **Meaningful Reward Function**: Partial progress rewards with penalties for bad behavior
- ✅ **Baseline Inference Script**: Uses OpenAI API with reproducible scoring
- ✅ **Interactive Web UI**: Beautiful Streamlit interface for hands-on exploration
- ✅ **Hugging Face Spaces Ready**: Deploy in minutes with one-click setup

## Project layout

- `app/` FastAPI webhook scaffold
- `my_env_v4.py` OpenEnv-compliant benchmark environment
- `ui_app.py` **Streamlit web UI** (main entry point for Hugging Face Spaces)
- `tasks/pr_review_tasks.json` 3 benchmark tasks (easy/medium/hard)
- `inference.py` OpenAI client inference runner
- `openenv.yaml` Environment metadata
- `requirements.txt` Dependencies including Pydantic and Streamlit

## Environment variables

Make sure these exist before running inference:

- `OPENAI_API_KEY` (or `GROQ_API_KEY`, `API_KEY`)
- `API_BASE_URL` (defaults to OpenAI)
- `MODEL_NAME` (defaults to gpt-4)

You can copy `.env.example` to `.env` and fill in the values you want.

## Getting Started

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Set Your API Key

**OpenAI:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Or use Groq (Free):**
```bash
export GROQ_API_KEY="gsk-..."
export API_BASE_URL="https://api.groq.com/openai/v1"
export MODEL_NAME="llama-3.3-70b-versatile"
```

### 3️⃣ Launch the UI

```bash
streamlit run ui_app.py
```

Open your browser to `http://localhost:8501` and start exploring!

---

## Run the benchmark inference script

```bash
python inference.py
```

This runs the AI on all 3 tasks and outputs reproducible baseline scores.

## Validate OpenEnv compliance

```bash
openenv validate
```

## Run the FastAPI app

```bash
uvicorn app.main:app --reload
```

## Deployment on Hugging Face Spaces

1. Create a new Hugging Face Space
2. Select **Python SDK** (automatically detects Streamlit)
3. Upload the project files or connect your GitHub repo
4. Set environment variables in Spaces secrets:
   - `OPENAI_API_KEY` or `GROQ_API_KEY` (required)
   - `API_BASE_URL` (optional, defaults to OpenAI)
   - `MODEL_NAME` (optional, defaults to gpt-4)
5. Rename `ui_app.py` to `app.py` (or update `.streamlit/config.toml`)
6. The Spaces will automatically run `streamlit run app.py`

**Example Spaces Setup:**
```
.
├── app.py (renamed from ui_app.py)
├── my_env_v4.py
├── inference.py
├── tasks/
│   └── pr_review_tasks.json
├── openenv.yaml
├── requirements.txt
└── .streamlit/
    └── config.toml
```

## Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get up and running in 3 steps
- **[Deployment Guide](DEPLOYMENT.md)** - Deploy to Hugging Face Spaces with detailed instructions
- **[OpenEnv Spec](openenv.yaml)** - Environment metadata and configuration



## Notes

- The benchmark environment currently uses local PR review tasks instead of a real container image.
- `MyEnvV4Env.from_docker_image()` is implemented so it matches the expected integration shape.
- The inference script prints the required `[START]`, `[STEP]`, and `[END]` lines.
- Groq works through the standard OpenAI Python client by pointing `API_BASE_URL` to `https://api.groq.com/openai/v1`.
- The Streamlit UI (`ui_app.py`) is the recommended entry point for users and Hugging Face Spaces deployments.
