import os
import sqlite3
import json
import asyncio
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging
import structlog
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, field_validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import psutil
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from src.security_expert.crew import SecurityExpertCrew

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
CREW_EXECUTION_COUNT = Counter('crew_executions_total', 'Total crew executions', ['action', 'status'])
CREW_EXECUTION_DURATION = Histogram('crew_execution_duration_seconds', 'Crew execution duration')

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Database and logging setup
DB_FILE = os.getenv("DATABASE_FILE", "security_analysis.db")
LOG_FILE = "application.log"

class DatabaseManager:
    """Thread-safe database operations with connection pooling"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._init_db()
    
    def _init_db(self):
        """Initialize database with proper schema"""
        try:
            with sqlite3.connect(self.db_file, timeout=30) as conn:
                conn.execute('PRAGMA journal_mode=WAL')  # Better concurrent access
                conn.execute('PRAGMA synchronous=NORMAL')  # Better performance
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        tech_stack TEXT NOT NULL,
                        interview_results TEXT,
                        analysis_summary TEXT NOT NULL,
                        analysis_type TEXT DEFAULT 'comprehensive',
                        status TEXT DEFAULT 'completed',
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_session_id ON analysis_history(session_id)
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON analysis_history(timestamp)
                ''')
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def add_analysis(self, session_id: str, tech_stack: str, interview_results: str, 
                    summary: str, analysis_type: str = 'comprehensive', status: str = 'completed'):
        """Add analysis to database with retry logic"""
        try:
            with sqlite3.connect(self.db_file, timeout=30) as conn:
                conn.execute('''
                    INSERT INTO analysis_history 
                    (session_id, tech_stack, interview_results, analysis_summary, analysis_type, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, tech_stack, interview_results, summary, analysis_type, status, datetime.now()))
                conn.commit()
                logger.info("Analysis saved to database", session_id=session_id)
        except Exception as e:
            logger.error("Failed to save analysis", session_id=session_id, error=str(e))
            raise

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get analysis history for a session"""
        try:
            with sqlite3.connect(self.db_file, timeout=30) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT tech_stack, interview_results, analysis_summary, analysis_type, 
                           status, timestamp, created_at 
                    FROM analysis_history 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (session_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to fetch history", session_id=session_id, error=str(e))
            return []

db_manager = DatabaseManager()

# Pydantic models with enhanced validation (V2 syntax)
class TechStackRequest(BaseModel):
    tech_stack: str = Field(..., min_length=1, max_length=2000, description="Technology stack description")
    
    @field_validator('tech_stack')
    @classmethod
    def validate_tech_stack(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Technology stack cannot be empty')
        return v.strip()

class InterviewRequest(BaseModel):
    user_response: str = Field(..., min_length=1, max_length=5000, description="User response to interview question")
    conversation_history: str = Field(default="", max_length=50000, description="Conversation history")
    
    @field_validator('user_response')
    @classmethod
    def validate_response(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('User response cannot be empty')
        return v.strip()

class AnalysisRequest(BaseModel):
    conversation_history: str = Field(..., min_length=1, max_length=50000, description="Complete conversation history")
    session_id: str = Field(..., min_length=1, max_length=100, description="Session identifier")
    tech_stack: str = Field(..., min_length=1, max_length=2000, description="Technology stack")
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Session ID cannot be empty')
        return v.strip()

class HistoryResponse(BaseModel):
    status: str
    history: List[Dict[str, Any]]
    total_count: int

class APIResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class CrewManager:
    """Manages crew instances with proper error handling and retries"""
    
    def __init__(self):
        self._crew_instance: Optional[SecurityExpertCrew] = None
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
    
    def _health_check(self) -> bool:
        """Check if crew instance is healthy"""
        current_time = time.time()
        if current_time - self._last_health_check > self._health_check_interval:
            try:
                if self._crew_instance is None:
                    return False
                # Simple health check - try to access the LLM
                _ = self._crew_instance.llm
                self._last_health_check = current_time
                return True
            except Exception as e:
                logger.warning("Crew health check failed", error=str(e))
                self._crew_instance = None
                return False
        return self._crew_instance is not None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_crew_instance(self) -> SecurityExpertCrew:
        """Get or create crew instance with health checking"""
        if not self._health_check():
            logger.info("Creating new crew instance")
            try:
                self._crew_instance = SecurityExpertCrew()
                logger.info("Crew instance created successfully")
            except Exception as e:
                logger.error("Failed to create crew instance", error=str(e))
                raise HTTPException(
                    status_code=503, 
                    detail="Service temporarily unavailable - crew initialization failed"
                )
        return self._crew_instance

crew_manager = CrewManager()

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger.info("🚀 AI Security Expert API starting up...")
    
    # Startup
    try:
        # Initialize database
        db_manager._init_db()
        
        # Pre-warm crew instance
        await asyncio.get_event_loop().run_in_executor(None, crew_manager.get_crew_instance)
        
        # Validate required environment variables
        required_env_vars = ["GEMINI_API_KEY"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")

# FastAPI application setup
app = FastAPI(
    title="AI Security Expert API",
    description="Production-grade Interactive Security Analysis through Comprehensive Requirements Gathering",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    #allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    allowed_hosts=["*"]
)

# CORS middleware - configure for production
app.add_middleware(
    CORSMiddleware,
    #allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","), # Default to empty list for security
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=get_remote_address(request)
    )
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(duration)
    
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=duration
    )
    
    return response

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        url=str(request.url)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        url=str(request.url),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )

# Dependency injection
async def get_crew_instance() -> SecurityExpertCrew:
    """Dependency to get crew instance"""
    return await asyncio.get_event_loop().run_in_executor(
        None, crew_manager.get_crew_instance
    )

# API Routes
@app.get("/", response_class=HTMLResponse, summary="API Landing Page")
async def root() -> HTMLResponse:
    """Landing page with API information"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
        <head>
            <title>AI Security Expert API</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .header { color: #2c3e50; }
                .status { color: #27ae60; font-weight: bold; }
                .links a { margin-right: 15px; text-decoration: none; color: #3498db; }
                .links a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1 class="header">🛡️ AI Security Expert API</h1>
            <p class="status">✅ Service is running</p>
            <p>Production-grade Interactive Security Analysis API powered by AI agents.</p>
            
            <h3>Available Endpoints:</h3>
            <div class="links">
                <a href="/docs">📚 API Documentation</a>
                <a href="/redoc">📖 ReDoc Documentation</a>
                <a href="/health">🏥 Health Check</a>
                <a href="/metrics">📊 Metrics</a>
            </div>
            
            <p><strong>Version:</strong> 2.0.0</p>
        </body>
    </html>
    """)

@app.get("/health", summary="Comprehensive Health Check")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint"""
    try:
        db_healthy = False
        try:
            with sqlite3.connect(DB_FILE, timeout=5) as conn:
                conn.execute("SELECT 1").fetchone()
            db_healthy = True
        except Exception:
            db_healthy = False
        
        crew_healthy = crew_manager._health_check()
        
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        health_status = {
            "status": "healthy" if db_healthy and crew_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "crew_ai": "healthy" if crew_healthy else "unhealthy",
                "memory_usage_percent": memory_usage,
                "disk_usage_percent": disk_usage
            }
        }
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )

@app.get("/metrics", summary="Prometheus Metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/interview/start", 
          summary="Start Security Interview", 
          response_model=APIResponse)
@limiter.limit("10/minute")
async def start_interview(
    request: Request,
    tech_request: TechStackRequest,
    crew: SecurityExpertCrew = Depends(get_crew_instance)
):
    """Start a new security interview session"""
    start_time = time.time()
    try:
        logger.info("Starting interview", tech_stack=tech_request.tech_stack[:100])
        
        inputs = {
            'tech_stack_description': tech_request.tech_stack,
            'action': 'start_interview',
            'conversation_history': ''
        }
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, crew.kickoff, inputs
        )
        
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='start_interview', status='success').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.info("Interview started successfully", duration=duration)
        
        return APIResponse(
            status="success",
            message=str(result),
            data={"type": "interview_question"}
        )
        
    except Exception as e:
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='start_interview', status='error').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.error("Interview start failed", error=str(e), duration=duration, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start interview")

@app.post("/interview/continue", 
          summary="Continue Security Interview", 
          response_model=APIResponse)
@limiter.limit("20/minute")
async def continue_interview(
    request: Request,
    interview_request: InterviewRequest,
    crew: SecurityExpertCrew = Depends(get_crew_instance)
):
    """Continue the interview with user response"""
    start_time = time.time()
    try:
        logger.info("Continuing interview", response_length=len(interview_request.user_response))
        
        inputs = {
            'user_response': interview_request.user_response,
            'conversation_history': interview_request.conversation_history,
            'action': 'continue_interview'
        }
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, crew.kickoff, inputs
        )
        
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='continue_interview', status='success').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.info("Interview continued successfully", duration=duration)
        
        return APIResponse(
            status="success",
            message=str(result),
            data={"type": "interview_question"}
        )
        
    except Exception as e:
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='continue_interview', status='error').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.error("Interview continuation failed", error=str(e), duration=duration, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to continue interview")

@app.post("/analysis/perform", 
          summary="Perform Security Analysis", 
          response_model=APIResponse)
@limiter.limit("5/minute")
async def perform_analysis(
    request: Request,
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    crew: SecurityExpertCrew = Depends(get_crew_instance)
):
    """Perform comprehensive security analysis"""
    start_time = time.time()
    try:
        logger.info("Starting analysis", session_id=analysis_request.session_id)
        
        inputs = {
            'conversation_history': analysis_request.conversation_history,
            'action': 'perform_analysis'
        }
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, crew.kickoff, inputs
        )
        
        background_tasks.add_task(
            db_manager.add_analysis,
            analysis_request.session_id,
            analysis_request.tech_stack,
            analysis_request.conversation_history,
            str(result)
        )
        
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='perform_analysis', status='success').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.info("Analysis completed successfully", session_id=analysis_request.session_id, duration=duration)
        
        return APIResponse(
            status="success",
            message=str(result),
            data={
                "type": "final_analysis", 
                "session_id": analysis_request.session_id,
                "analysis_length": len(str(result))
            }
        )
        
    except Exception as e:
        duration = time.time() - start_time
        CREW_EXECUTION_COUNT.labels(action='perform_analysis', status='error').inc()
        CREW_EXECUTION_DURATION.observe(duration)
        
        logger.error("Analysis failed", session_id=analysis_request.session_id, error=str(e), duration=duration, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform analysis")

@app.get("/history/{session_id}", 
         response_model=HistoryResponse, 
         summary="Get Analysis History")
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    session_id: str,
    limit: int = 50
) -> HistoryResponse:
    """Get analysis history for a session"""
    try:
        if not session_id.strip():
            raise HTTPException(status_code=400, detail="Session ID cannot be empty")
        
        limit = min(limit, 100) # Cap limit at 100
            
        logger.info("Fetching history", session_id=session_id, limit=limit)
        
        history = await asyncio.get_event_loop().run_in_executor(
            None, db_manager.get_history, session_id, limit
        )
        
        return HistoryResponse(
            status="success",
            history=history,
            total_count=len(history)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch history", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch history")

@app.get("/sessions", response_model=APIResponse, summary="Get Active Sessions")
@limiter.limit("10/minute")
async def get_sessions(request: Request):
    """Get list of recent sessions from the last 7 days"""
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT session_id, MAX(timestamp) as last_activity, COUNT(*) as analysis_count
                FROM analysis_history 
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY session_id 
                ORDER BY last_activity DESC 
                LIMIT 100
            ''')
            sessions = [dict(row) for row in cursor.fetchall()]
            
        return APIResponse(
            status="success",
            data={"sessions": sessions, "count": len(sessions)}
        )
        
    except Exception as e:
        logger.error("Failed to fetch sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        log_level="info",
        reload=True # Recommended for development
    )
