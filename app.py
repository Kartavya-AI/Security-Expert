import streamlit as st
from src.security_expert.crew import SecurityExpertCrew
from dotenv import load_dotenv
import os
import time
from datetime import datetime
import re
import sqlite3
import json

load_dotenv()

# -------------------- DB and Logging Setup --------------------
DB_FILE = "security_analysis.db"
LOG_FILE = "logs.json"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            analysis_summary TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_analysis_to_db(session_id, tech_stack, summary):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analysis_history (session_id, tech_stack, analysis_summary, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (session_id, tech_stack, summary, datetime.now()))
    conn.commit()
    conn.close()

def get_history_from_db(session_id):
    conn = sqlite3.connect(DB_FILE)
    # PARSE_DECLTYPES allows sqlite to recognize the DATETIME type
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT tech_stack, analysis_summary, timestamp FROM analysis_history WHERE session_id = ? ORDER BY timestamp DESC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def log_error(error_details):
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)
    with open(LOG_FILE, 'r+') as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
        logs.append(error_details)
        f.seek(0)
        json.dump(logs, f, indent=4)

# Initialize the database
init_db()


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
        color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem;
    }
    .main-header h1 { margin: 0; font-size: 2.5rem; font-weight: 700; }
    .main-header p { margin-top: 0.5rem; font-size: 1.1rem; opacity: 0.9; }
    .card { background: #1e1e2f; color: #fff; padding: 1rem; border-radius: 10px; margin: 0.5rem 0; border: 1px solid #333; }
    .chat-message { background: #1e1e2f; color: #fff; padding: 1.25rem; border-radius: 10px; margin: 0.5rem 0; border-left: 4px solid #667eea; }
    .user-message { background: #3b3b4f; border-left: 4px solid #764ba2; }
    .analysis-result { background: #2b3a3a; border-left: 4px solid #28a745; }
    .error-result { background: #4a2a2a; border-left: 4px solid #dc3545; }
    .metric-card { background: #667eea; color: white; padding: 1rem; border-radius: 10px; text-align: center; }
    .section-header { color: #eee; font-size: 1.2rem; font-weight: bold; margin: 1rem 0 0.5rem; border-bottom: 1px solid #444; padding-bottom: 0.2rem; }
</style>
""", unsafe_allow_html=True)

# -------------------- Logic --------------------
def run_security_crew(tech_stack: str, api_key: str = None, serper_key: str = None) -> dict:
    try:
        inputs = {'tech_stack_description': tech_stack}
        crew = SecurityExpertCrew(api_key=api_key, serper_key=serper_key)
        result = crew.crew().kickoff(inputs=inputs)
        return {
            "status": "success",
            "analysis": str(result),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tech_stack": tech_stack
        }
    except Exception as e:
        error_info = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tech_stack": tech_stack,
        }
        log_error(error_info)
        return error_info

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
if "session_id" not in st.session_state:
    st.session_state.session_id = os.urandom(24).hex()
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
    api_key = st.text_input("Gemini API Key", type="password", key="gemini_key", placeholder="Enter your Gemini API key")
    serper_key = st.text_input("Serper API Key (Optional)", type="password", key="serper_key", placeholder="Enter your Serper API key")

    st.markdown('<div class="section-header">📊 Session Stats</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-card">{st.session_state.analysis_count}<br><small>Analyses</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">{len(st.session_state.messages)}<br><small>Messages</small></div>', unsafe_allow_html=True)
    st.markdown("---")

    # -------------------- PREVIOUS CHAT HISTORY (NEW CODE) --------------------
    st.markdown('<div class="section-header">📜 Analysis History</div>', unsafe_allow_html=True)
    history = get_history_from_db(st.session_state.session_id)

    if not history:
        st.info("No analyses in the current session yet.")
    else:
        with st.expander("View Past Analyses", expanded=False):
            for i, item in enumerate(history):
                # Using item['tech_stack'] and item['timestamp'] as conn.row_factory is set
                tech_stack = item['tech_stack']
                ts = item['timestamp']
                
                # Format the timestamp for better readability
                formatted_ts = ts.strftime("%b %d, %H:%M") if isinstance(ts, datetime) else ts

                st.markdown(f"""
                <div class="card" style="margin-bottom: 10px; padding: 0.8rem;">
                    <p style="font-size: 0.9rem; font-weight: bold; margin-bottom: 5px;">{tech_stack}</p>
                    <small><em>Analyzed: {formatted_ts}</em></small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Re-run Analysis", key=f"history_btn_{i}"):
                    st.session_state.quick_input = tech_stack
                    st.rerun()
    st.markdown("---")
    # -------------------- END OF NEW CODE --------------------

    st.markdown('<div class="section-header">🚀 Quick Actions</div>', unsafe_allow_html=True)
    if st.button("🌐 Web App Stack"): st.session_state.quick_input = "React frontend with Node.js Express backend, MongoDB database, deployed on AWS EC2"
    if st.button("📱 Mobile App Stack"): st.session_state.quick_input = "Flutter app with Firebase backend"
    if st.button("☁️ Cloud Native Stack"): st.session_state.quick_input = "Docker + Kubernetes + PostgreSQL + Redis on GCP"
    st.markdown("---")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.analysis_count = 0
        st.rerun()

# -------------------- Chat Display --------------------
with st.container():
    for msg in st.session_state.messages:
        role = msg["role"]
        with st.chat_message(role):
            if role == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
            elif role == "assistant":
                if "analysis_data" in msg:
                    data = msg["analysis_data"]
                    if data.get("status") == "success":
                        st.markdown(f'<div class="chat-message analysis-result"><strong>Security Expert:</strong><br><em>Stack:</em> {data["tech_stack"]} <br><small>{data["timestamp"]}</small></div>', unsafe_allow_html=True)
                        parsed = parse_report(data["analysis"])
                        tabs = st.tabs([f"📄 {k}" for k in parsed.keys()])
                        for i, (tab, content) in enumerate(zip(tabs, parsed.values())):
                            with tab: st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-message error-result"><strong>Error:</strong><br>{data["error"]}</div>', unsafe_allow_html=True)

# -------------------- Prompt Input & Processing --------------------
prompt = st.session_state.quick_input or st.chat_input("💬 Describe your tech stack...")
if st.session_state.quick_input:
    st.session_state.quick_input = ""

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{prompt}</div>', unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner(f"Analyzing '{prompt}'..."):
            data = run_security_crew(prompt, api_key or os.getenv("GEMINI_API_KEY"), serper_key or os.getenv("SERPER_API_KEY"))

            if data["status"] == "success":
                st.session_state.analysis_count += 1
                add_analysis_to_db(st.session_state.session_id, prompt, data["analysis"])

            st.session_state.messages.append({
                "role": "assistant",
                "content": data.get("analysis", ""),
                "analysis_data": data
            })
    st.rerun()