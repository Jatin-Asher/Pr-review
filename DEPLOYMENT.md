# Hugging Face Spaces Deployment Guide

This guide explains how to deploy the AI PR Reviewer project on Hugging Face Spaces.

## Prerequisites

- A Hugging Face account (https://huggingface.co)
- OpenAI API key or Groq API key
- Basic familiarity with Hugging Face Spaces

## Quick Start (5 minutes)

### Step 1: Create a New Space

1. Go to https://huggingface.co/spaces
2. Click "Create New Space"
3. Fill in the details:
   - **Space name**: `ai-pr-reviewer` (or your choice)
   - **License**: MIT
   - **Select the Space SDK**: Select **Python SDK** (Streamlit)
4. Click "Create Space"

### Step 2: Add Files

You have two options:

#### Option A: Git Clone (Recommended)

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/ai-pr-reviewer
cd ai-pr-reviewer
# Copy all project files here
git add .
git commit -m "Initial commit"
git push
```

#### Option B: Manual Upload

1. In the Space, click "Files" tab
2. Upload these files:
   - `app.py` (rename from `ui_app.py`)
   - `my_env_v4.py`
   - `inference.py`
   - `requirements.txt`
   - `openenv.yaml`
   - Folder: `tasks/` with `pr_review_tasks.json`
   - Folder: `app/` with all FastAPI files
   - Folder: `.streamlit/` with `config.toml`

### Step 3: Set Environment Variables

1. In your Space, click "Settings" (gear icon)
2. Scroll to "Repository secrets"
3. Add these secrets:
   - **OPENAI_API_KEY**: Your OpenAI API key
   - **GROQ_API_KEY**: (optional) Your Groq API key
   - **API_BASE_URL**: (optional) `https://api.groq.com/openai/v1` (if using Groq)
   - **MODEL_NAME**: (optional) `gpt-4` or `llama-3.3-70b-versatile`

### Step 4: Deploy

The Space will automatically:
1. Install dependencies from `requirements.txt`
2. Run `streamlit run app.py`
3. Launch the web interface

Your app is now live! Share the Space URL with others.

## File Structure for Spaces

```
ai-pr-reviewer/
├── app.py                    # Main Streamlit app (rename from ui_app.py)
├── my_env_v4.py             # Environment implementation
├── inference.py             # Baseline inference script
├── requirements.txt         # Dependencies
├── openenv.yaml             # OpenEnv metadata
├── tasks/
│   └── pr_review_tasks.json # Task definitions
├── app/                     # FastAPI code (optional for Spaces)
│   ├── __init__.py
│   ├── main.py
│   ├── github.py
│   ├── ai.py
│   └── utils.py
└── .streamlit/
    └── config.toml          # Streamlit configuration
```

## API Key Setup

### Using OpenAI

1. Get your API key from https://platform.openai.com/account/api-keys
2. Add to Space secrets as `OPENAI_API_KEY`

### Using Groq (Free Alternative)

1. Sign up at https://console.groq.com
2. Get your API key
3. Add to Space secrets:
   - `GROQ_API_KEY`: Your Groq key
   - `API_BASE_URL`: `https://api.groq.com/openai/v1`
   - `MODEL_NAME`: `llama-3.3-70b-versatile`

## Troubleshooting

### Space won't start
- Check if all required dependencies are in `requirements.txt`
- Verify environment variables are set correctly
- Check the Space logs for errors

### API key errors
- Ensure the secret name matches exactly (case-sensitive)
- Verify your key is valid
- Check if the API has insufficient quota

### UI not loading
- Clear browser cache and refresh
- Check Streamlit logs in Space for errors
- Verify all Python files are uploaded

## Local Testing Before Deployment

Test your setup locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key-here"
# or for Groq:
export GROQ_API_KEY="your-key-here"
export API_BASE_URL="https://api.groq.com/openai/v1"
export MODEL_NAME="llama-3.3-70b-versatile"

# Run the app
streamlit run ui_app.py
```

Then visit `http://localhost:8501` in your browser.

## Performance Tips

- **Choose a faster model**: If using OpenAI, consider `gpt-3.5-turbo` instead of `gpt-4` for faster reviews
- **Use Groq**: Free tier is often faster than OpenAI for the same quality
- **Cache tasks**: The environment caches loaded tasks, so cold starts are infrequent

## Support

For issues or questions:
1. Check the README.md in the main repo
2. Review the [Streamlit docs](https://docs.streamlit.io)
3. Check [Hugging Face Spaces docs](https://huggingface.co/docs/hub/spaces)

## Next Steps

- Share your Space URL with others
- Customize the theme in `.streamlit/config.toml`
- Extend tasks in `tasks/pr_review_tasks.json`
- Integrate with GitHub webhooks using the FastAPI app
