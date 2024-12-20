// Toggle Sidebar
document.addEventListener('DOMContentLoaded', function() {
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');

    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
});

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            window.location.href = '/dashboard';
        } else {
            const error = await response.json();
            alert(error.detail || 'Login failed');
        }
    } catch (error) {
        alert('Login failed');
    }
}

// Handle logout
function handleLogout() {
    window.location.href = '/logout';
}

// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup login form handler
    const loginForm = document.querySelector('form[action="/login"]');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Setup logout handler
    const logoutLink = document.querySelector('a[href="/logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            handleLogout();
        });
    }

    // Add token to all fetch requests
    const token = localStorage.getItem('token');
    if (token) {
        const headers = new Headers();
        headers.append('Authorization', `Bearer ${token}`);
        
        // Add headers to all fetch requests
        const originalFetch = window.fetch;
        window.fetch = function() {
            if (arguments[1] && !arguments[1].headers) {
                if (arguments[1].method !== 'GET') {
                    arguments[1].headers = headers;
                }
            }
            return originalFetch.apply(this, arguments);
        };
    }
});
