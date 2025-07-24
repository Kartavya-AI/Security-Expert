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
            interview_results TEXT,
            analysis_summary TEXT NOT NULL,
            analysis_type TEXT DEFAULT 'comprehensive',
            timestamp DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_analysis_to_db(session_id, tech_stack, interview_results, summary, analysis_type='comprehensive'):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analysis_history (session_id, tech_stack, interview_results, analysis_summary, analysis_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, tech_stack, interview_results, summary, analysis_type, datetime.now()))
    conn.commit()
    conn.close()

def get_history_from_db(session_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT tech_stack, interview_results, analysis_summary, analysis_type, timestamp FROM analysis_history WHERE session_id = ? ORDER BY timestamp DESC", (session_id,))
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
    .interviewer-message { background: #2a3a4a; border-left: 4px solid #ffa500; }
    .analysis-result { background: #2b3a3a; border-left: 4px solid #28a745; }
    .error-result { background: #4a2a2a; border-left: 4px solid #dc3545; }
    .metric-card { background: #667eea; color: white; padding: 1rem; border-radius: 10px; text-align: center; }
    .section-header { color: #eee; font-size: 1.2rem; font-weight: bold; margin: 1rem 0 0.5rem; border-bottom: 1px solid #444; padding-bottom: 0.2rem; }
    .process-indicator { background: #2a3a4a; padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #17a2b8; }
    .interview-phase { background: #2a3a4a; padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #ffa500; }
    .ready-for-analysis { background: #1e3a1e; padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #28a745; }
</style>
""", unsafe_allow_html=True)

# -------------------- Logic --------------------
def start_interview(tech_stack: str, api_key: str = None, serper_key: str = None) -> dict:
    """Start the interview process with the first question"""
    try:
        crew = SecurityExpertCrew(api_key=api_key, serper_key=serper_key)
        inputs = {
            'tech_stack_description': tech_stack,
            'conversation_history': "",
            'user_response': "",
            'action': 'start_interview'
        }
        result = crew.kickoff(inputs=inputs)
        
        return {
            "status": "success",
            "message": str(result),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "interview_question"
        }
    except Exception as e:
        error_info = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        log_error(error_info)
        return error_info

def continue_interview(user_response: str, conversation_history: str, api_key: str = None, serper_key: str = None) -> dict:
    """Continue the interview with user's response"""
    try:
        crew = SecurityExpertCrew(api_key=api_key, serper_key=serper_key)
        inputs = {
            'tech_stack_description': "",
            'user_response': user_response,
            'conversation_history': conversation_history,
            'action': 'continue_interview'
        }
        result = crew.kickoff(inputs=inputs)
        
        return {
            "status": "success",
            "message": str(result),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "interview_question"
        }
    except Exception as e:
        error_info = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        log_error(error_info)
        return error_info

def perform_analysis(conversation_history: str, api_key: str = None, serper_key: str = None) -> dict:
    """Perform final security analysis based on interview"""
    try:
        crew = SecurityExpertCrew(api_key=api_key, serper_key=serper_key)
        inputs = {
            'tech_stack_description': "",
            'conversation_history': conversation_history,
            'user_response': "",
            'action': 'perform_analysis'
        }
        result = crew.kickoff(inputs=inputs)
        
        return {
            "status": "success",
            "analysis": str(result),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "final_analysis"
        }
    except Exception as e:
        error_info = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        log_error(error_info)
        return error_info

def parse_report(report_text: str) -> dict:
    sections = {}
    # Updated pattern to handle both single # and ## headings
    pattern = r"##?\s+(.*?)\n(.*?)(?=\n##?\s+|\Z)"
    matches = re.findall(pattern, report_text, re.DOTALL)
    if not matches:
        return {"📋 Full Report": report_text}
    for title, content in matches:
        # Clean up the title and add appropriate emoji if missing
        clean_title = title.strip()
        if not any(emoji in clean_title for emoji in ['🎯', '🚨', '⚠️', '✅', '🔧', '🛡️', '📊', '🔗', '📋']):
            if 'executive' in clean_title.lower() or 'summary' in clean_title.lower():
                clean_title = f"🎯 {clean_title}"
            elif 'critical' in clean_title.lower() or 'vulnerability' in clean_title.lower():
                clean_title = f"🚨 {clean_title}"
            elif 'recommendation' in clean_title.lower() or 'action' in clean_title.lower():
                clean_title = f"✅ {clean_title}"
            elif 'profile' in clean_title.lower() or 'technology' in clean_title.lower():
                clean_title = f"📋 {clean_title}"
            else:
                clean_title = f"📄 {clean_title}"
        sections[clean_title] = content.strip().replace("###", "####")
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
if "interview_phase" not in st.session_state:
    st.session_state.interview_phase = "not_started"  # not_started, interviewing, ready_for_analysis, completed
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = ""
if "initial_tech_stack" not in st.session_state:
    st.session_state.initial_tech_stack = ""

# -------------------- Main Header --------------------
st.markdown("""
<div class="main-header">
    <h1>🛡️ AI Security Expert</h1>
    <p>Interactive Security Analysis through Comprehensive Requirements Gathering</p>
</div>
""", unsafe_allow_html=True)

# Add process explanation
if st.session_state.interview_phase == "not_started":
    st.markdown("""
    <div class="process-indicator">
        <strong>🔄 How it works:</strong><br>
        1. <strong>Start:</strong> Tell us about your tech stack<br>
        2. <strong>Interview:</strong> Our AI expert will ask specific questions about your setup<br>
        3. <strong>Analysis:</strong> Get a comprehensive, tailored security report<br>
        4. <strong>Follow-up:</strong> Ask additional questions about the recommendations
    </div>
    """, unsafe_allow_html=True)
elif st.session_state.interview_phase == "interviewing":
    st.markdown("""
    <div class="interview-phase">
        <strong>📋 Interview Phase Active:</strong> Answer the questions below to help us understand your specific implementation. 
        When you're ready, click "Generate Security Analysis" to get your tailored report.
    </div>
    """, unsafe_allow_html=True)
elif st.session_state.interview_phase == "ready_for_analysis":
    st.markdown("""
    <div class="ready-for-analysis">
        <strong>✅ Interview Complete:</strong> Ready to generate your comprehensive security analysis!
    </div>
    """, unsafe_allow_html=True)

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown('<div class="section-header">🔧 Configuration</div>', unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key", type="password", key="gemini_key", placeholder="Enter your Gemini API key")
    serper_key = st.text_input("Serper API Key (Optional)", type="password", key="serper_key", placeholder="For enhanced research capabilities")

    st.markdown('<div class="section-header">📊 Session Stats</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-card">{st.session_state.analysis_count}<br><small>Analyses</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">{len(st.session_state.messages)}<br><small>Messages</small></div>', unsafe_allow_html=True)
    
    # Show interview phase status
    phase_emoji = {
        "not_started": "⏸️",
        "interviewing": "❓",
        "ready_for_analysis": "✅",
        "completed": "🎯"
    }
    phase_text = {
        "not_started": "Not Started",
        "interviewing": "Interview Active",
        "ready_for_analysis": "Ready for Analysis",
        "completed": "Analysis Complete"
    }
    st.markdown(f'<div class="metric-card">{phase_emoji.get(st.session_state.interview_phase, "❓")}<br><small>{phase_text.get(st.session_state.interview_phase, "Unknown")}</small></div>', unsafe_allow_html=True)
    
    st.markdown("---")

    # Show analysis button if ready
    if st.session_state.interview_phase == "ready_for_analysis":
        if st.button("🔍 Generate Security Analysis", type="primary"):
            with st.spinner("🔬 Performing comprehensive security analysis..."):
                analysis_result = perform_analysis(
                    st.session_state.conversation_history,
                    api_key or os.getenv("GEMINI_API_KEY"),
                    serper_key or os.getenv("SERPER_API_KEY")
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Security Analysis Complete",
                    "analysis_data": analysis_result
                })
                
                if analysis_result["status"] == "success":
                    st.session_state.interview_phase = "completed"
                    st.session_state.analysis_count += 1
                    add_analysis_to_db(
                        st.session_state.session_id,
                        st.session_state.initial_tech_stack,
                        st.session_state.conversation_history,
                        analysis_result["analysis"],
                        "comprehensive"
                    )
                st.rerun()

    # -------------------- Analysis History --------------------
    st.markdown('<div class="section-header">📜 Analysis History</div>', unsafe_allow_html=True)
    history = get_history_from_db(st.session_state.session_id)

    if not history:
        st.info("No analyses in the current session yet.")
    else:
        with st.expander("View Past Analyses", expanded=False):
            for i, item in enumerate(history):
                tech_stack = item['tech_stack']
                ts = item['timestamp']
                analysis_type = item['analysis_type'] if 'analysis_type' in item.keys() else 'comprehensive'
                
                formatted_ts = ts.strftime("%b %d, %H:%M") if isinstance(ts, datetime) else ts

                st.markdown(f"""
                <div class="card" style="margin-bottom: 10px; padding: 0.8rem;">
                    <p style="font-size: 0.9rem; font-weight: bold; margin-bottom: 5px;">{tech_stack}</p>
                    <small><em>Type: {analysis_type.title()} | {formatted_ts}</em></small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Re-run Analysis", key=f"history_btn_{i}"):
                    # Reset session for new analysis
                    st.session_state.interview_phase = "not_started"
                    st.session_state.conversation_history = ""
                    st.session_state.messages = []
                    st.session_state.quick_input = tech_stack
                    st.rerun()
    
    st.markdown("---")

    st.markdown('<div class="section-header">🚀 Quick Start Examples</div>', unsafe_allow_html=True)
    if st.button("🌐 Web Application"): 
        st.session_state.quick_input = "React frontend with Node.js Express backend, MongoDB database"
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.messages = []
    if st.button("📱 Mobile Application"): 
        st.session_state.quick_input = "Flutter mobile app with Firebase backend"
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.messages = []
    if st.button("☁️ Cloud Native Stack"): 
        st.session_state.quick_input = "Microservices with Docker and Kubernetes"
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.messages = []
    if st.button("🤖 AI/ML Application"): 
        st.session_state.quick_input = "Python ML application with TensorFlow and PostgreSQL"
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.messages = []
    if st.button("🏢 Enterprise System"): 
        st.session_state.quick_input = "Java Spring Boot application with Oracle database"
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.messages = []
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.analysis_count = 0
        st.session_state.interview_phase = "not_started"
        st.session_state.conversation_history = ""
        st.session_state.initial_tech_stack = ""
        st.rerun()
    
    if st.session_state.interview_phase == "interviewing":
        if st.button("✅ Skip to Analysis", help="Skip remaining questions and proceed with current information"):
            st.session_state.interview_phase = "ready_for_analysis"
            st.rerun()

# -------------------- Chat Display --------------------
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
                        if data.get("type") == "interview_question":
                            st.markdown(f'<div class="chat-message interviewer-message"><strong>🤖 Security Expert:</strong><br>{data["message"]}</div>', unsafe_allow_html=True)
                        elif data.get("type") == "final_analysis":
                            st.markdown(f'<div class="chat-message analysis-result"><strong>🛡️ Security Analysis Complete:</strong><br><small>{data["timestamp"]}</small></div>', unsafe_allow_html=True)
                            parsed_analysis = parse_report(data["analysis"])
                            if parsed_analysis:
                                # Default the first section to be open
                                first_title = next(iter(parsed_analysis))
                                for title, content in parsed_analysis.items():
                                    with st.expander(title, expanded=(title == first_title)):
                                        st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-message error-result"><strong>❌ Error:</strong><br>{data["error"]}<br><small>{data.get("timestamp", "")}</small></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message interviewer-message"><strong>🤖 Security Expert:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)

# -------------------- Input Processing --------------------
# Handle quick input
if st.session_state.quick_input:
    prompt = st.session_state.quick_input
    st.session_state.quick_input = ""
else:
    # Dynamic prompt based on phase
    if st.session_state.interview_phase == "not_started":
        prompt = st.chat_input("💬 Describe your technology stack to begin the security interview...")
    elif st.session_state.interview_phase == "interviewing":
        prompt = st.chat_input("💬 Answer the security expert's question...")
    elif st.session_state.interview_phase == "completed":
        prompt = st.chat_input("💬 Ask follow-up questions about your security analysis...")
    else:
        prompt = st.chat_input("💬 Type your message...")

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(f'<div class="chat-message user-message"><strong>You:</strong><br>{prompt}</div>', unsafe_allow_html=True)

    with st.chat_message("assistant"):
        if st.session_state.interview_phase == "not_started":
            # Start the interview
            st.session_state.initial_tech_stack = prompt
            st.session_state.conversation_history += f"Initial tech stack: {prompt}\n\n"
            
            with st.spinner("🤖 Security expert is preparing interview questions..."):
                result = start_interview(
                    prompt,
                    api_key or os.getenv("GEMINI_API_KEY"),
                    serper_key or os.getenv("SERPER_API_KEY")
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("message", ""),
                    "analysis_data": result
                })
                
                if result["status"] == "success":
                    st.session_state.interview_phase = "interviewing"
                    st.session_state.conversation_history += f"Interviewer: {result['message']}\n\n"
                
        elif st.session_state.interview_phase == "interviewing":
            # Continue the interview
            st.session_state.conversation_history += f"User: {prompt}\n\n"
            
            with st.spinner("🤖 Processing your response..."):
                result = continue_interview(
                    prompt,
                    st.session_state.conversation_history,
                    api_key or os.getenv("GEMINI_API_KEY"),
                    serper_key or os.getenv("SERPER_API_KEY")
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result.get("message", ""),
                    "analysis_data": result
                })
                
                if result["status"] == "success":
                    message = result["message"]
                    st.session_state.conversation_history += f"Interviewer: {message}\n\n"
                    
                    if "Complete Technology Profile" in message or "📋 Complete Technology Profile" in message:
                        st.session_state.interview_phase = "ready_for_analysis"

                    if any(phrase in message.lower() for phrase in [
                        "thank you for the information",
                        "that completes our interview",
                        "ready to proceed with the analysis",
                        "i have enough information",
                        "ready for analysis"
                    ]):
                        st.session_state.interview_phase = "ready_for_analysis"
        
        elif st.session_state.interview_phase == "completed":
            st.markdown(f'<div class="chat-message interviewer-message"><strong>🤖 Security Expert:</strong><br>Thank you for your question: "{prompt}". For detailed follow-up analysis, please start a new session or refer to the comprehensive analysis above.</div>', unsafe_allow_html=True)
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": f"Thank you for your question: '{prompt}'. For detailed follow-up analysis, please start a new session or refer to the comprehensive analysis above."
            })
    st.rerun()