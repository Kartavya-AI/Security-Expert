import sqlite3
import os
from datetime import datetime, timedelta
import json
import hashlib

def init_security_memory_db(db_path="security_memory.db"):
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    print(f"Creating new database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables without inline INDEX definitions
    cursor.execute('''
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            tech_stack_hash TEXT NOT NULL,
            analysis_result TEXT NOT NULL,
            risks TEXT,
            recommendations TEXT,
            timestamp DATETIME NOT NULL,
            user_feedback TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE security_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technology TEXT NOT NULL,
            vulnerability_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            frequency INTEGER DEFAULT 1,
            last_seen DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE user_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            preference_key TEXT NOT NULL,
            preference_value TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE analysis_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            pattern_description TEXT,
            tech_keywords TEXT NOT NULL,
            common_risks TEXT NOT NULL,
            recommended_solutions TEXT NOT NULL,
            pattern_score REAL DEFAULT 1.0,
            times_matched INTEGER DEFAULT 1,
            last_matched DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        )
    ''')

    # Create indexes separately
    print("Creating indexes...")
    cursor.execute('CREATE INDEX idx_conv_session_id ON conversations (session_id)')
    cursor.execute('CREATE INDEX idx_conv_tech_stack_hash ON conversations (tech_stack_hash)')
    cursor.execute('CREATE INDEX idx_conv_timestamp ON conversations (timestamp)')
    
    cursor.execute('CREATE INDEX idx_si_technology ON security_insights (technology)')
    cursor.execute('CREATE INDEX idx_si_risk_level ON security_insights (risk_level)')
    cursor.execute('CREATE INDEX idx_si_frequency ON security_insights (frequency)')
    
    cursor.execute('CREATE INDEX idx_uc_session_id ON user_context (session_id)')
    cursor.execute('CREATE INDEX idx_uc_preference_key ON user_context (preference_key)')

    cursor.execute('CREATE INDEX idx_ap_pattern_name ON analysis_patterns (pattern_name)')
    cursor.execute('CREATE INDEX idx_ap_pattern_score ON analysis_patterns (pattern_score)')

    print("Database tables and indexes created successfully!")
    
    # --- The rest of the function for inserting sample data remains the same ---
    
    sample_insights = [
        ("react", "XSS Vulnerability", "High", "Implement Content Security Policy (CSP) headers", 5),
        ("nodejs", "Dependency Vulnerabilities", "High", "Regular npm audit and dependency updates", 8),
        ("mongodb", "NoSQL Injection", "Medium", "Input validation and parameterized queries", 3),
        ("docker", "Container Escape", "High", "Use non-root users and security contexts", 6),
        ("aws", "S3 Bucket Misconfiguration", "High", "Enable bucket policies and access logging", 4),
        ("kubernetes", "RBAC Misconfiguration", "High", "Implement least-privilege RBAC policies", 7),
        ("postgresql", "SQL Injection", "High", "Use prepared statements and input validation", 9),
        ("firebase", "Insecure Rules", "Medium", "Review and tighten Firestore security rules", 2),
        ("nginx", "Server Information Disclosure", "Low", "Hide server version and configure headers", 3),
        ("redis", "Unauthorized Access", "High", "Enable authentication and network security", 4)
    ]
    
    base_time = datetime.now() - timedelta(days=30)
    
    for i, (tech, vuln, risk, rec, freq) in enumerate(sample_insights):
        cursor.execute('''
            INSERT INTO security_insights 
            (technology, vulnerability_type, risk_level, recommendation, frequency, last_seen, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            tech, vuln, risk, rec, freq,
            base_time + timedelta(days=i*2),
            base_time + timedelta(days=i*2)
        ))
    
    sample_patterns = [
        (
            "MEAN Stack",
            "Common security issues in MongoDB, Express, Angular, Node.js stack",
            "mongodb,express,angular,nodejs,mean",
            json.dumps(["NoSQL Injection", "XSS", "CSRF", "Dependency Vulnerabilities"]),
            json.dumps(["Input validation", "CSP headers", "CSRF tokens", "Regular updates"]),
            0.9
        ),
        (
            "Docker Containerization",
            "Security concerns in containerized applications",
            "docker,container,containerization",
            json.dumps(["Container Escape", "Privilege Escalation", "Image Vulnerabilities"]),
            json.dumps(["Non-root users", "Security contexts", "Image scanning"]),
            0.95
        ),
        (
            "Cloud AWS Deployment",
            "Common AWS security misconfigurations",
            "aws,ec2,s3,lambda,cloud",
            json.dumps(["S3 Misconfiguration", "IAM Over-permissions", "Network Exposure"]),
            json.dumps(["Bucket policies", "Least privilege IAM", "VPC configuration"]),
            0.85
        )
    ]
    
    for pattern_name, desc, keywords, risks, solutions, score in sample_patterns:
        cursor.execute('''
            INSERT INTO analysis_patterns
            (pattern_name, pattern_description, tech_keywords, common_risks, 
             recommended_solutions, pattern_score, times_matched, last_matched, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern_name, desc, keywords, risks, solutions, score, 
            3, datetime.now() - timedelta(days=5), datetime.now() - timedelta(days=20)
        ))
    
    sample_conversations = [
        {
            "session_id": "demo_001",
            "tech_stack": "React frontend with Node.js backend and MongoDB",
            "analysis": "## Executive Summary\nMEAN stack with moderate security posture...",
            "risks": ["XSS vulnerabilities", "NoSQL injection", "Dependency issues"],
            "recommendations": ["Implement CSP", "Input validation", "Update dependencies"]
        },
        {
            "session_id": "demo_002", 
            "tech_stack": "Docker containerized Python Flask app on AWS",
            "analysis": "## Executive Summary\nContainerized Flask application with cloud deployment...",
            "risks": ["Container escape", "S3 misconfiguration", "Flask debug mode"],
            "recommendations": ["Disable debug", "Bucket policies", "Security contexts"]
        }
    ]
    
    for i, conv in enumerate(sample_conversations):
        tech_hash = hashlib.md5(conv["tech_stack"].lower().encode()).hexdigest()
        cursor.execute('''
            INSERT INTO conversations
            (session_id, tech_stack, tech_stack_hash, analysis_result, risks, recommendations, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            conv["session_id"],
            conv["tech_stack"],
            tech_hash,
            conv["analysis"],
            json.dumps(conv["risks"]),
            json.dumps(conv["recommendations"]),
            datetime.now() - timedelta(days=10+i*5)
        ))
    
    conn.commit()
    print(f"Sample data inserted successfully!")
    print(f"Database initialized with:")
    print(f"- {len(sample_insights)} security insights")
    print(f"- {len(sample_patterns)} analysis patterns")
    print(f"- {len(sample_conversations)} sample conversations")
    cursor.execute("SELECT COUNT(*) FROM security_insights")
    insights_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversations")
    conv_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM analysis_patterns")
    patterns_count = cursor.fetchone()[0]
    
    print(f"\nVerification:")
    print(f"- Security insights: {insights_count} records")
    print(f"- Conversations: {conv_count} records") 
    print(f"- Analysis patterns: {patterns_count} records")
    
    conn.close()
    print(f"\nDatabase setup complete! File: {os.path.abspath(db_path)}")


def reset_database():
    print("Resetting Security Memory Database...")
    init_security_memory_db()

if __name__ == "__main__":
    print("🛡️ Security Expert Memory Database Initialization")
    choice = input("Choose an option:\n1. Initialize new database\n2. Reset existing database\nEnter choice (1 or 2): ")
    if choice == "1":
        init_security_memory_db()
    elif choice == "2":
        reset_database()
    else:
        print("Invalid choice. Initializing new database...")
        init_security_memory_db()
    
    print("\n✅ Database setup completed successfully!")
    print("You can now run your Streamlit app with memory functionality.")