"""
Jottask Email Connection Setup
Allows users to connect their email accounts for automatic task creation
"""

import os
from flask import Blueprint, render_template_string, request, redirect, url_for, session, jsonify
from supabase import create_client, Client
from functools import wraps

email_setup_bp = Blueprint('email_setup', __name__, url_prefix='/email')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


EMAIL_SETUP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Setup - Jottask</title>
    <style>
        :root {
            --primary: #6366F1;
            --primary-dark: #4F46E5;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --gray-50: #F9FAFB;
            --gray-100: #F3F4F6;
            --gray-200: #E5E7EB;
            --gray-500: #6B7280;
            --gray-700: #374151;
            --gray-900: #111827;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--gray-50);
            color: var(--gray-900);
            line-height: 1.5;
        }

        .nav {
            background: white;
            border-bottom: 1px solid var(--gray-200);
            padding: 0 24px;
            display: flex;
            align-items: center;
            height: 64px;
        }

        .nav a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
        }

        .main {
            max-width: 800px;
            margin: 40px auto;
            padding: 0 24px;
        }

        .card {
            background: white;
            border-radius: 12px;
            border: 1px solid var(--gray-200);
            margin-bottom: 24px;
        }

        .card-header {
            padding: 20px;
            border-bottom: 1px solid var(--gray-200);
        }

        .card-body {
            padding: 20px;
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
        }

        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-secondary {
            background: var(--gray-100);
            color: var(--gray-700);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: var(--gray-700);
        }

        .form-input {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--gray-300);
            border-radius: 8px;
            font-size: 14px;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary);
        }

        .connection-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            border-bottom: 1px solid var(--gray-100);
        }

        .connection-item:last-child {
            border-bottom: none;
        }

        .connection-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .connection-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            background: var(--gray-100);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .connection-status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-active {
            background: #D1FAE5;
            color: #065F46;
        }

        .status-inactive {
            background: #FEE2E2;
            color: #991B1B;
        }

        .help-text {
            font-size: 13px;
            color: var(--gray-500);
            margin-top: 8px;
        }

        .steps {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .step {
            display: flex;
            gap: 16px;
        }

        .step-number {
            width: 28px;
            height: 28px;
            background: var(--primary);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            flex-shrink: 0;
        }

        .step-content h4 {
            margin-bottom: 4px;
        }

        .step-content p {
            color: var(--gray-500);
            font-size: 14px;
        }

        .code-box {
            background: var(--gray-900);
            color: #10B981;
            padding: 12px 16px;
            border-radius: 8px;
            font-family: monospace;
            margin-top: 8px;
            font-size: 14px;
        }

        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        }

        .alert-success {
            background: #D1FAE5;
            color: #065F46;
        }

        .alert-error {
            background: #FEE2E2;
            color: #991B1B;
        }
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/dashboard">← Back to Dashboard</a>
    </nav>

    <main class="main">
        <h1 style="margin-bottom: 8px;">Email Connections</h1>
        <p style="color: var(--gray-500); margin-bottom: 32px;">
            Connect your email to automatically create tasks from incoming messages.
        </p>

        {% if message %}
        <div class="alert alert-success">{{ message }}</div>
        {% endif %}

        {% if error %}
        <div class="alert alert-error">{{ error }}</div>
        {% endif %}

        <!-- Existing Connections -->
        {% if connections %}
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Your Connections</h2>
            </div>
            <div class="card-body" style="padding: 0;">
                {% for conn in connections %}
                <div class="connection-item">
                    <div class="connection-info">
                        <div class="connection-icon">
                            {% if conn.provider == 'gmail' %}📧{% else %}✉️{% endif %}
                        </div>
                        <div>
                            <strong>{{ conn.email_address }}</strong>
                            <div style="font-size: 13px; color: var(--gray-500);">
                                {{ conn.provider|capitalize }} •
                                Last sync: {{ conn.last_sync_at[:16].replace('T', ' ') if conn.last_sync_at else 'Never' }}
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="connection-status {% if conn.is_active %}status-active{% else %}status-inactive{% endif %}">
                            {{ 'Active' if conn.is_active else 'Inactive' }}
                        </span>
                        <form method="POST" action="/email/{{ conn.id }}/delete" style="margin: 0;">
                            <button type="submit" class="btn btn-danger" style="padding: 6px 12px; font-size: 13px;">Remove</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Add New Connection -->
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Add Email Connection</h2>
            </div>
            <div class="card-body">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
                    <div class="card" style="cursor: pointer; border: 2px solid var(--gray-200);" onclick="showGmailSetup()">
                        <div class="card-body" style="text-align: center; padding: 24px;">
                            <div style="font-size: 40px; margin-bottom: 12px;">📧</div>
                            <h3>Gmail</h3>
                            <p style="color: var(--gray-500); font-size: 14px;">Connect via App Password</p>
                        </div>
                    </div>
                    <div class="card" style="cursor: pointer; border: 2px solid var(--gray-200); opacity: 0.5;">
                        <div class="card-body" style="text-align: center; padding: 24px;">
                            <div style="font-size: 40px; margin-bottom: 12px;">📬</div>
                            <h3>Forward Email</h3>
                            <p style="color: var(--gray-500); font-size: 14px;">Coming soon</p>
                        </div>
                    </div>
                </div>

                <!-- Gmail Setup Form -->
                <div id="gmail-setup" style="display: none;">
                    <h3 style="margin-bottom: 16px;">Gmail Setup Instructions</h3>

                    <div class="steps" style="margin-bottom: 24px;">
                        <div class="step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <h4>Enable 2-Factor Authentication</h4>
                                <p>Go to your Google Account → Security → 2-Step Verification</p>
                            </div>
                        </div>
                        <div class="step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <h4>Create an App Password</h4>
                                <p>Go to Google Account → Security → App passwords → Create new</p>
                            </div>
                        </div>
                        <div class="step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <h4>Enter your credentials below</h4>
                                <p>Use your Gmail address and the App Password you created</p>
                            </div>
                        </div>
                    </div>

                    <form method="POST" action="/email/add/gmail">
                        <div class="form-group">
                            <label class="form-label">Gmail Address</label>
                            <input type="email" name="email_address" class="form-input" placeholder="you@gmail.com" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">App Password</label>
                            <input type="password" name="app_password" class="form-input" placeholder="xxxx xxxx xxxx xxxx" required>
                            <p class="help-text">This is NOT your regular Gmail password. Generate one at myaccount.google.com/apppasswords</p>
                        </div>

                        <button type="submit" class="btn btn-primary">Connect Gmail</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- How it Works -->
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">How Email Processing Works</h2>
            </div>
            <div class="card-body">
                <div class="steps">
                    <div class="step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h4>Emails are scanned automatically</h4>
                            <p>We check your inbox every 15 minutes for new actionable emails.</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h4>AI extracts task information</h4>
                            <p>Our AI identifies tasks, due dates, client info, and priority levels.</p>
                        </div>
                    </div>
                    <div class="step">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h4>Tasks appear in your dashboard</h4>
                            <p>New tasks are created automatically and you get notified.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function showGmailSetup() {
            document.getElementById('gmail-setup').style.display = 'block';
        }
    </script>
