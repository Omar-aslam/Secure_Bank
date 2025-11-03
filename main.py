from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection, init_db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
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
    account = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    
    if account:
        return jsonify({
            'account_type': account['account_type'],
            'balance': float(account['balance']),
            'account_id': account['id']
        })
    return jsonify({'error': 'Account not found'}), 404

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
    """Deposit funds into account"""
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
    account = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    # Update balance
    new_balance = account['balance'] + amount
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_balance, account['id'])
    )
    
    # Record transaction
    conn.execute('''
        INSERT INTO transactions (to_account_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?)
    ''', (account['id'], 'DEPOSIT', amount, 'Deposit to account'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully deposited ${amount:.2f}'})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    """Withdraw funds from account"""
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
    account = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    if not account:
        conn.close()
        return jsonify({'error': 'Account not found'}), 404
    
    if account['balance'] < amount:
        conn.close()
        return jsonify({'error': 'Insufficient funds'}), 400
    
    # Update balance
    new_balance = account['balance'] - amount
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_balance, account['id'])
    )
    
    # Record transaction
    conn.execute('''
        INSERT INTO transactions (from_account_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?)
    ''', (account['id'], 'WITHDRAWAL', amount, 'Withdrawal from account'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully withdrew ${amount:.2f}'})

@app.route('/api/transfer', methods=['POST'])
def transfer():
    """Transfer funds to another account"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        amount = float(data.get('amount', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount format'}), 400
    
    to_account_number = data.get('to_account_number')
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than zero'}), 400
    
    if not to_account_number:
        return jsonify({'error': 'Recipient account number required'}), 400
    
    conn = get_db_connection()
    
    # Get sender account
    from_account = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    
    if not from_account:
        conn.close()
        return jsonify({'error': 'Your account not found'}), 404
    
    if from_account['balance'] < amount:
        conn.close()
        return jsonify({'error': 'Insufficient funds'}), 400
    
    # Get recipient account
    to_user = conn.execute(
        'SELECT * FROM users WHERE account_number = ?',
        (to_account_number,)
    ).fetchone()
    
    if not to_user:
        conn.close()
        return jsonify({'error': 'Recipient account not found'}), 404
    
    to_account = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ?',
        (to_user['id'],)
    ).fetchone()
    
    if not to_account:
        conn.close()
        return jsonify({'error': 'Recipient account not found'}), 404
    
    # Perform transfer
    new_from_balance = from_account['balance'] - amount
    new_to_balance = to_account['balance'] + amount
    
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_from_balance, from_account['id'])
    )
    conn.execute(
        'UPDATE accounts SET balance = ? WHERE id = ?',
        (new_to_balance, to_account['id'])
    )
    
    # Record transaction
    conn.execute('''
        INSERT INTO transactions (from_account_id, to_account_id, transaction_type, amount, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (from_account['id'], to_account['id'], 'TRANSFER', amount, 
          f'Transfer to {to_account_number}'))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True, 
        'new_balance': new_from_balance, 
        'message': f'Successfully transferred ${amount:.2f} to {to_account_number}'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
