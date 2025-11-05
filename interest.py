# This file contains the rules for adding interest to accounts.
# Interest is extra money added to accounts like Savings or Fixed Deposit, based on their balance and rate.
# Interest calculation logic for SecureBank
# Provides functions to calculate and apply interest to accounts
from datetime import datetime, timedelta
from database import get_db_connection

def calculate_interest(account_id):
    """Calculate interest for an account based on its type"""
    conn = get_db_connection()
    
    # Get account details with its type
    account = conn.execute('''
        SELECT a.*, at.interest_rate, at.type_name
        FROM accounts a
        JOIN account_types at ON a.account_type_id = at.id
        WHERE a.id = ?
    ''', (account_id,)).fetchone()
    
    if not account:
        conn.close()
        return False, "Account not found"
    
    # Skip if account type doesn't earn interest
    if account['interest_rate'] == 0:
        conn.close()
        return True, "Account type does not earn interest"
    
    # Calculate days since last interest calculation
    last_calc = datetime.strptime(account['last_interest_calc_date'], '%Y-%m-%d %H:%M:%S') if account['last_interest_calc_date'] else datetime.strptime(account['created_at'], '%Y-%m-%d %H:%M:%S')
    days_since_last_calc = (datetime.now() - last_calc).days
    
    if days_since_last_calc < 1:
        conn.close()
        return True, "Interest already calculated today"
    
    # Calculate daily interest rate (annual rate / 365)
    daily_rate = float(account['interest_rate']) / 365 / 100
    interest_amount = float(account['balance']) * daily_rate * days_since_last_calc
    
    # Update balance and last calculation date
    try:
        conn.execute('''
            UPDATE accounts
            SET balance = balance + ?,
                last_interest_calc_date = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (interest_amount, account_id))
        
        # Log the interest credit as a transaction
        conn.execute('''
            INSERT INTO transactions 
            (to_account_id, transaction_type, amount, description)
            VALUES (?, 'INTEREST', ?, ?)
        ''', (account_id, interest_amount, f"Interest credit for {account['type_name']} account"))
        
        conn.commit()
        conn.close()
        return True, f"Interest of ${interest_amount:.2f} credited successfully"
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error calculating interest: {str(e)}"