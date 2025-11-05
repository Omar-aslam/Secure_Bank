// This file controls how the dashboard page works for users.
// It loads account info, shows transactions, and handles forms for deposit, withdraw, and transfer.
// The code makes sure users see the right options and get feedback if something goes wrong.
// SecureBank Dashboard Frontend JS
// Handles account info, transactions, and form logic for deposit, withdraw, and transfer
let currentAccountId = null;

async function loadAccountInfo() {
    try {
        const response = await fetch('/api/account-info');
        const data = await response.json();
        
        if (response.ok && data.accounts && data.accounts.length > 0) {
            let totalBalance = 0;
            const accountsContainer = document.getElementById('accountsContainer') || document.createElement('div');
            accountsContainer.id = 'accountsContainer';
            accountsContainer.innerHTML = '';
            
            data.accounts.forEach(account => {
                totalBalance += account.balance;
                const accountDiv = document.createElement('div');
                accountDiv.className = 'account-item';
                accountDiv.innerHTML = `
                    <div class="account-type">${account.account_type} Account</div>
                    <div class="account-balance">$${account.balance.toFixed(2)}</div>
                    <div class="account-details">
                        <div>Interest Rate: ${account.interest_rate}%</div>
                        <div>Minimum Balance: $${account.minimum_balance}</div>
                    </div>
                `;
                accountsContainer.appendChild(accountDiv);
            });
            
            document.getElementById('balance').textContent = `$${totalBalance.toFixed(2)}`;
            
            // Insert accounts container after the main balance display
            const balanceContainer = document.querySelector('.account-summary');
            if (!document.getElementById('accountsContainer')) {
                balanceContainer.parentNode.insertBefore(accountsContainer, balanceContainer.nextSibling);
            }
            
            // Set the current account ID to the first account
            currentAccountId = data.accounts[0].account_id;
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

// Populate account dropdowns
async function loadAccountTypes() {
    try {
        const response = await fetch('/api/account-types');
        const data = await response.json();
        
        if (response.ok) {
            const accounts = data.account_types;
            const fromSelect = document.getElementById('fromAccountType');
            const toSelect = document.getElementById('toAccountType');
            
            // Clear existing options
            fromSelect.innerHTML = '<option value="">Select Source Account</option>';
            toSelect.innerHTML = '<option value="">Select Destination Account</option>';
            
            // Add account types
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.name;
                option.textContent = `${account.name} Account`;
                fromSelect.appendChild(option.cloneNode(true));
                toSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading account types:', error);
    }
}

// Handle transfer type change
function updateTransferFormUI() {
    const transferType = document.getElementById('transferType').value;
    const isExternal = transferType === 'external';
    const toAccountSelect = document.getElementById('toAccountType');
    const externalAccount = document.getElementById('externalAccount');
    toAccountSelect.style.display = isExternal ? 'none' : 'block';
    externalAccount.style.display = isExternal ? 'block' : 'none';
    toAccountSelect.required = !isExternal;
    externalAccount.required = isExternal;
}

document.getElementById('transferType').addEventListener('change', updateTransferFormUI);

// Initialize transfer form UI on page load
window.addEventListener('DOMContentLoaded', () => {
    updateTransferFormUI();
});

document.getElementById('transferForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(document.getElementById('transferAmount').value);
    const transferType = document.getElementById('transferType').value;
    const fromAccountType = document.getElementById('fromAccountType').value;
    let toAccount = '';
    
    if (transferType === 'internal') {
        toAccount = document.getElementById('toAccountType').value;
    } else {
        toAccount = document.getElementById('externalAccount').value;
    }
    
    try {
        const response = await fetch('/api/transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                amount,
                transferType,
                fromAccountType,
                ...(transferType === 'internal' ? { toAccountType: toAccount } : { to_account: toAccount })
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message);
            document.getElementById('transferAmount').value = '';
            document.getElementById('fromAccountType').value = '';
            if (transferType === 'internal') {
                document.getElementById('toAccountType').value = '';
            } else {
                document.getElementById('externalAccount').value = '';
            }
            await loadAccountInfo();
            await loadTransactions();
        } else {
            showNotification(data.error, true);
        }
    } catch (error) {
        showNotification('An error occurred', true);
    }
});

// Initial loads
loadAccountInfo();
loadTransactions();
loadAccountTypes();
