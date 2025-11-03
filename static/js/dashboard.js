let currentAccountId = null;

async function loadAccountInfo() {
    try {
        const response = await fetch('/api/account-info');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;
            document.getElementById('accountType').textContent = data.account_type + ' Account';
            currentAccountId = data.account_id;
        }
    } catch (error) {
        console.error('Error loading account info:', error);
    }
}

async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        const transactions = await response.json();
        
        const transactionsList = document.getElementById('transactionsList');
        
        if (transactions.length === 0) {
            transactionsList.innerHTML = '<p class="loading">No transactions yet</p>';
            return;
        }
        
        transactionsList.innerHTML = transactions.map(t => {
            const isPositive = t.type === 'DEPOSIT' || t.type === 'TRANSFER';
            const amountClass = isPositive ? 'positive' : 'negative';
            const sign = isPositive ? '+' : '-';
            
            return `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-type">${t.type}</div>
                        <div class="transaction-date">${new Date(t.created_at).toLocaleString()}</div>
                    </div>
                    <div class="transaction-amount ${amountClass}">
                        ${sign}$${t.amount.toFixed(2)}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function showNotification(message, isError = false) {
    const notification = document.getElementById('notification');
    const messageSpan = document.getElementById('notificationMessage');
    
    messageSpan.textContent = message;
    notification.className = 'notification' + (isError ? ' error' : '');
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

document.getElementById('depositForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(document.getElementById('depositAmount').value);
    
    try {
        const response = await fetch('/api/deposit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amount })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message);
            document.getElementById('depositAmount').value = '';
            await loadAccountInfo();
            await loadTransactions();
        } else {
            showNotification(data.error, true);
        }
    } catch (error) {
        showNotification('An error occurred', true);
    }
});

document.getElementById('withdrawForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(document.getElementById('withdrawAmount').value);
    
    try {
        const response = await fetch('/api/withdraw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ amount })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message);
            document.getElementById('withdrawAmount').value = '';
            await loadAccountInfo();
            await loadTransactions();
        } else {
            showNotification(data.error, true);
        }
    } catch (error) {
        showNotification('An error occurred', true);
    }
});

document.getElementById('transferForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(document.getElementById('transferAmount').value);
    const toAccountNumber = document.getElementById('transferAccount').value;
    
    try {
        const response = await fetch('/api/transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                amount,
                to_account_number: toAccountNumber
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message);
            document.getElementById('transferAmount').value = '';
            document.getElementById('transferAccount').value = '';
            await loadAccountInfo();
            await loadTransactions();
        } else {
            showNotification(data.error, true);
        }
    } catch (error) {
        showNotification('An error occurred', true);
    }
});

loadAccountInfo();
loadTransactions();