</body>
</html>
"""


@email_setup_bp.route('/')
@login_required
def email_setup():
    user_id = session['user_id']

    # Get existing connections
    connections = supabase.table('email_connections')\
        .select('*')\
        .eq('user_id', user_id)\
        .execute()

    return render_template_string(
        EMAIL_SETUP_TEMPLATE,
        connections=connections.data or [],
        message=request.args.get('message'),
        error=request.args.get('error')
    )


@email_setup_bp.route('/add/gmail', methods=['POST'])
@login_required
def add_gmail():
    user_id = session['user_id']
    email_address = request.form.get('email_address', '').lower().strip()
    app_password = request.form.get('app_password', '').strip()

    if not email_address or not app_password:
        return redirect(url_for('email_setup.email_setup', error='Please fill in all fields'))

    # Test the connection
    import imaplib
    try:
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(email_address, app_password.replace(' ', ''))
        imap.logout()
    except Exception as e:
        return redirect(url_for('email_setup.email_setup', error=f'Connection failed: Invalid credentials'))

    # Check if already exists
    existing = supabase.table('email_connections')\
        .select('id')\
        .eq('user_id', user_id)\
        .eq('email_address', email_address)\
        .execute()

    if existing.data:
        # Update existing
        supabase.table('email_connections').update({
            'imap_password': app_password.replace(' ', ''),
            'is_active': True
        }).eq('id', existing.data[0]['id']).execute()
    else:
        # Create new
        supabase.table('email_connections').insert({
            'user_id': user_id,
            'provider': 'gmail',
            'email_address': email_address,
            'imap_password': app_password.replace(' ', ''),
            'is_active': True
        }).execute()

    return redirect(url_for('email_setup.email_setup', message='Gmail connected successfully!'))


@email_setup_bp.route('/<connection_id>/delete', methods=['POST'])
@login_required
def delete_connection(connection_id):
    user_id = session['user_id']

    supabase.table('email_connections')\
        .delete()\
        .eq('id', connection_id)\
        .eq('user_id', user_id)\
        .execute()

    return redirect(url_for('email_setup.email_setup', message='Connection removed'))


@email_setup_bp.route('/<connection_id>/toggle', methods=['POST'])
@login_required
def toggle_connection(connection_id):
    user_id = session['user_id']

    # Get current status
    conn = supabase.table('email_connections')\
        .select('is_active')\
        .eq('id', connection_id)\
        .eq('user_id', user_id)\
        .single()\
        .execute()

    if conn.data:
        new_status = not conn.data['is_active']
        supabase.table('email_connections').update({
            'is_active': new_status
        }).eq('id', connection_id).execute()

    return redirect(url_for('email_setup.email_setup'))
