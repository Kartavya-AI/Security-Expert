from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

from src.security_expert.crew import SecurityExpertCrew

load_dotenv()

app = FastAPI(
    title="AI Security Expert API",
    description="Interactive Security Analysis through Comprehensive Requirements Gathering",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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

def add_analysis_to_db(session_id: str, tech_stack: str, interview_results: str, summary: str, analysis_type: str = 'comprehensive'):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analysis_history (session_id, tech_stack, interview_results, analysis_summary, analysis_type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, tech_stack, interview_results, summary, analysis_type, datetime.now()))
    conn.commit()
    conn.close()

def get_history_from_db(session_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT tech_stack, interview_results, analysis_summary, analysis_type, timestamp FROM analysis_history WHERE session_id = ? ORDER BY timestamp DESC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def log_error(error_details: Dict[str, Any]):
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

class TechStackRequest(BaseModel):
    tech_stack: str

class InterviewRequest(BaseModel):
    user_response: str
    conversation_history: str

class AnalysisRequest(BaseModel):
    conversation_history: str
    session_id: str
    tech_stack: str

class HistoryResponse(BaseModel):
    status: str
    history: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    print("🚀 AI Security Expert API starting up...")
    init_db()

@app.get("/", response_class=HTMLResponse, summary="API Landing Page")
async def root() -> HTMLResponse:
    return HTMLResponse("""
    <html>
        <head>
            <title>AI Security Expert API</title>
        </head>
        <body>
            <h1>🛡️ AI Security Expert API</h1>
            <p>Interactive Security Analysis API</p>
            <p>Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """)

@app.get("/health", summary="Health Check")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def get_crew_instance() -> SecurityExpertCrew:
    return SecurityExpertCrew()

@app.post("/interview/start", summary="Start Security Interview")
async def start_interview(request: TechStackRequest):
    try:
        crew = get_crew_instance()
        inputs = {
            'tech_stack_description': request.tech_stack,
            'action': 'start_interview'
        }
        result = crew.kickoff(inputs=inputs)
        return {
            "status": "success",
            "message": str(result),
            "type": "interview_question"
        }
    except Exception as e:
        error_info = {"error": str(e), "timestamp": datetime.now().isoformat()}
        log_error(error_info)
        raise HTTPException(status_code=500, detail=error_info)

@app.post("/interview/continue", summary="Continue Security Interview")
async def continue_interview(request: InterviewRequest):
    try:
        crew = get_crew_instance()
        inputs = {
            'user_response': request.user_response,
            'conversation_history': request.conversation_history,
            'action': 'continue_interview'
        }
        result = crew.kickoff(inputs=inputs)
        return {
            "status": "success",
            "message": str(result),
            "type": "interview_question"
        }
    except Exception as e:
        error_info = {"error": str(e), "timestamp": datetime.now().isoformat()}
        log_error(error_info)
        raise HTTPException(status_code=500, detail=error_info)

@app.post("/analysis/perform", summary="Perform Security Analysis")
async def perform_analysis(request: AnalysisRequest):
    try:
        crew = get_crew_instance()
        inputs = {
            'conversation_history': request.conversation_history,
            'action': 'perform_analysis'
        }
        result = crew.kickoff(inputs=inputs)
        add_analysis_to_db(
            session_id=request.session_id,
            tech_stack=request.tech_stack,
            interview_results=request.conversation_history,
            summary=str(result)
        )
        
        return {
            "status": "success",
            "analysis": str(result),
            "type": "final_analysis"
        }
    except Exception as e:
        error_info = {"error": str(e), "timestamp": datetime.now().isoformat()}
        log_error(error_info)
        raise HTTPException(status_code=500, detail=error_info)

@app.get("/history/{session_id}", response_model=HistoryResponse, summary="Get Analysis History")
async def get_history(session_id: str) -> Dict[str, Any]:
    try:
        history = get_history_from_db(session_id)
        return {"status": "success", "history": history}
    except Exception as e:
        error_info = {"error": str(e), "timestamp": datetime.now().isoformat()}
        log_error(error_info)
        raise HTTPException(status_code=500, detail=error_info)