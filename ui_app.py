import asyncio
import json
import os
from typing import Optional
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from my_env_v4 import MyEnvV4Env, Action

# Load environment variables
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="AI PR Reviewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 16px;
        padding: 10px 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .verdict-approve {
        color: #28a745;
        font-weight: bold;
    }
    .verdict-reject {
        color: #dc3545;
        font-weight: bold;
    }
    .verdict-comment {
        color: #ffc107;
        font-weight: bold;
    }
    .score-bar {
        background-color: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        height: 30px;
        margin: 10px 0;
    }
    .score-fill {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if "env" not in st.session_state:
    st.session_state.env = None
if "observation" not in st.session_state:
    st.session_state.observation = None
if "task_history" not in st.session_state:
    st.session_state.task_history = []
if "current_task_results" not in st.session_state:
    st.session_state.current_task_results = None
if "api_configured" not in st.session_state:
    st.session_state.api_configured = False

def check_api_key():
    """Check if API key is available"""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    return api_key is not None

@st.cache_resource
def get_environment():
    """Load the environment (cached)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    env = loop.run_until_complete(MyEnvV4Env.from_docker_image())
    return env

def get_score_color(score: float) -> str:
    """Get color based on score"""
    if score >= 0.9:
        return "#28a745"  # Green
    elif score >= 0.7:
        return "#ffc107"  # Yellow
    elif score >= 0.5:
        return "#fd7e14"  # Orange
    else:
        return "#dc3545"  # Red

def display_score_bar(score: float, label: str = "Score"):
    """Display a visual score bar"""
    color = get_score_color(score)
    percentage = int(score * 100)
    st.markdown(f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: bold;">{label}</span>
                <span style="font-weight: bold;">{percentage}%</span>
            </div>
            <div style="background-color: #e0e0e0; border-radius: 10px; overflow: hidden; height: 25px;">
                <div style="width: {percentage}%; height: 100%; background-color: {color}; 
                           border-radius: 10px; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_diff(diff_text: str):
    """Render a code diff with syntax highlighting"""
    st.markdown("**Code Changes:**")
    st.code(diff_text, language="diff")

def get_verdict_badge(verdict: Optional[str]) -> str:
    """Return HTML badge for verdict"""
    if verdict == "APPROVE":
        return '<span style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 5px;">✓ APPROVE</span>'
    elif verdict == "REQUEST_CHANGES":
        return '<span style="background-color: #dc3545; color: white; padding: 5px 10px; border-radius: 5px;">✗ REQUEST CHANGES</span>'
    else:
        return '<span style="background-color: #ffc107; color: black; padding: 5px 10px; border-radius: 5px;">◆ COMMENT</span>'

async def run_inference(observation, history):
    """Run AI inference on the task"""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    api_base_url = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
    model_name = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    
    if not api_key:
        st.error("❌ API key not found. Please set OPENAI_API_KEY or GROQ_API_KEY in your environment.")
        return None
    
    client = OpenAI(base_url=api_base_url, api_key=api_key)
    
    # Build prompt
    history_block = "\n".join(history[-2:]) if history else "None"
    prompt = f"""Review this pull request and provide a verdict.

Task ID: {observation.task_id}
Repository: {observation.repository}
PR Number: {observation.pr_number}
Title: {observation.title}
Description: {observation.description}
Changed Files: {", ".join(observation.changed_files)}

Diff:
{observation.diff}

Previous Attempts:
{history_block}

Provide a review with:
1. A verdict line containing exactly one of: APPROVE, REQUEST_CHANGES, COMMENT
2. A summary of the main risk or quality assessment
3. Specific findings grounded in the diff
4. Test impact or missing coverage"""
    
    system_prompt = """You are reviewing a GitHub pull request in an AI benchmark.
Return a concise but substantive code review in plain text.
Your review must include a clear verdict and specific technical findings."""
    
    try:
        with st.spinner("🤖 AI is reviewing the PR..."):
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
        return response.choices[0].message.content or ""
    except Exception as e:
        st.error(f"❌ Error calling AI API: {str(e)}")
        return None

def main():
    # Header
    st.markdown("# 🔍 AI PR Reviewer Benchmark")
    st.markdown("**An OpenEnv-compliant benchmark environment for evaluating AI code review agents**")
    st.markdown("---")
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Check API key status
        if check_api_key():
            st.success("✅ API Key Detected")
            st.session_state.api_configured = True
        else:
            st.warning("⚠️ No API Key Found")
            st.info("Set `OPENAI_API_KEY` or `GROQ_API_KEY` in your environment")
            st.session_state.api_configured = False
        
        st.markdown("### 📋 Tasks")
        st.info("""
        **Easy**: Simple documentation update
        
        **Medium**: React state management bug
        
        **Hard**: Security vulnerability in auth
        """)
        
        st.markdown("### 📊 Reward Breakdown")
        st.info("""
        - **Verdict (40%)**: Correct APPROVE/REQUEST_CHANGES
        - **Required Findings (40%)**: Key issues identified
        - **Nice-to-Have (10%)**: Extra insights
        - **Explanation (10%)**: Clear justification
        """)
        
        st.markdown("### 📚 Documentation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📖 View README"):
                st.info("README documentation available in project root")
        with col2:
            if st.button("🔗 OpenEnv Spec"):
                st.info("Full OpenEnv specification in openenv.yaml")
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["🚀 Run Review", "📊 Results", "📈 Statistics"])
    
    with tab1:
        st.markdown("## Start a PR Review")
        
        # Load environment
        try:
            env = get_environment()
        except Exception as e:
            st.error(f"Error loading environment: {str(e)}")
            return
        
        # Task selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            task_id = st.selectbox(
                "Select a Task:",
                ["django-auth-bypass (Hard - Security)", "react-stale-state (Medium - Bug)", "simple-doc-update (Easy - Docs)"],
                key="task_select"
            )
        
        # Map task name to ID
        task_map = {
            "django-auth-bypass (Hard - Security)": "django-auth-bypass",
            "react-stale-state (Medium - Bug)": "react-stale-state",
            "simple-doc-update (Easy - Docs)": "simple-doc-update"
        }
        task_id_selected = task_map[task_id]
        
        with col2:
            if st.button("🔄 Load Task", use_container_width=True):
                st.session_state.task_history = []
                st.session_state.current_task_results = None
        
        # Reset and load task
        os.environ["PR_REVIEW_TASK_ID"] = task_id_selected
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            observation, reward, done, info = loop.run_until_complete(env.reset())
            st.session_state.observation = observation
        except Exception as e:
            st.error(f"Error loading task: {str(e)}")
            return
        
        if st.session_state.observation:
            obs = st.session_state.observation
            
            # Display task details
            st.markdown("### 📋 Pull Request Details")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Repository", obs.repository)
            with col2:
                st.metric("PR Number", f"#{obs.pr_number}")
            with col3:
                st.metric("Difficulty", task_id.split("(")[1].split(" -")[0].strip())
            
            st.markdown(f"**Title:** `{obs.title}`")
            st.markdown(f"**Description:** {obs.description}")
            
            st.markdown("#### 📁 Changed Files")
            for file in obs.changed_files:
                st.markdown(f"  • `{file}`")
            
            # Display diff
            st.markdown("#### 📝 Diff")
            with st.expander("View Code Changes", expanded=True):
                render_diff(obs.diff)
            
            # Run review button
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if st.button("🤖 Run AI Review", use_container_width=True, key="run_review"):
                    if not st.session_state.api_configured:
                        st.error("❌ API not configured. Please set your API key.")
                    else:
                        # Run inference
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        review_text = loop.run_until_complete(run_inference(obs, st.session_state.task_history))
                        
                        if review_text:
                            # Step through environment
                            action = Action(review=review_text)
                            observation, reward, done, info = loop.run_until_complete(env.step(action))
                            
                            # Store results
                            st.session_state.current_task_results = {
                                "review": review_text,
                                "reward": reward,
                                "done": done,
                                "info": info,
                                "observation": observation
                            }
                            st.session_state.task_history.append(review_text)
                            st.session_state.observation = observation
                            
                            st.rerun()
            
            with col2:
                if st.button("Clear", use_container_width=True):
                    st.session_state.task_history = []
                    st.session_state.current_task_results = None
                    st.rerun()
    
    with tab2:
        st.markdown("## 📊 Review Results")
        
        if st.session_state.current_task_results:
            results = st.session_state.current_task_results
            
            # Display review
            st.markdown("### 🔍 AI Review")
            with st.expander("View Full Review", expanded=True):
                st.text_area("Review Content:", value=results["review"], height=200, disabled=True)
            
            # Display score
            st.markdown("### ⭐ Scoring")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Score", f"{results['reward']:.1%}", delta=f"{results['reward']:.2f}")
            
            with col2:
                st.metric("Success", "✅ Yes" if results["info"].get("success") else "❌ No")
            
            with col3:
                st.metric("Steps", results["observation"].step_count if results["observation"] else 0)
            
            with col4:
                st.metric("Attempts Left", results["observation"].attempts_remaining if results["observation"] else 0)
            
            # Score breakdown
            if "score_breakdown" in results["info"]:
                breakdown = results["info"]["score_breakdown"]
                st.markdown("#### Score Breakdown")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    display_score_bar(breakdown.get("verdict", 0), "Verdict")
                with col2:
                    display_score_bar(breakdown.get("required_findings", 0), "Required")
                with col3:
                    display_score_bar(breakdown.get("nice_to_have_findings", 0), "Nice-to-Have")
                with col4:
                    display_score_bar(breakdown.get("explanation", 0), "Explanation")
            
            # Predicted verdict
            if "predicted_verdict" in results["info"]:
                verdict = results["info"]["predicted_verdict"]
                st.markdown("#### 🎯 Predicted Verdict")
                st.markdown(get_verdict_badge(verdict), unsafe_allow_html=True)
            
            # Feedback
            if results["observation"] and results["observation"].evaluator_feedback:
                st.markdown("#### 💬 Evaluator Feedback")
                st.info(results["observation"].evaluator_feedback)
            
            # Action error
            if results["observation"] and results["observation"].last_action_error:
                st.markdown("#### ⚠️ Action Error")
                st.warning(f"Error: {results['observation'].last_action_error}")
        else:
            st.info("👈 Run a review on the **Run Review** tab to see results")
    
    with tab3:
        st.markdown("## 📈 Session Statistics")
        
        if st.session_state.task_history:
            st.markdown(f"### Session Overview")
            st.metric("Total Reviews Run", len(st.session_state.task_history))
            
            if st.session_state.current_task_results:
                st.metric("Current Task Score", f"{st.session_state.current_task_results['reward']:.1%}")
            
            st.markdown("### Review History")
            for i, review in enumerate(st.session_state.task_history, 1):
                with st.expander(f"Review #{i}", expanded=False):
                    st.text_area(f"Content", value=review, height=150, disabled=True, key=f"history_{i}")
        else:
            st.info("👈 No reviews yet. Start by running a review on the **Run Review** tab")
        
        # Task information
        st.markdown("---")
        st.markdown("### 📋 Available Tasks")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with st.container():
                st.markdown("**🟢 Easy**")
                st.markdown("`simple-doc-update`")
                st.caption("Documentation update - Should APPROVE")
        
        with col2:
            with st.container():
                st.markdown("**🟡 Medium**")
                st.markdown("`react-stale-state`")
                st.caption("React bug - Should REQUEST CHANGES")
        
        with col3:
            with st.container():
                st.markdown("**🔴 Hard**")
                st.markdown("`django-auth-bypass`")
                st.caption("Security issue - Should REQUEST CHANGES")

if __name__ == "__main__":
    main()
