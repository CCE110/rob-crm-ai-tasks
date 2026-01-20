"""
Jottask Onboarding Flow
Guides new users through initial setup
"""

import os
from flask import Blueprint, render_template_string, request, redirect, url_for, session
from supabase import create_client, Client
from functools import wraps

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')

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


ONBOARDING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Jottask</title>
    <style>
        :root {
            --primary: #6366F1;
            --primary-dark: #4F46E5;
            --success: #10B981;
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
            background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            padding: 48px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 25px 80px rgba(0,0,0,0.25);
        }

        .logo {
            text-align: center;
            margin-bottom: 32px;
        }

        .logo svg {
            width: 64px;
            height: 64px;
        }

        .logo h1 {
            color: var(--primary);
            font-size: 28px;
            margin-top: 12px;
        }

        .welcome {
            text-align: center;
            margin-bottom: 40px;
        }

        .welcome h2 {
            font-size: 24px;
            color: var(--gray-900);
            margin-bottom: 12px;
        }

        .welcome p {
            color: var(--gray-500);
            font-size: 16px;
        }

        .steps {
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-bottom: 40px;
        }

        .step {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }

        .step-circle {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
        }

        .step-circle.active {
            background: var(--primary);
            color: white;
        }

        .step-circle.completed {
            background: var(--success);
            color: white;
        }

        .step-circle.pending {
            background: var(--gray-200);
            color: var(--gray-500);
        }

        .step-label {
            font-size: 12px;
            color: var(--gray-500);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--gray-700);
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--gray-200);
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.2s;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary);
        }

        .btn {
            width: 100%;
            padding: 14px 24px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
        }

        .btn-secondary {
            background: var(--gray-100);
            color: var(--gray-700);
            margin-top: 12px;
        }

        .features {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 32px 0;
        }

        .feature {
            padding: 16px;
            background: var(--gray-50);
            border-radius: 12px;
        }

        .feature-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }

        .feature h4 {
            font-size: 14px;
            color: var(--gray-900);
            margin-bottom: 4px;
        }

        .feature p {
            font-size: 12px;
            color: var(--gray-500);
        }

        .skip-link {
            display: block;
            text-align: center;
            margin-top: 20px;
            color: var(--gray-500);
            text-decoration: none;
            font-size: 14px;
        }

        .skip-link:hover {
            color: var(--primary);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <svg viewBox="0 0 512 512">
                <defs>
                    <linearGradient id="grad3" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:#8B5CF6" />
                        <stop offset="100%" style="stop-color:#6366F1" />
                    </linearGradient>
                </defs>
                <rect width="512" height="512" rx="96" fill="white"/>
                <rect x="120" y="80" width="220" height="300" rx="24" fill="url(#grad3)"/>
                <line x1="160" y1="150" x2="300" y2="150" stroke="white" stroke-width="12" stroke-linecap="round" opacity="0.5"/>
                <line x1="160" y1="200" x2="300" y2="200" stroke="white" stroke-width="12" stroke-linecap="round" opacity="0.5"/>
                <line x1="160" y1="250" x2="260" y2="250" stroke="white" stroke-width="12" stroke-linecap="round" opacity="0.5"/>
                <circle cx="310" cy="350" r="70" fill="#10B981"/>
                <path d="M275 350 L300 375 L355 315" fill="none" stroke="white" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h1>Jottask</h1>
        </div>

        {% if step == 1 %}
        <div class="welcome">
            <h2>Welcome, {{ user_name }}!</h2>
            <p>Let's get you set up in just a few steps</p>
        </div>

        <div class="steps">
            <div class="step">
                <div class="step-circle active">1</div>
                <span class="step-label">Profile</span>
            </div>
            <div class="step">
                <div class="step-circle pending">2</div>
                <span class="step-label">Email</span>
            </div>
            <div class="step">
                <div class="step-circle pending">3</div>
                <span class="step-label">First Task</span>
            </div>
        </div>

        <form method="POST" action="/onboarding/step1">
            <div class="form-group">
                <label class="form-label">What should we call you?</label>
                <input type="text" name="full_name" class="form-input" value="{{ user_name }}" required>
            </div>

            <div class="form-group">
                <label class="form-label">Company name (optional)</label>
                <input type="text" name="company_name" class="form-input" placeholder="Your company or business">
            </div>

            <div class="form-group">
                <label class="form-label">Your timezone</label>
                <select name="timezone" class="form-input">
                    <option value="Australia/Brisbane">Australia/Brisbane (AEST)</option>
                    <option value="Australia/Sydney">Australia/Sydney</option>
                    <option value="Australia/Melbourne">Australia/Melbourne</option>
                    <option value="Australia/Perth">Australia/Perth</option>
                    <option value="Pacific/Auckland">New Zealand</option>
                    <option value="America/New_York">US Eastern</option>
                    <option value="America/Los_Angeles">US Pacific</option>
                    <option value="Europe/London">UK (GMT/BST)</option>
                </select>
            </div>

            <button type="submit" class="btn btn-primary">Continue</button>
        </form>

        {% elif step == 2 %}
        <div class="welcome">
            <h2>Connect Your Email</h2>
            <p>Jottask can automatically create tasks from your emails</p>
        </div>

        <div class="steps">
            <div class="step">
                <div class="step-circle completed">✓</div>
                <span class="step-label">Profile</span>
            </div>
            <div class="step">
                <div class="step-circle active">2</div>
                <span class="step-label">Email</span>
            </div>
            <div class="step">
                <div class="step-circle pending">3</div>
                <span class="step-label">First Task</span>
            </div>
        </div>

        <div class="features">
            <div class="feature">
                <div class="feature-icon">📧</div>
                <h4>Auto-create tasks</h4>
                <p>Forward emails to create tasks automatically</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🤖</div>
                <h4>AI extraction</h4>
                <p>We'll extract due dates and priorities</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🔗</div>
                <h4>Thread emails</h4>
                <p>Related emails grouped together</p>
            </div>
            <div class="feature">
                <div class="feature-icon">🔔</div>
                <h4>Reminders</h4>
                <p>Get notified before tasks are due</p>
            </div>
        </div>

        <form method="POST" action="/onboarding/step2">
            <button type="submit" class="btn btn-primary">Set Up Later</button>
        </form>

        <a href="/onboarding/step3" class="skip-link">Skip for now →</a>

        {% elif step == 3 %}
        <div class="welcome">
            <h2>Create Your First Task</h2>
            <p>Let's add a task to get you started</p>
        </div>

        <div class="steps">
            <div class="step">
                <div class="step-circle completed">✓</div>
                <span class="step-label">Profile</span>
            </div>
            <div class="step">
                <div class="step-circle completed">✓</div>
                <span class="step-label">Email</span>
            </div>
            <div class="step">
                <div class="step-circle active">3</div>
                <span class="step-label">First Task</span>
            </div>
        </div>

        <form method="POST" action="/onboarding/complete">
            <div class="form-group">
                <label class="form-label">What do you need to do?</label>
                <input type="text" name="task_title" class="form-input" placeholder="e.g., Follow up with client" required>
            </div>

            <div class="form-group">
                <label class="form-label">When is it due?</label>
                <input type="date" name="due_date" class="form-input" value="{{ today }}">
            </div>

            <button type="submit" class="btn btn-primary">Create Task & Finish Setup</button>
        </form>

        <a href="/dashboard" class="skip-link">Skip and go to dashboard →</a>
        {% endif %}
    </div>
</body>
</html>
"""


@onboarding_bp.route('/')
@login_required
def start():
    """Start onboarding flow"""
    user_id = session['user_id']

    # Check if user has completed onboarding
    user = supabase.table('users').select('onboarding_completed').eq('id', user_id).single().execute()

    if user.data and user.data.get('onboarding_completed'):
        return redirect(url_for('dashboard'))

    return render_template_string(
        ONBOARDING_TEMPLATE,
        step=1,
        user_name=session.get('user_name', 'there')
    )


@onboarding_bp.route('/step1', methods=['POST'])
@login_required
def step1():
    """Save profile info"""
    user_id = session['user_id']

    full_name = request.form.get('full_name')
    company_name = request.form.get('company_name')
    timezone = request.form.get('timezone')

    supabase.table('users').update({
        'full_name': full_name,
        'company_name': company_name,
        'timezone': timezone
    }).eq('id', user_id).execute()

    session['user_name'] = full_name
    session['timezone'] = timezone

    return render_template_string(ONBOARDING_TEMPLATE, step=2, user_name=full_name)


@onboarding_bp.route('/step2', methods=['POST'])
@login_required
def step2():
    """Email setup (placeholder)"""
    from datetime import date
    return render_template_string(
        ONBOARDING_TEMPLATE,
        step=3,
        user_name=session.get('user_name'),
        today=date.today().isoformat()
    )


@onboarding_bp.route('/step3')
@login_required
def step3():
    """Show step 3"""
    from datetime import date
    return render_template_string(
        ONBOARDING_TEMPLATE,
        step=3,
        user_name=session.get('user_name'),
        today=date.today().isoformat()
    )


@onboarding_bp.route('/complete', methods=['POST'])
@login_required
def complete():
    """Complete onboarding and create first task"""
    user_id = session['user_id']

    task_title = request.form.get('task_title')
    due_date = request.form.get('due_date')

    # Create first task
    if task_title:
        supabase.table('tasks').insert({
            'user_id': user_id,
            'title': task_title,
            'due_date': due_date,
            'due_time': '09:00:00',
            'priority': 'medium',
            'status': 'pending'
        }).execute()

    # Mark onboarding complete
    supabase.table('users').update({
        'onboarding_completed': True
    }).eq('id', user_id).execute()

    return redirect(url_for('dashboard'))
