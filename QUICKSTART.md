# Quick Start Guide

Get started with the AI PR Reviewer in 3 steps!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Your API Key

Choose one option:

**Option A: OpenAI**
```bash
export OPENAI_API_KEY="sk-..."
```

**Option B: Groq (Free)**
```bash
export GROQ_API_KEY="gsk-..."
export API_BASE_URL="https://api.groq.com/openai/v1"
export MODEL_NAME="llama-3.3-70b-versatile"
```

## Step 3: Run the UI

```bash
streamlit run ui_app.py
```

Open your browser to `http://localhost:8501` and start reviewing!

---

## What You Can Do

### 🎯 Review Pull Requests
Select from 3 real-world PR review scenarios:
- **Easy**: Simple documentation update
- **Medium**: React state management bug  
- **Hard**: Security vulnerability

### 🤖 AI-Powered Analysis
The UI runs AI models (via OpenAI or Groq) to analyze code changes and provide reviews.

### 📊 Get Detailed Scores
See how well the AI review matches expert standards:
- Verdict accuracy (40%)
- Key findings identified (40%)
- Nice-to-have insights (10%)
- Clear explanation (10%)

### 💾 Track Progress
View review history and performance statistics across sessions.

---

## Alternative Options

### Run Batch Inference
Test the AI on all 3 tasks without UI:
```bash
python inference.py
```

### API Server
Run as a REST API:
```bash
uvicorn app.main:app --reload
```

### Validate OpenEnv Compliance
```bash
openenv validate
```

---

## Need Help?

- **Local issues**: Check `requirements.txt` and environment variables
- **Hugging Face deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **API errors**: Verify your API key is valid and has credits
- **Bug reports**: Check the README and project issues

**Happy reviewing!** 🚀
