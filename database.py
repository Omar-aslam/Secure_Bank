import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DATABASE = 'banking.db'

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash a password securely using werkzeug"""
    return generate_password_hash(password)

def init_db():
    """Initialize the database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_account_id INTEGER,
            to_account_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_account_id) REFERENCES accounts(id),
            FOREIGN KEY (to_account_id) REFERENCES accounts(id)
        )
    ''')
    
    # Create demo accounts if they don't exist
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] == 0:
        # Create demo user 1
        cursor.execute('''
            INSERT INTO users (account_number, full_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', ('ACC001', 'John Doe', 'john@example.com', hash_password('password123')))
        user1_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO accounts (user_id, account_type, balance)
            VALUES (?, ?, ?)
        ''', (user1_id, 'Checking', 5000.00))
        
        # Create demo user 2
        cursor.execute('''
            INSERT INTO users (account_number, full_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', ('ACC002', 'Jane Smith', 'jane@example.com', hash_password('password123')))
        user2_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO accounts (user_id, account_type, balance)
            VALUES (?, ?, ?)
        ''', (user2_id, 'Checking', 3000.00))
        
        print("Demo accounts created!")
        print("Account 1: ACC001 / password123 (Balance: $5,000)")
        print("Account 2: ACC002 / password123 (Balance: $3,000)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
