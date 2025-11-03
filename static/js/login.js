document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const accountNumber = document.getElementById('account_number').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('error-message');
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                account_number: accountNumber,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.location.href = '/dashboard';
        } else {
            errorDiv.textContent = data.message;
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'An error occurred. Please try again.';
        errorDiv.style.display = 'block';
    }
});
