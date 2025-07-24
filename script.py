import sqlite3
import os
from datetime import datetime

DB_FILE = "security_analysis.db"

def init_db():
    """Initializes the database and creates the analysis table if it doesn't exist."""
    if os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' already exists.")
    else:
        print(f"Creating a new database file: '{DB_FILE}'")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_stack TEXT NOT NULL,
            analysis_summary TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')

    print("Database and 'analysis_history' table are ready.")
    conn.commit()
    conn.close()

def add_analysis(tech_stack, summary):
    """Adds a new analysis record to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO analysis_history (tech_stack, analysis_summary, timestamp)
        VALUES (?, ?, ?)
    ''', (tech_stack, summary, datetime.now()))

    conn.commit()
    print(f"Successfully added analysis for: {tech_stack}")
    conn.close()

def view_history():
    """Prints all records from the analysis_history table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, tech_stack, analysis_summary, timestamp FROM analysis_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    if not rows:
        print("No analysis history found.")
    else:
        print("\n--- Analysis History ---")
        for row in rows:
            print(f"ID: {row[0]}, Stack: {row[1]}, Summary: {row[2]}, Time: {row[3]}")
        print("----------------------")

    conn.close()

if __name__ == "__main__":
    print("🛡️ Security Analysis Database Script 🛡️")
    init_db()
    view_history()