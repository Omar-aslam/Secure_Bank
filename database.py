# This file helps the bank app talk to the database (where all account info is stored).
# It sets up the database and provides functions to connect and manage data.
# Database utility functions for SecureBank
# Handles connection, initialization, and schema setup for SQLite
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

def migrate_accounts(conn, cursor):
    """Migrate existing accounts to the new schema"""
    # Check if we need to migrate
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'account_type' in columns and 'account_type_id' not in columns:
        # Create temporary table
        cursor.execute('''
            CREATE TABLE accounts_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_type_id INTEGER NOT NULL,
                balance REAL DEFAULT 0.0,
                last_interest_calc_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (account_type_id) REFERENCES account_types(id)
            )
        ''')
        
        # Ensure account types exist
        cursor.execute("SELECT COUNT(*) FROM account_types")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                'INSERT INTO account_types (type_name, interest_rate, minimum_balance, description) VALUES (?, ?, ?, ?)',
                [
                    ('Checking', 0.0, 0.0, 'Basic checking account with no minimum balance'),
                    ('Savings', 2.5, 100.0, 'Savings account with 2.5% annual interest rate'),
                    ('Fixed Deposit', 5.0, 1000.0, 'Fixed deposit account with 5% annual interest rate'),
                    ('Premium Checking', 0.5, 5000.0, 'Premium checking account with 0.5% interest rate')
                ]
            )
        
        # Get account type mapping
        cursor.execute("SELECT id, type_name FROM account_types")
        type_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Migrate data
        cursor.execute("SELECT * FROM accounts")
        old_accounts = cursor.fetchall()
        
        for account in old_accounts:
            account_type = account[2]  # account_type column in old schema
            type_id = type_map.get(account_type, type_map['Checking'])  # Default to Checking if type not found
            
            cursor.execute('''
                INSERT INTO accounts_temp (id, user_id, account_type_id, balance, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (account[0], account[1], type_id, account[3], account[4]))
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE accounts")
        cursor.execute("ALTER TABLE accounts_temp RENAME TO accounts")
        
        print("Account migration completed successfully!")

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
    
    # Create account_types table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT UNIQUE NOT NULL,
            interest_rate REAL NOT NULL,
            minimum_balance REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_type_id INTEGER NOT NULL,
            balance REAL DEFAULT 0.0,
            last_interest_calc_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (account_type_id) REFERENCES account_types(id)
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
    
    # Create account types if they don't exist
    cursor.execute("SELECT COUNT(*) as count FROM account_types")
    if cursor.fetchone()['count'] == 0:
        # Insert default account types
        account_types = [
            ('Checking', 0.0, 0.0, 'Basic checking account with no minimum balance'),
            ('Savings', 2.5, 100.0, 'Savings account with 2.5% annual interest rate'),
            ('Fixed Deposit', 5.0, 1000.0, 'Fixed deposit account with 5% annual interest rate'),
            ('Premium Checking', 0.5, 5000.0, 'Premium checking account with 0.5% interest rate')
        ]
        cursor.executemany('''
            INSERT INTO account_types (type_name, interest_rate, minimum_balance, description)
            VALUES (?, ?, ?, ?)
        ''', account_types)

    # Create demo accounts if they don't exist
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] == 0:
        # Migrate existing accounts if needed
        migrate_accounts(conn, cursor)
        
        # Get account type IDs
        cursor.execute("SELECT id, type_name FROM account_types")
        account_type_map = {row['type_name']: row['id'] for row in cursor.fetchall()}

        # Create demo user 1
        cursor.execute('''
            INSERT INTO users (account_number, full_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', ('ACC001', 'John Doe', 'john@example.com', hash_password('password123')))
        user1_id = cursor.lastrowid
        
        # Create multiple accounts for user 1
        accounts_user1 = [
            (user1_id, account_type_map['Checking'], 5000.00),
            (user1_id, account_type_map['Savings'], 10000.00),
            (user1_id, account_type_map['Fixed Deposit'], 20000.00)
        ]
        cursor.executemany('''
            INSERT INTO accounts (user_id, account_type_id, balance)
            VALUES (?, ?, ?)
        ''', accounts_user1)
        
        # Create demo user 2
        cursor.execute('''
            INSERT INTO users (account_number, full_name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', ('ACC002', 'Jane Smith', 'jane@example.com', hash_password('password123')))
        user2_id = cursor.lastrowid
        
        # Create multiple accounts for user 2
        accounts_user2 = [
            (user2_id, account_type_map['Premium Checking'], 15000.00),
            (user2_id, account_type_map['Savings'], 8000.00)
        ]
        cursor.executemany('''
            INSERT INTO accounts (user_id, account_type_id, balance)
            VALUES (?, ?, ?)
        ''', accounts_user2)
        
        print("Demo accounts created!")
        print("Account 1: ACC001 / password123")
        print("- Checking Balance: $5,000")
        print("- Savings Balance: $10,000")
        print("- Fixed Deposit: $20,000")
        print("\nAccount 2: ACC002 / password123")
        print("- Premium Checking Balance: $15,000")
        print("- Savings Balance: $8,000")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
