import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


DATABASE = 'espresso_tracker.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS espresso_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coffee TEXT NOT NULL,
            grinder_setting TEXT NOT NULL,
            input_weight REAL NOT NULL,
            output_weight REAL NOT NULL,
            taste_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def add_entry(coffee: str, grinder_setting: str, input_weight: float, 
              output_weight: float, taste_comment: str = '') -> int:
    """Add a new espresso entry to the database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO espresso_entry (coffee, grinder_setting, input_weight, 
                                   output_weight, taste_comment)
        VALUES (?, ?, ?, ?, ?)
    ''', (coffee, grinder_setting, input_weight, output_weight, taste_comment))
    
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def get_all_entries() -> List[Dict]:
    """Get all entries ordered by creation date (newest first)."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM espresso_entry
        ORDER BY created_at DESC
    ''')
    
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries


def get_entry_by_id(entry_id: int) -> Optional[Dict]:
    """Get a single entry by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM espresso_entry WHERE id = ?', (entry_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_entries_by_coffee(coffee_name: str) -> List[Dict]:
    """Get all entries for a specific coffee."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM espresso_entry
        WHERE coffee = ?
        ORDER BY created_at DESC
    ''', (coffee_name,))
    
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries


def get_all_coffees() -> List[str]:
    """Get a list of all unique coffee names."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT DISTINCT coffee FROM espresso_entry ORDER BY coffee')
    coffees = [row[0] for row in cursor.fetchall()]
    conn.close()
    return coffees


def calculate_extraction_ratio(input_weight: float, output_weight: float) -> float:
    """Calculate extraction ratio (output/input)."""
    if input_weight == 0:
        return 0.0
    return round(output_weight / input_weight, 2)
