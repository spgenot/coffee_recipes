import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from werkzeug.security import generate_password_hash, check_password_hash


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
    
    # Create user table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create espresso_entry table (check if user_id column exists)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS espresso_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            coffee TEXT NOT NULL,
            grinder_setting TEXT NOT NULL,
            input_weight REAL NOT NULL,
            output_weight REAL NOT NULL,
            taste_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    ''')
    
    # Migration: Add user_id column if it doesn't exist (for existing databases)
    try:
        cursor.execute('SELECT user_id FROM espresso_entry LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, need to migrate
        # Create a default anonymous user for existing entries
        cursor.execute('''
            INSERT OR IGNORE INTO user (id, email, password_hash)
            VALUES (1, 'anonymous@system.local', ?)
        ''', (generate_password_hash('migration'),))
        
        # Add user_id column with default value
        cursor.execute('ALTER TABLE espresso_entry ADD COLUMN user_id INTEGER DEFAULT 1')
        cursor.execute('UPDATE espresso_entry SET user_id = 1 WHERE user_id IS NULL')
        
        # Make user_id NOT NULL
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        cursor.execute('''
            CREATE TABLE espresso_entry_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coffee TEXT NOT NULL,
                grinder_setting TEXT NOT NULL,
                input_weight REAL NOT NULL,
                output_weight REAL NOT NULL,
                taste_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        ''')
        cursor.execute('''
            INSERT INTO espresso_entry_new 
            SELECT id, COALESCE(user_id, 1), coffee, grinder_setting, input_weight, 
                   output_weight, taste_comment, created_at
            FROM espresso_entry
        ''')
        cursor.execute('DROP TABLE espresso_entry')
        cursor.execute('ALTER TABLE espresso_entry_new RENAME TO espresso_entry')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_espresso_entry_user_id ON espresso_entry(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_espresso_entry_coffee ON espresso_entry(coffee)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_email ON user(email)')
    
    conn.commit()
    conn.close()


def add_entry(user_id: int, coffee: str, grinder_setting: str, input_weight: float, 
              output_weight: float, taste_comment: str = '') -> int:
    """Add a new espresso entry to the database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO espresso_entry (user_id, coffee, grinder_setting, input_weight, 
                                   output_weight, taste_comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, coffee, grinder_setting, input_weight, output_weight, taste_comment))
    
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def get_all_entries(user_id: Optional[int] = None) -> List[Dict]:
    """Get all entries ordered by creation date (newest first).
    If user_id is provided, returns user's entries + anonymous community entries.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    if user_id:
        # Get user's entries + anonymous entries from others
        cursor.execute('''
            SELECT e.*, u.email as user_email
            FROM espresso_entry e
            LEFT JOIN user u ON e.user_id = u.id
            WHERE e.user_id = ? OR e.user_id != ?
            ORDER BY e.created_at DESC
        ''', (user_id, user_id))
    else:
        # Get all entries (for unauthenticated users)
        cursor.execute('''
            SELECT e.*, u.email as user_email
            FROM espresso_entry e
            LEFT JOIN user u ON e.user_id = u.id
            ORDER BY e.created_at DESC
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


def get_entries_by_coffee(coffee_name: str, user_id: Optional[int] = None) -> List[Dict]:
    """Get all entries for a specific coffee.
    If user_id is provided, returns user's entries + anonymous community entries.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    if user_id:
        # Get user's entries + anonymous entries from others
        cursor.execute('''
            SELECT e.*, u.email as user_email
            FROM espresso_entry e
            LEFT JOIN user u ON e.user_id = u.id
            WHERE e.coffee = ? AND (e.user_id = ? OR e.user_id != ?)
            ORDER BY e.created_at DESC
        ''', (coffee_name, user_id, user_id))
    else:
        # Get all entries (for unauthenticated users)
        cursor.execute('''
            SELECT e.*, u.email as user_email
            FROM espresso_entry e
            LEFT JOIN user u ON e.user_id = u.id
            WHERE e.coffee = ?
            ORDER BY e.created_at DESC
        ''', (coffee_name,))
    
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries


def get_user_entries(user_id: int) -> List[Dict]:
    """Get all entries for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM espresso_entry
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries


def get_anonymous_entries_by_coffee(coffee_name: str, exclude_user_id: int) -> List[Dict]:
    """Get anonymous entries for a coffee, excluding the specified user's entries."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.*
        FROM espresso_entry e
        WHERE e.coffee = ? AND e.user_id != ?
        ORDER BY e.created_at DESC
    ''', (coffee_name, exclude_user_id))
    
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries


def get_user_and_anonymous_entries_by_coffee(coffee_name: str, user_id: int) -> tuple:
    """Get user's entries and anonymous entries separately for a coffee.
    Returns (user_entries, anonymous_entries)
    """
    user_entries = get_user_entries(user_id)
    user_entries = [e for e in user_entries if e['coffee'] == coffee_name]
    
    anonymous_entries = get_anonymous_entries_by_coffee(coffee_name, user_id)
    
    return user_entries, anonymous_entries


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


# User management functions

def create_user(email: str, password: str) -> int:
    """Create a new user with hashed password."""
    conn = get_db()
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute('''
            INSERT INTO user (email, password_hash)
            VALUES (?, ?)
        ''', (email, password_hash))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Email already exists")


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM user WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def verify_password(user: Dict, password: str) -> bool:
    """Verify password against user's hash."""
    return check_password_hash(user['password_hash'], password)


def update_user_password(user_id: int, new_password: str):
    """Update user's password."""
    conn = get_db()
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(new_password)
    
    cursor.execute('''
        UPDATE user
        SET password_hash = ?
        WHERE id = ?
    ''', (password_hash, user_id))
    
    conn.commit()
    conn.close()


def update_entry(entry_id: int, user_id: int, coffee: str, grinder_setting: str,
                 input_weight: float, output_weight: float, taste_comment: str = ''):
    """Update an espresso entry. Only the owner can update."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute('SELECT user_id FROM espresso_entry WHERE id = ?', (entry_id,))
    row = cursor.fetchone()
    if not row or row[0] != user_id:
        conn.close()
        raise PermissionError("You can only edit your own entries")
    
    cursor.execute('''
        UPDATE espresso_entry
        SET coffee = ?, grinder_setting = ?, input_weight = ?, 
            output_weight = ?, taste_comment = ?
        WHERE id = ? AND user_id = ?
    ''', (coffee, grinder_setting, input_weight, output_weight, taste_comment, entry_id, user_id))
    
    conn.commit()
    conn.close()


def delete_entry(entry_id: int, user_id: int):
    """Delete an espresso entry. Only the owner can delete."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify ownership
    cursor.execute('SELECT user_id FROM espresso_entry WHERE id = ?', (entry_id,))
    row = cursor.fetchone()
    if not row or row[0] != user_id:
        conn.close()
        raise PermissionError("You can only delete your own entries")
    
    cursor.execute('DELETE FROM espresso_entry WHERE id = ? AND user_id = ?', (entry_id, user_id))
    
    conn.commit()
    conn.close()
