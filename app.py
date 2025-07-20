import streamlit as st
from src.security_expert.crew import SecurityExpertCrew
from dotenv import load_dotenv
import os
import time
from datetime import datetime
import re

load_dotenv()

st.set_page_config(
    page_title="AI Security Expert",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- Custom Styling --------------------
st.markdown("""
<style>
    .stDeployButton {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px; }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
    }

    .main-header h1 { margin: 0; font-size: 2.5rem; font-weight: 700; }
    .main-header p { margin-top: 0.5rem; font-size: 1.1rem; opacity: 0.9; }

    .card { background: #1e1e2f; color: #fff; padding: 1rem; border-radius: 10px; margin: 0.5rem 0; border: 1px solid #333; }

    .chat-message {
        background: #1e1e2f;
        color: #fff;
        padding: 1.25rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }

    .user-message {
        background: #3b3b4f;
        border-left: 4px solid #764ba2;
    }

    .analysis-result {
        background: #2b3a3a;
        border-left: 4px solid #28a745;
    }

    .error-result {
        background: #4a2a2a;
        border-left: 4px solid #dc3545;
    }

    .metric-card {
        background: #667eea;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }

    .section-header {
        color: #eee;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 1rem 0 0.5rem;
        border-bottom: 1px solid #444;
        padding-bottom: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Logic --------------------
def run_security_crew(tech_stack: str, api_key: str = None) -> dict:
    try:
        inputs = {'tech_stack_description': tech_stack}
        crew = SecurityExpertCrew(api_key=api_key)
        result = crew.crew().kickoff(inputs=inputs)
        return {
            "status": "success",
            "analysis": str(result),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tech_stack": tech_stack
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tech_stack": tech_stack
        }

def parse_report(report_text: str) -> dict:
    sections = {}
    pattern = r"##\s(.*?)\n(.*?)(?=\n##\s|\Z)"
    matches = re.findall(pattern, report_text, re.DOTALL)
    if not matches:
        return {"📋 Full Report": report_text}
    for title, content in matches:
        sections[title.strip()] = content.strip().replace("###", "####")
    return sections

# -------------------- State Init --------------------
if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quick_input" not in st.session_state:
    st.session_state.quick_input = ""

# -------------------- Main Header --------------------
st.markdown("""
<div class="main-header">
    <h1>🛡️ AI Security Expert</h1>
    <p>Advanced Security Analysis for Your Technology Stack</p>
</div>
""", unsafe_allow_html=True)

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown('<div class="section-header">🔧 Configuration</div>', unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key", type="password", key="gemini_key", placeholder="Enter API key...")
    serper_key = st.text_input("Serper API Key (Optional)", type="password", key="serper_key", placeholder="Enter Serper key...")

    st.markdown('<div class="section-header">📊 Session Stats</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-card">{st.session_state.analysis_count}<br><small>Analyses</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">{len(st.session_state.messages)}<br><small>Messages</small></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">🚀 Quick Actions</div>', unsafe_allow_html=True)
    if st.button("🌐 Web App Stack"): st.session_state.quick_input = "React frontend with Node.js Express backend, MongoDB database, deployed on AWS EC2 with S3 for file storage"
    if st.button("📱 Mobile App Stack"): st.session_state.quick_input = "Flutter app with Firebase backend"
    if st.button("☁️ Cloud Native Stack"): st.session_state.quick_input = "Docker + Kubernetes + PostgreSQL + Redis on GCP"
    if st.button("🧠 Deep Learning Stack"): st.session_state.quick_input = "PyTorch + HuggingFace Transformers + FastAPI + Docker + NVIDIA GPU"
    st.markdown("---")
    if st.button("🗑️ Clear Chat"): st.session_state.messages = []; st.session_state.analysis_count = 0; st.rerun()

# -------------------- Chat Display --------------------
st.markdown('<div class="section-header">💬 Security Analysis Chat</div>', unsafe_allow_html=True)
with st.container():
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            if "analysis_data" in msg:
                data = msg["analysis_data"]
                if data.get("status") == "success":
                    st.markdown(f'<div class="chat-message analysis-result"><strong>Security Expert:</strong><br><em>Stack:</em> {data["tech_stack"]} <br><small>{data["timestamp"]}</small></div>', unsafe_allow_html=True)
                    parsed = parse_report(data["analysis"])
                    if len(parsed) > 1:
                        tabs = st.tabs([f"📄 {k}" for k in parsed])
                        for tab, content in zip(tabs, parsed.values()):
                            with tab: st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="card">{data["analysis"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message error-result"><strong>Error:</strong><br>{data["error"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message"><strong>Security Expert:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)

# -------------------- Prompt Input --------------------
prompt = st.session_state.quick_input if st.session_state.quick_input else st.chat_input("💬 Describe your tech stack...")
st.session_state.quick_input = ""

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.empty():
        st.markdown(f'''
        <div class="chat-message status-analyzing">
            🔄 Analyzing <code>{prompt}</code>...
        </div>
        ''', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        for i in range(100): time.sleep(0.02); progress_bar.progress(i + 1)

        data = run_security_crew(prompt, api_key or None)
        progress_bar.empty()
        if data["status"] == "success":
            st.session_state.analysis_count += 1
        st.session_state.messages.append({
            "role": "assistant",
            "content": data.get("analysis", ""),
            "analysis_data": data
        })
    st.rerun()