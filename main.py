# SecureBank Flask backend
# This file powers the bank's web application. It manages user login, account details, deposits, withdrawals, transfers, and interest calculations.
# Each section below is explained in plain language for easy understanding.
# --- Initialization and Configuration ---
# The following lines set up the web server and database connection.
# Home page: If the user is already logged in, they go to their dashboard. Otherwise, they are sent to the login page.
# Login endpoint: This checks the user's account number and password. If correct, it logs them in and remembers them for future actions.
# Logout endpoint: This logs the user out and forgets who they are.
# Dashboard page: Shows the user's name and account number at the top of the page.
# API: Get all account info for the logged-in user
# This provides details about all the user's accounts, such as balances and account types.
# API: Get all available account types (for dropdowns/UI)
# This lists all possible account types (Checking, Savings, etc.) and their rules.
# API: Calculate and apply interest for a specific account
# This lets the bank add interest to an account, increasing its balance.
# API: Get recent transactions for the logged-in user
# This shows the user a list of their latest deposits, withdrawals, and transfers.
# SecureBank Flask backend
# Implements user authentication, account management, transactions, and interest calculation
# All endpoints require user authentication via session
# --- Initialization and Configuration ---
# Home page: Redirects to dashboard if logged in, otherwise to login
# Login endpoint: Handles login form and authentication
# Logout endpoint: Clears session and redirects to login
# Dashboard page: Renders dashboard template with user info
# API: Get all account info for the logged-in user
# API: Get all available account types (for dropdowns/UI)
# API: Calculate and apply interest for a specific account
# API: Get recent transactions for the logged-in user
# SecureBank Flask backend
# This file implements user authentication, account management, transactions, and interest calculation.
# All endpoints require user authentication via session.
###########################################################
# Initialization and Configuration
###########################################################
# Home page: Redirects to dashboard if logged in, otherwise to login
# Login endpoint: Handles login form and authentication
# Logout endpoint: Clears session and redirects to login
# Dashboard page: Renders dashboard template with user info
# API: Get all account info for the logged-in user
# API: Get all available account types (for dropdowns/UI)
# API: Calculate and apply interest for a specific account
# API: Get recent transactions for the logged-in user
# API: Deposit funds into the user's Checking account only
# API: Withdraw funds from the user's Checking account only
# API: Transfer funds between user's own accounts or to another user's account
# Flask app entry point
git credential-manager-core erasefrom flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection, init_db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from interest import calculate_interest
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database on startup
with app.app_context():
    init_db()

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
            
        account_number = data.get('account_number')
        password = data.get('password')
        
        if not account_number or not password:
            return jsonify({'success': False, 'message': 'Account number and password required'}), 400
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE account_number = ?',
            (account_number,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['account_number'] = user['account_number']
            session['full_name'] = user['full_name']
            return jsonify({'success': True, 'message': 'Login successful!'})
        else:
            return jsonify({'success': False, 'message': 'Invalid account number or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                         full_name=session.get('full_name'),
                         account_number=session.get('account_number'))

@app.route('/api/account-info')
def get_account_info():
    """Get user account information"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    # First check if the account_type_id column exists
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(accounts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'account_type_id' in columns:
        # New schema
        accounts = conn.execute('''
            SELECT a.*, at.type_name, at.interest_rate, at.minimum_balance, at.description
            FROM accounts a
            JOIN account_types at ON a.account_type_id = at.id
            WHERE a.user_id = ?
        ''', (session['user_id'],)).fetchall()
        
        if accounts:
            result = {
                'accounts': [{
                    'account_id': acc['id'],
                    'account_type': acc['type_name'],
                    'balance': float(acc['balance']),
                    'interest_rate': float(acc['interest_rate']),
                    'minimum_balance': float(acc['minimum_balance']),
                    'description': acc['description'],
                    'created_at': acc['created_at']
                } for acc in accounts]
            }
    else:
        # Old schema
        account = conn.execute(
            'SELECT * FROM accounts WHERE user_id = ?',
            (session['user_id'],)
        ).fetchone()
        
        if account:
            result = {
                'accounts': [{
                    'account_id': account['id'],
                    'account_type': account['account_type'],
                    'balance': float(account['balance']),
                    'created_at': account['created_at']
                }]
            }
    
    conn.close()
    
    if 'result' in locals():
        return jsonify(result)
    return jsonify({'error': 'No accounts found'}), 404

@app.route('/api/account-types')
def get_account_types():
    """Get all available account types"""
    conn = get_db_connection()
    types = conn.execute('SELECT * FROM account_types').fetchall()
    conn.close()
    
    return jsonify({
        'account_types': [{
            'id': t['id'],
            'name': t['type_name'],
            'interest_rate': float(t['interest_rate']),
            'minimum_balance': float(t['minimum_balance']),
            'description': t['description']
        } for t in types]
    })

@app.route('/api/accounts/<int:account_id>/calculate-interest', methods=['POST'])
def calculate_account_interest(account_id):
    """Calculate and apply interest for a specific account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Verify account belongs to user
    conn = get_db_connection()
    account = conn.execute(
        'SELECT * FROM accounts WHERE id = ? AND user_id = ?',
        (account_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not account:
        return jsonify({'error': 'Account not found or access denied'}), 404
    
    success, message = calculate_interest(account_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400

@app.route('/api/transactions')
def get_transactions():
    """Get user transaction history"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    account = conn.execute(
        'SELECT id FROM accounts WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    transactions = conn.execute('''
        SELECT * FROM transactions 
        WHERE from_account_id = ? OR to_account_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    ''', (account['id'], account['id'])).fetchall()
    conn.close()
    
    return jsonify([{
        'id': t['id'],
        'type': t['transaction_type'],
        'amount': float(t['amount']),
        'description': t['description'],
        'created_at': t['created_at']
    } for t in transactions])

@app.route('/api/deposit', methods=['POST'])
def deposit():
    # Only deposits to Checking account are allowed
    # When a user deposits money, it is always added to their Checking account.
    # The system checks if the amount is valid and then updates the balance.
    # Only deposits to Checking account are allowed
    """Deposit funds into checking account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount format'}), 400
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than zero'}), 400
    
    conn = get_db_connection()
    # Get the checking account
    account = conn.execute('''
        SELECT a.* FROM accounts a
        JOIN account_types at ON a.account_type_id = at.id
        WHERE a.user_id = ? AND at.type_name = 'Checking'
    ''', (session['user_id'],)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Checking account not found'}), 404
    
    # Update balance
    new_balance = float(account['balance']) + amount
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_balance, account['id'])
    )
    
    # Record transaction
    conn.execute('''
        INSERT INTO transactions (to_account_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?)
    ''', (account['id'], 'DEPOSIT', amount, 'Deposit to Checking account'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully deposited ${amount:.2f} to Checking account'})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    # Only withdrawals from Checking account are allowed
    # When a user withdraws money, it is always taken from their Checking account.
    # The system checks if the user has enough money and if the account stays above the minimum required balance.
    # Only withdrawals from Checking account are allowed
    # Enforce minimum balance for Checking account
    """Withdraw funds from checking account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount format'}), 400
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than zero'}), 400
    
    conn = get_db_connection()
    # Get the checking account
    account = conn.execute('''
        SELECT a.*, at.minimum_balance FROM accounts a
        JOIN account_types at ON a.account_type_id = at.id
        WHERE a.user_id = ? AND at.type_name = 'Checking'
    ''', (session['user_id'],)).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Checking account not found'}), 404
    
    new_balance = float(account['balance']) - amount
    if new_balance < float(account['minimum_balance']):
        conn.close()
        return jsonify({'error': f'Cannot withdraw: minimum balance for Checking is ${account["minimum_balance"]:.2f}'}), 400
    
    # Update balance
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_balance, account['id'])
    )
    
    # Record transaction
    conn.execute('''
        INSERT INTO transactions (from_account_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?)
    ''', (account['id'], 'WITHDRAWAL', amount, 'Withdrawal from Checking account'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully withdrew ${amount:.2f} from Checking account'})

@app.route('/api/transfer', methods=['POST'])
def transfer():
    # Handles both internal (between user's own accounts) and external (to another user) transfers
    # Internal: Move money between your own accounts (e.g., from Checking to Savings)
    # External: Send money to another user's account number
    # The system checks that you have enough money and that your account doesn't go below the minimum required balance.
    # If you try to send money to yourself, it will show an error.
# Flask app entry point
# This starts the web server so users can access the bank online.
    # Handles both internal (between user's own accounts) and external (to another user) transfers
    # Enforces minimum balance for all account types
    """Handle both internal and external transfers"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json(silent=True)
    if not data or 'amount' not in data or 'transferType' not in data or 'fromAccountType' not in data:
        return jsonify({'error': 'Amount, transfer type, and source account type are required'}), 400
    
    amount = float(data['amount'])
    transfer_type = data['transferType']
    from_account_type = data['fromAccountType']
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    conn = get_db_connection()
    try:
        # Get source account
        from_account = conn.execute('''
            SELECT a.* FROM accounts a
            JOIN account_types at ON a.account_type_id = at.id
            WHERE a.user_id = ? AND at.type_name = ?
        ''', (session['user_id'], from_account_type)).fetchone()
        
        if not from_account:
            return jsonify({'error': 'Source account not found'}), 404
        
        # Check sufficient balance and minimum balance
        new_balance = float(from_account['balance']) - amount
        # Get minimum balance for the account type
        min_balance_row = conn.execute('SELECT minimum_balance FROM account_types WHERE type_name = ?', (from_account_type,)).fetchone()
        min_balance = float(min_balance_row['minimum_balance']) if min_balance_row else 0.0
        if new_balance < min_balance:
            return jsonify({'error': f'Cannot transfer: minimum balance for {from_account_type} is ${min_balance:.2f}'}), 400
        
        if transfer_type == 'internal':
            # Internal transfer between own accounts
            if 'toAccountType' not in data:
                return jsonify({'error': 'Destination account type is required'}), 400
            
            to_account_type = data['toAccountType']
            
            if from_account_type == to_account_type:
                return jsonify({'error': 'Cannot transfer to the same account type'}), 400
            
            # Get destination account
            to_account = conn.execute('''
                SELECT a.* FROM accounts a
                JOIN account_types at ON a.account_type_id = at.id
                WHERE a.user_id = ? AND at.type_name = ?
            ''', (session['user_id'], to_account_type)).fetchone()
            
            if not to_account:
                return jsonify({'error': 'Destination account not found'}), 404
            
            description = f"Transfer from {from_account_type} to {to_account_type}"
            
        else:  # external transfer
            if 'to_account' not in data:
                return jsonify({'error': 'Destination account number is required'}), 400
            
            to_account_number = data['to_account']
            
            if to_account_number == session['account_number']:
                return jsonify({'error': 'Cannot transfer to your own account number'}), 400
            
            # Get recipient's account (first available account)
            recipient = conn.execute('''
                SELECT u.id, u.account_number, u.full_name, a.id as account_id 
                FROM users u 
                JOIN accounts a ON u.id = a.user_id
                WHERE u.account_number = ?
                LIMIT 1
            ''', (to_account_number,)).fetchone()
            
            if not recipient:
                return jsonify({'error': 'Recipient account not found'}), 404
            
            to_account = {'id': recipient['account_id']}
            description = f"Transfer to account {to_account_number}"
        
        # Perform transfer
        conn.execute(
            'UPDATE accounts SET balance = balance - ? WHERE id = ?',
            (amount, from_account['id'])
        )
        
        conn.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (amount, to_account['id'])
        )
        
        # Record transaction
        conn.execute('''
            INSERT INTO transactions 
            (from_account_id, to_account_id, transaction_type, amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (from_account['id'], to_account['id'], 'TRANSFER', amount, description))
        
        conn.commit()
        return jsonify({
            'message': f'Successfully transferred ${amount:.2f}. {description}',
            'new_balance': float(from_account['balance']) - amount
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
