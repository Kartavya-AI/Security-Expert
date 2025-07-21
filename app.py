import streamlit as st
from src.security_expert.crew import SecurityExpertCrew
from dotenv import load_dotenv
import os
import time
from datetime import datetime
import re
import uuid

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

    .memory-context {
        background: #2a2a3a;
        border-left: 4px solid #ffc107;
        color: #fff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
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

    .memory-stats {
        background: #2a2a3a;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }

    .session-info {
        background: #1a1a2a;
        padding: 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        color: #ccc;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Logic --------------------
def run_security_crew(tech_stack: str, api_key: str = None, session_id: str = None) -> dict:
    try:
        crew = SecurityExpertCrew(api_key=api_key, session_id=session_id)
        result = crew.run_analysis(tech_stack)
        return result
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

def get_memory_stats(session_id: str = None) -> dict:
    """Get memory statistics for display"""
    try:
        from src.security_expert.crew import SecurityMemoryManager
        memory_manager = SecurityMemoryManager()
        
        # Get conversation count for current session
        history = memory_manager.get_conversation_history(session_id or "", limit=100)
        
        # Get total insights count
        insights = memory_manager.get_security_insights()
        
        # Get similar analyses count (using a common tech stack)
        similar = memory_manager.get_similar_analyses("web app", limit=100)
        
        return {
            "session_conversations": len(history),
            "total_insights": len(insights),
            "total_analyses": len(similar)
        }
    except Exception:
        return {
            "session_conversations": 0,
            "total_insights": 0,
            "total_analyses": 0
        }

# -------------------- State Init --------------------
if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quick_input" not in st.session_state:
    st.session_state.quick_input = ""
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "show_memory_context" not in st.session_state:
    st.session_state.show_memory_context = False

# -------------------- Main Header --------------------
st.markdown("""
<div class="main-header">
    <h1>🛡️ AI Security Expert</h1>
    <p>Advanced Security Analysis with Memory-Enhanced Intelligence</p>
</div>
""", unsafe_allow_html=True)

# -------------------- Sidebar --------------------
with st.sidebar:
    st.markdown('<div class="section-header">🔧 Configuration</div>', unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key", type="password", key="gemini_key", placeholder="Enter API key...")
    serper_key = st.text_input("Serper API Key (Optional)", type="password", key="serper_key", placeholder="Enter Serper key...")

    # Session info
    st.markdown('<div class="section-header">📱 Session Info</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="session-info">Session ID: {st.session_state.session_id}</div>', unsafe_allow_html=True)
    
    # Memory toggle
    st.session_state.show_memory_context = st.checkbox("🧠 Show Memory Context", value=st.session_state.show_memory_context)
    
    # Memory statistics
    st.markdown('<div class="section-header">🧠 Memory Stats</div>', unsafe_allow_html=True)
    memory_stats = get_memory_stats(st.session_state.session_id)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-card">{memory_stats["session_conversations"]}<br><small>Session</small></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card">{memory_stats["total_insights"]}<br><small>Insights</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">{st.session_state.analysis_count}<br><small>Current</small></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card">{memory_stats["total_analyses"]}<br><small>Historical</small></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">🚀 Quick Actions</div>', unsafe_allow_html=True)
    if st.button("🌐 Web App Stack"): 
        st.session_state.quick_input = "React frontend with Node.js Express backend, MongoDB database, deployed on AWS EC2 with S3 for file storage"
    if st.button("📱 Mobile App Stack"): 
        st.session_state.quick_input = "Flutter app with Firebase backend"
    if st.button("☁️ Cloud Native Stack"): 
        st.session_state.quick_input = "Docker + Kubernetes + PostgreSQL + Redis on GCP"
    if st.button("🧠 Deep Learning Stack"): 
        st.session_state.quick_input = "PyTorch + HuggingFace Transformers + FastAPI + Docker + NVIDIA GPU"
    
    st.markdown("---")
    
    # Memory management buttons
    st.markdown('<div class="section-header">🗂️ Memory Management</div>', unsafe_allow_html=True)
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.session_state.analysis_count = 0
        st.rerun()
    
    if st.button("🗑️ Clear Current Chat"):
        st.session_state.messages = []
        st.session_state.analysis_count = 0
        st.rerun()

    # Memory insights preview
    if st.button("👁️ View Memory Insights"):
        try:
            from src.security_expert.crew import SecurityMemoryManager
            memory_manager = SecurityMemoryManager()
            insights = memory_manager.get_security_insights()[:5]
            
            if insights:
                st.markdown("**Recent Security Insights:**")
                for tech, vuln, risk, rec, freq in insights:
                    st.markdown(f"• **{tech}** ({freq}x): {vuln[:30]}...")
            else:
                st.info("No security insights stored yet.")
        except Exception as e:
            st.error(f"Error loading insights: {str(e)}")

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
                    # Show session info
                    session_info = f"Session: {data.get('session_id', 'N/A')} | {data['timestamp']}"
                    st.markdown(f'<div class="chat-message analysis-result"><strong>🛡️ Security Expert (Memory-Enhanced):</strong><br><em>Stack:</em> {data["tech_stack"]}<br><small>{session_info}</small></div>', unsafe_allow_html=True)
                    
                    # Show memory context if enabled
                    if st.session_state.show_memory_context:
                        analysis_text = data["analysis"]
                        if "Previous Similar Analyses:" in analysis_text or "Relevant Security Insights" in analysis_text:
                            memory_start = analysis_text.find("## Previous Similar Analyses:")
                            memory_end = analysis_text.find("## Current Analysis Request:")
                            if memory_start != -1 and memory_end != -1:
                                memory_context = analysis_text[memory_start:memory_end].strip()
                                st.markdown(f'<div class="memory-context"><strong>🧠 Memory Context Used:</strong><br>{memory_context}</div>', unsafe_allow_html=True)
                    
                    # Parse and display main analysis
                    main_analysis = data["analysis"]
                    if "## Current Analysis Request:" in main_analysis:
                        main_analysis = main_analysis.split("## Current Analysis Request:")[-1].strip()
                    
                    parsed = parse_report(main_analysis)
                    if len(parsed) > 1:
                        tabs = st.tabs([f"📄 {k}" for k in parsed])
                        for tab, content in zip(tabs, parsed.values()):
                            with tab: 
                                st.markdown(f'<div class="card">{content}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="card">{main_analysis}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-message error-result"><strong>Error:</strong><br>{data["error"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message"><strong>Security Expert:</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)

# -------------------- Prompt Input --------------------
prompt = st.session_state.quick_input if st.session_state.quick_input else st.chat_input("💬 Describe your tech stack for security analysis...")
st.session_state.quick_input = ""

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.empty():
        st.markdown(f'''
        <div class="chat-message status-analyzing">
            🔄 Analyzing <code>{prompt}</code> with memory enhancement...
            <br><small>Session: {st.session_state.session_id}</small>
        </div>
        ''', unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulated progress with status updates
        stages = [
            "🧠 Loading memory context...",
            "🔍 Analyzing similar past cases...",
            "⚡ Running security analysis...",
            "📊 Generating insights...",
            "💾 Storing results in memory..."
        ]
        
        for i, stage in enumerate(stages):
            status_text.text(stage)
            for j in range(20):
                progress_bar.progress((i * 20 + j + 1))
                time.sleep(0.01)

        data = run_security_crew(prompt, api_key or None, st.session_state.session_id)
        
        progress_bar.empty()
        status_text.empty()
        
        if data["status"] == "success":
            st.session_state.analysis_count += 1
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": data.get("analysis", ""),
            "analysis_data": data
        })
    st.rerun()