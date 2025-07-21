import os
import sqlite3
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.memory import ShortTermMemory, LongTermMemory
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import hashlib
import json

load_dotenv()

class SecurityMemoryManager:
    """
    Custom memory manager for security analysis history using SQLite
    """
    def __init__(self, db_path: str = "security_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for storing conversation history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                tech_stack TEXT,
                tech_stack_hash TEXT,
                analysis_result TEXT,
                risks TEXT,
                recommendations TEXT,
                timestamp DATETIME,
                user_feedback TEXT
            )
        ''')
        
        # Table for storing security patterns and insights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                technology TEXT,
                vulnerability_type TEXT,
                risk_level TEXT,
                recommendation TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen DATETIME,
                created_at DATETIME
            )
        ''')
        
        # Table for storing user preferences and context
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                preference_key TEXT,
                preference_value TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def generate_tech_stack_hash(self, tech_stack: str) -> str:
        """Generate hash for tech stack to identify similar queries"""
        return hashlib.md5(tech_stack.lower().strip().encode()).hexdigest()
    
    def store_conversation(self, session_id: str, tech_stack: str, analysis_result: str, 
                         risks: list = None, recommendations: list = None):
        """Store conversation in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tech_stack_hash = self.generate_tech_stack_hash(tech_stack)
        
        cursor.execute('''
            INSERT INTO conversations 
            (session_id, tech_stack, tech_stack_hash, analysis_result, risks, recommendations, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            tech_stack,
            tech_stack_hash,
            analysis_result,
            json.dumps(risks) if risks else None,
            json.dumps(recommendations) if recommendations else None,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_similar_analyses(self, tech_stack: str, limit: int = 3) -> list:
        """Retrieve similar past analyses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tech_stack_hash = self.generate_tech_stack_hash(tech_stack)
        
        # First, try exact match
        cursor.execute('''
            SELECT tech_stack, analysis_result, risks, recommendations, timestamp
            FROM conversations 
            WHERE tech_stack_hash = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (tech_stack_hash, limit))
        
        exact_matches = cursor.fetchall()
        
        if exact_matches:
            conn.close()
            return exact_matches
        
        # If no exact match, find similar tech stacks using keywords
        keywords = tech_stack.lower().split()
        similar_analyses = []
        
        for keyword in keywords[:3]:  # Use top 3 keywords
            cursor.execute('''
                SELECT tech_stack, analysis_result, risks, recommendations, timestamp
                FROM conversations 
                WHERE LOWER(tech_stack) LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (f'%{keyword}%', limit))
            
            results = cursor.fetchall()
            similar_analyses.extend(results)
        
        conn.close()
        
        # Remove duplicates and limit results
        seen = set()
        unique_analyses = []
        for analysis in similar_analyses:
            if analysis[0] not in seen:  # tech_stack as identifier
                seen.add(analysis[0])
                unique_analyses.append(analysis)
                if len(unique_analyses) >= limit:
                    break
        
        return unique_analyses
    
    def store_security_insight(self, technology: str, vulnerability_type: str, 
                             risk_level: str, recommendation: str):
        """Store security insights for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if insight already exists
        cursor.execute('''
            SELECT id, frequency FROM security_insights 
            WHERE technology = ? AND vulnerability_type = ? AND risk_level = ?
        ''', (technology, vulnerability_type, risk_level))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update frequency and last_seen
            cursor.execute('''
                UPDATE security_insights 
                SET frequency = frequency + 1, last_seen = ?, recommendation = ?
                WHERE id = ?
            ''', (datetime.now(), recommendation, existing[0]))
        else:
            # Insert new insight
            cursor.execute('''
                INSERT INTO security_insights 
                (technology, vulnerability_type, risk_level, recommendation, last_seen, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (technology, vulnerability_type, risk_level, recommendation, 
                  datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_security_insights(self, technology: str = None) -> list:
        """Retrieve relevant security insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if technology:
            cursor.execute('''
                SELECT technology, vulnerability_type, risk_level, recommendation, frequency
                FROM security_insights 
                WHERE technology LIKE ?
                ORDER BY frequency DESC, last_seen DESC
                LIMIT 10
            ''', (f'%{technology}%',))
        else:
            cursor.execute('''
                SELECT technology, vulnerability_type, risk_level, recommendation, frequency
                FROM security_insights 
                ORDER BY frequency DESC, last_seen DESC
                LIMIT 20
            ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """Get recent conversation history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tech_stack, analysis_result, timestamp
            FROM conversations 
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results

@CrewBase
class SecurityExpertCrew:
    """
    Enhanced SecurityExpertCrew with memory capabilities
    """
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, api_key: str = None, serper_key: str = None, session_id: str = None):
        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        serper_api_key = serper_key or os.getenv("SERPER_API_KEY")
        if not gemini_key:
            raise ValueError("No Gemini API Key found")

        self.llm = LLM(model="gemini/gemini-2.0-flash-exp", api_key=api_key)
        self.search_tool = None
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize memory manager
        self.memory_manager = SecurityMemoryManager()
        
        # Initialize CrewAI memory components
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()
        
        if serper_api_key:
            try:
                self.search_tool = SerperDevTool()
            except Exception:
                self.search_tool = None

    def enhance_prompt_with_memory(self, tech_stack: str) -> str:
        """Enhance the analysis prompt with relevant memory context"""
        context_parts = []
        
        # Get similar past analyses
        similar_analyses = self.memory_manager.get_similar_analyses(tech_stack, limit=2)
        if similar_analyses:
            context_parts.append("## Previous Similar Analyses:")
            for i, (past_stack, past_result, _, _, timestamp) in enumerate(similar_analyses, 1):
                context_parts.append(f"**Analysis {i} ({timestamp}):**")
                context_parts.append(f"Stack: {past_stack}")
                context_parts.append(f"Key insights from previous analysis: {past_result[:200]}...")
                context_parts.append("---")
        
        # Get relevant security insights
        # Extract main technologies from tech stack
        tech_keywords = []
        common_techs = ['react', 'node', 'python', 'docker', 'kubernetes', 'aws', 'mongodb', 
                       'postgresql', 'redis', 'nginx', 'apache', 'mysql', 'firebase', 'flutter']
        
        for tech in common_techs:
            if tech.lower() in tech_stack.lower():
                tech_keywords.append(tech)
        
        if tech_keywords:
            insights = []
            for tech in tech_keywords[:3]:  # Limit to 3 technologies
                tech_insights = self.memory_manager.get_security_insights(tech)
                insights.extend(tech_insights[:2])  # Get top 2 insights per tech
            
            if insights:
                context_parts.append("## Relevant Security Insights from Past Analyses:")
                for tech, vuln_type, risk_level, recommendation, frequency in insights:
                    context_parts.append(f"- **{tech}** ({vuln_type}, {risk_level}): {recommendation} (seen {frequency}x)")
        
        # Get recent conversation history
        history = self.memory_manager.get_conversation_history(self.session_id, limit=3)
        if history:
            context_parts.append("## Recent Analysis History:")
            for past_stack, past_result, timestamp in history:
                context_parts.append(f"- **{timestamp}**: {past_stack} → Key findings: {past_result[:150]}...")
        
        if context_parts:
            memory_context = "\n".join(context_parts)
            enhanced_prompt = f"""
{memory_context}

## Current Analysis Request:
Technology Stack: {tech_stack}

Based on the above context and your expertise, provide a comprehensive security analysis. 
Consider patterns from similar past analyses but focus on the specific current stack.
If you notice recurring issues from the memory context, emphasize those in your analysis.
"""
            return enhanced_prompt
        
        return tech_stack

    def store_analysis_results(self, tech_stack: str, analysis_result: str):
        """Store analysis results for future reference"""
        # Parse the analysis result to extract risks and recommendations
        risks = []
        recommendations = []
        
        lines = analysis_result.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if '🚨 Top 3 Critical Risks' in line:
                current_section = 'risks'
            elif '✅ Top 3 Recommendations' in line:
                current_section = 'recommendations'
            elif line.startswith(('1.', '2.', '3.')) and current_section:
                if current_section == 'risks':
                    risks.append(line)
                elif current_section == 'recommendations':
                    recommendations.append(line)
        
        # Store conversation
        self.memory_manager.store_conversation(
            self.session_id, tech_stack, analysis_result, risks, recommendations
        )
        
        # Extract and store security insights
        # This is a simplified extraction - in production, you might want more sophisticated parsing
        for risk in risks:
            if ':' in risk:
                risk_desc = risk.split(':', 1)[1].strip()
                # Extract technology and vulnerability type (simplified)
                tech_words = ['sql', 'xss', 'csrf', 'authentication', 'authorization', 
                             'encryption', 'docker', 'kubernetes', 'aws', 'database']
                
                for tech in tech_words:
                    if tech in risk_desc.lower():
                        self.memory_manager.store_security_insight(
                            technology=tech,
                            vulnerability_type=risk_desc[:50],
                            risk_level="High",  # Default, could be enhanced with parsing
                            recommendation="See full analysis for details"
                        )

    @agent
    def security_analyst(self) -> Agent:
        tools = []
        if self.search_tool:
            tools.append(self.search_tool)
            
        return Agent(
            config=self.agents_config['security_analyst'],
            llm=self.llm,
            tools=tools,
            memory=self.short_term_memory,
            verbose=True
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
            agent=self.security_analyst()
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.security_analyst()],
            tasks=[self.analysis_task()],
            process=Process.sequential,
            memory=self.long_term_memory,
            verbose=True
        )
    
    def run_analysis(self, tech_stack: str) -> dict:
        """Run security analysis with memory enhancement"""
        try:
            # Enhance prompt with memory context
            enhanced_tech_stack = self.enhance_prompt_with_memory(tech_stack)
            
            inputs = {'tech_stack_description': enhanced_tech_stack}
            result = self.crew().kickoff(inputs=inputs)
            
            # Store results for future memory
            self.store_analysis_results(tech_stack, str(result))
            
            return {
                "status": "success",
                "analysis": str(result),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tech_stack": tech_stack,
                "session_id": self.session_id
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tech_stack": tech_stack,
                "session_id": self.session_id
            }